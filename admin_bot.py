import asyncio
import os
import random
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command

from telethon import TelegramClient
from telethon.tl.functions.channels import CreateChannelRequest, TogglePreHistoryHiddenRequest, InviteToChannelRequest
from telethon.tl.functions.channels import EditPhotoRequest
from telethon.tl.functions.contacts import AddContactRequest
from telethon.errors import SessionPasswordNeededError

# ================= НАСТРОЙКИ (Берутся из переменных Railway) =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

GROUPS_COUNT = 4
DELAY_CREATE_GROUP = 15
DELAY_INVITE = 3
# ==============================================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class SetupPipeline(StatesGroup):
    waiting_for_name = State()
    waiting_for_photo = State()
    waiting_for_main_targets = State()
    waiting_for_phone = State()
    waiting_for_tg_code = State()
    waiting_for_password = State()

runtime_config = {
    "group_name": "",
    "photo_path": "avatar.jpg",
    "main_targets": [],
    "current_phone": "",
    "client": None,
    "accounts_processed": 0
}

def get_admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Очистить всё и Сбросить")]],
        resize_keyboard=True
    )

async def reset_all_data(state: FSMContext, message: Message):
    await state.clear()
    runtime_config["group_name"] = ""
    runtime_config["main_targets"] = []
    runtime_config["current_phone"] = ""
    runtime_config["accounts_processed"] = 0
    if runtime_config["client"]:
        try: await runtime_config["client"].disconnect()
        except: pass
        runtime_config["client"] = None
    if os.path.exists(runtime_config["photo_path"]):
        try: os.remove(runtime_config["photo_path"])
        except: pass
    await message.answer("🗑️ Все настройки сброшены. Шаг 1: Рожай новое название для групп:", reply_markup=get_admin_keyboard())
    await state.set_state(SetupPipeline.waiting_for_name)

# Убрали проверку ADMIN_ID
@dp.message(F.text == "❌ Очистить всё и Сбросить")
async def global_reset(message: Message, state: FSMContext):
    await reset_all_data(state, message)

# Убрали проверку ADMIN_ID
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    runtime_config["accounts_processed"] = 0
    await message.answer("⚙️ Конвейер готов. Шаг 1: Отправь базовое название для групп:", reply_markup=get_admin_keyboard())
    await state.set_state(SetupPipeline.waiting_for_name)

@dp.message(SetupPipeline.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    runtime_config["group_name"] = message.text
    await message.answer("🖼️ Шаг 2: Скинь картинку для аватарки чатов:")
    await state.set_state(SetupPipeline.waiting_for_photo)

@dp.message(SetupPipeline.waiting_for_photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    await bot.download(message.photo[-1], destination=runtime_config["photo_path"])
    await message.answer("👥 Шаг 3: Скинь список номеров телефонов (по одному в строке, с плюсом):")
    await state.set_state(SetupPipeline.waiting_for_main_targets)

@dp.message(SetupPipeline.waiting_for_main_targets)
async def process_targets(message: Message, state: FSMContext):
    runtime_config["main_targets"] = [line.strip() for line in message.text.split("\n") if line.strip()]
    await message.answer("📱 Шаг 4: Скинь номер телефона рабочего аккаунта (с плюсом):")
    await state.set_state(SetupPipeline.waiting_for_phone)

@dp.message(SetupPipeline.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    runtime_config["current_phone"] = phone
    session_name = f"session_{phone.replace('+', '')}"
    client = TelegramClient(session_name, API_ID, API_HASH)
    await client.connect()
    runtime_config["client"] = client
    
    if await client.is_user_authorized():
        await message.answer("✅ Аккаунт авторизован. Погнали делать группы...")
        await state.clear()
        asyncio.create_task(create_groups_logic(message, state))
    else:
        await client.send_code_request(phone)
        await message.answer(f"📩 Код подтверждения отправлен. Пиши его сюда:")
        await state.set_state(SetupPipeline.waiting_for_tg_code)

@dp.message(SetupPipeline.waiting_for_tg_code)
async def process_tg_code(message: Message, state: FSMContext):
    try:
        await runtime_config["client"].sign_in(runtime_config["current_phone"], message.text.strip())
        await message.answer("✅ Успешно! Создаю группы...")
        await state.clear()
        asyncio.create_task(create_groups_logic(message, state))
    except SessionPasswordNeededError:
        await message.answer("🔒 На аккаунте пароль. Пиши его сюда:")
        await state.set_state(SetupPipeline.waiting_for_password)

@dp.message(SetupPipeline.waiting_for_password)
async def process_password(message: Message, state: FSMContext):
    try:
        await runtime_config["client"].sign_in(password=message.text.strip())
        await message.answer("✅ Пароль подошел! Запускаю создание...")
        await state.clear()
        asyncio.create_task(create_groups_logic(message, state))
    except Exception as e:
        await message.answer(f"❌ Ошибка пароля: {e}")

async def create_groups_logic(message: Message, state: FSMContext):
    client = runtime_config["client"]
    target_phones = runtime_config["main_targets"]
    for i in range(GROUPS_COUNT):
        name = f"{runtime_config['group_name']} {random.randint(100, 999)}"
        group = (await client(CreateChannelRequest(title=name, about="", megagroup=True))).chats[0]
        if target_phones:
            await client(InviteToChannelRequest(group, target_phones))
        await message.answer(f"📦 Группа '{name}' готова.")
        await asyncio.sleep(DELAY_INVITE)
    await client.disconnect()
    await message.answer("🎉 Конвейер отработал!")

async def main(): await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())
    
