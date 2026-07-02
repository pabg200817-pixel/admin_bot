import asyncio
import os
import random
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

from telethon import TelegramClient
from telethon.tl.functions.channels import CreateChannelRequest, InviteToChannelRequest
from telethon.errors import SessionPasswordNeededError

# ================= НАСТРОЙКИ =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

GROUPS_COUNT = 4
DELAY_INVITE = 3
# =============================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class SetupPipeline(StatesGroup):
    waiting_for_name = State()
    waiting_for_photo = State()
    waiting_for_main_targets = State()
    waiting_for_phone = State()
    waiting_for_tg_code = State()
    waiting_for_password = State()

def get_admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Сбросить текущий процесс")]],
        resize_keyboard=True
    )

@dp.message(F.text == "❌ Сбросить текущий процесс")
async def cmd_reset(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🗑️ Процесс сброшен. Начни заново командой /start")

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("⚙️ Бот готов к работе.\nШаг 1: Напиши название для групп:", reply_markup=get_admin_keyboard())
    await state.set_state(SetupPipeline.waiting_for_name)

@dp.message(SetupPipeline.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(group_name=message.text)
    await message.answer("🖼️ Шаг 2: Скинь картинку для аватарки чатов:")
    await state.set_state(SetupPipeline.waiting_for_photo)

@dp.message(SetupPipeline.waiting_for_photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    # Сохраняем фото с уникальным именем для пользователя
    photo_path = f"avatar_{message.from_user.id}.jpg"
    await bot.download(message.photo[-1], destination=photo_path)
    await state.update_data(photo_path=photo_path)
    
    await message.answer("👥 Шаг 3: Скинь список НОМЕРОВ ТЕЛЕФОНОВ (по одному в строке, с плюсом):")
    await state.set_state(SetupPipeline.waiting_for_main_targets)

@dp.message(SetupPipeline.waiting_for_main_targets)
async def process_targets(message: Message, state: FSMContext):
    targets = [line.strip() for line in message.text.split("\n") if line.strip()]
    await state.update_data(main_targets=targets)
    await message.answer("📱 Шаг 4: Скинь номер телефона рабочего аккаунта (с плюсом):")
    await state.set_state(SetupPipeline.waiting_for_phone)

@dp.message(SetupPipeline.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    await state.update_data(phone=phone)
    
    session_name = f"session_{phone.replace('+', '')}"
    client = TelegramClient(session_name, API_ID, API_HASH)
    await client.connect()
    
    if await client.is_user_authorized():
        await message.answer("✅ Аккаунт уже авторизован. Создаю группы...")
        await create_groups_logic(message, state, client)
    else:
        await client.send_code_request(phone)
        # Сохраняем клиента в стейт, чтобы потом использовать
        await state.update_data(client=client)
        await message.answer(f"📩 Пиши код подтверждения:")
        await state.set_state(SetupPipeline.waiting_for_tg_code)

@dp.message(SetupPipeline.waiting_for_tg_code)
async def process_tg_code(message: Message, state: FSMContext):
    data = await state.get_data()
    client = data['client']
    try:
        await client.sign_in(data['phone'], message.text.strip())
        await message.answer("✅ Успешно! Создаю группы...")
        await create_groups_logic(message, state, client)
    except SessionPasswordNeededError:
        await message.answer("🔒 Нужен облачный пароль:")
        await state.set_state(SetupPipeline.waiting_for_password)

async def create_groups_logic(message: Message, state: FSMContext, client: TelegramClient):
    data = await state.get_data()
    target_phones = data.get("main_targets", [])
    group_name = data.get("group_name", "Group")
    
    for i in range(GROUPS_COUNT):
        name = f"{group_name} {random.randint(100, 999)}"
        group = (await client(CreateChannelRequest(title=name, about="", megagroup=True))).chats[0]
        if target_phones:
            await client(InviteToChannelRequest(group, target_phones))
        await message.answer(f"📦 Группа {name} создана.")
        await asyncio.sleep(DELAY_INVITE)
        
    await client.disconnect()
    await message.answer("🎉 Готово! Конвейер завершил работу.")
    await state.clear()

async def main(): await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())
