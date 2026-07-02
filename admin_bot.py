import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from telethon import TelegramClient

# Настройка
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")

# Инициализация
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ВАЖНО: сохраняем сессию в /tmp (там всегда есть права на запись в Railway)
session_path = "/tmp/session_1"
client = TelegramClient(session_path, API_ID, API_HASH)

class BotStates(StatesGroup):
    waiting_for_group_name = State()

def main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="➕ Создать группу")],
        [KeyboardButton(text="📊 Статус")]
    ], resize_keyboard=True)

@dp.message(F.text == "/start")
async def start(message: Message):
    await message.answer("Бот запущен. Используй кнопки:", reply_markup=main_kb())

@dp.message(F.text == "➕ Создать группу")
async def ask_group(message: Message, state: FSMContext):
    await message.answer("Введите название новой группы:")
    await state.set_state(BotStates.waiting_for_group_name)

@dp.message(BotStates.waiting_for_group_name)
async def process_group(message: Message, state: FSMContext):
    try:
        # Создаем канал через Telethon
        await client.create_channel(title=message.text, about="Группа от админ-бота")
        await message.answer(f"✅ Группа '{message.text}' создана!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    await state.clear()

@dp.message(F.text == "📊 Статус")
async def status(message: Message):
    me = await client.get_me()
    await message.answer(f"👤 Аккаунт: {me.first_name}\n✅ Сессия: Работает")

async def main():
    await client.connect()
    # Если ты загрузил файл session_1.session, он подхватится автоматически
    print("Бот и Telethon запущены!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
