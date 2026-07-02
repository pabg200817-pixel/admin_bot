import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from telethon import TelegramClient

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Получение переменных с очисткой от пробелов
TOKEN = os.getenv("BOT_TOKEN", "").strip()
API_ID = os.getenv("API_ID", "").strip()
API_HASH = os.getenv("API_HASH", "").strip()

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Состояния
class LoginStates(StatesGroup):
    waiting_for_num = State()
    waiting_for_code = State()

@dp.message(Command("start"))
async def start(message: Message):
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🛠 Настроить аккаунты")]], resize_keyboard=True)
    await message.answer("Бот запущен. Нажми кнопку для начала авторизации:", reply_markup=kb)

@dp.message(F.text == "🛠 Настроить аккаунты")
async def start_login(message: Message, state: FSMContext):
    await message.answer("Введи номер телефона в международном формате (с плюсом, например +1...):")
    await state.set_state(LoginStates.waiting_for_num)

@dp.message(LoginStates.waiting_for_num)
async def process_num(message: Message, state: FSMContext):
    phone = message.text
    if not os.path.exists("sessions"):
        os.makedirs("sessions")
    
    # Создаем клиента
    client = TelegramClient("sessions/session_1", int(API_ID), API_HASH)
    
    try:
        await client.connect()
        # Запрос кода
        sent = await client.send_code_request(phone)
        
        # Сохраняем данные в состояние
        await state.update_data(client=client, phone=phone, phone_code_hash=sent.phone_code_hash)
        
        await message.answer("✅ Запрос отправлен! Код должен прийти в официальный клиент Telegram. Введи его цифрами:")
        await state.set_state(LoginStates.waiting_for_code)
        
    except Exception as e:
        error_msg = f"❌ ОШИБКА: {str(e)}"
        await message.answer(error_msg)
        print(f"DEBUG ERROR: {error_msg}") # Это будет в логах Railway

@dp.message(LoginStates.waiting_for_code)
async def process_code(message: Message, state: FSMContext):
    data = await state.get_data()
    client = data['client']
    phone = data['phone']
    code = message.text
    
    try:
        await client.sign_in(phone, code)
        await message.answer("✅ Успешно! Аккаунт авторизован.")
        await client.disconnect()
        await state.clear()
    except Exception as e:
        await message.answer(f"❌ ОШИБКА КОДА: {str(e)}")
        print(f"DEBUG ERROR: {str(e)}")

async def main():
    print("Бот запущен и готов к работе...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
