import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from telethon import TelegramClient
from telethon.tl.functions.channels import CreateChannelRequest

# Настройка
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Используем /tmp для сессии, чтобы Railway не выдавал ошибку записи
client = TelegramClient("/tmp/session_1", API_ID, API_HASH)

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
        # ПРАВИЛЬНЫЙ ВЫЗОВ создания канала в Telethon
        await client(CreateChannelRequest(
            title=message.text,
            about="Группа от админ-бота"
        ))
        await message.answer(f"✅ Группа '{message.text}' успешно создана!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    await state.clear()

@dp.message(F.text == "📊 Статус")
async def status(message: Message):
    try:
        me = await client.get_me()
        await message.answer(f"👤 Аккаунт: {me.first_name} (@{me.username})")
    except Exception as e:
        await message.answer(f"❌ Клиент не авторизован или не подключен: {e}")

async def main():
    await client.start() # Это лучший способ инициализации
    print("Бот и Telethon запущены!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
