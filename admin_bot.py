import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from telethon import TelegramClient

# Настройка
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

# Инициализация
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
client = TelegramClient("sessions/session_1", API_ID, API_HASH)

# Состояния для логики
class BotStates(StatesGroup):
    waiting_for_group_name = State()

# Клавиатура
def main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="➕ Создать группу")],
        [KeyboardButton(text="📊 Статус аккаунта")]
    ], resize_keyboard=True)

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("Привет! Я готов к работе. Выбери действие:", reply_markup=main_kb())

@dp.message(F.text == "➕ Создать группу")
async def ask_group_name(message: Message, state: FSMContext):
    await message.answer("Введите название будущей группы:")
    await state.set_state(BotStates.waiting_for_group_name)

@dp.message(BotStates.waiting_for_group_name)
async def create_group(message: Message, state: FSMContext):
    group_name = message.text
    try:
        # Телефоновская логика создания группы
        result = await client.create_channel(title=group_name, about="Группа создана ботом")
        await message.answer(f"✅ Группа '{group_name}' успешно создана!", reply_markup=main_kb())
    except Exception as e:
        await message.answer(f"❌ Ошибка при создании: {e}")
    await state.clear()

@dp.message(F.text == "📊 Статус аккаунта")
async def check_status(message: Message):
    me = await client.get_me()
    await message.answer(f"👤 Авторизован как: {me.first_name} (@{me.username})")

async def main():
    # Запуск Telethon клиента
    await client.connect()
    
    if not await client.is_user_authorized():
        print("!!! КРИТИЧЕСКАЯ ОШИБКА: Файл сессии не найден или не авторизован !!!")
        return

    print("Сессия активна. Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
