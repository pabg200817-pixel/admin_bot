import os
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from telethon import TelegramClient
from telethon.tl.functions.channels import CreateChannelRequest

# Настройка логов
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ВАЖНО: используем папку /tmp для сессий
clients = {}

def get_client(name):
    if name not in clients:
        # Сессия будет сохранена как файл в /tmp/accN
        clients[name] = TelegramClient(f"/tmp/{name}", API_ID, API_HASH)
    return clients[name]

class BotStates(StatesGroup):
    waiting_for_group_name = State()

def main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📱 Выбрать аккаунт")],
        [KeyboardButton(text="➕ Создать группу")]
    ], resize_keyboard=True)

@dp.message(F.text == "/start")
async def start(message: Message):
    await message.answer("Бот запущен. Выберите аккаунт (напишите acc1, acc2...):", reply_markup=main_kb())

@dp.message(F.text.startswith("acc"))
async def set_acc(message: Message, state: FSMContext):
    await state.update_data(current_acc=message.text)
    await message.answer(f"✅ Аккаунт {message.text} выбран.")

@dp.message(F.text == "➕ Создать группу")
async def ask_group(message: Message, state: FSMContext):
    data = await state.get_data()
    if 'current_acc' not in data:
        await message.answer("⚠️ Сначала выберите аккаунт (напишите acc1, acc2...)")
        return
    await message.answer("Введите название группы:")
    await state.set_state(BotStates.waiting_for_group_name)

@dp.message(BotStates.waiting_for_group_name)
async def process_group(message: Message, state: FSMContext):
    data = await state.get_data()
    acc_name = data['current_acc']
    client = get_client(acc_name)
    
    try:
        # Правильный вызов API для создания канала
        await client.start()
        await client(CreateChannelRequest(title=message.text, about="Группа от бота"))
        await message.answer(f"✅ Группа '{message.text}' успешно создана через {acc_name}")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
