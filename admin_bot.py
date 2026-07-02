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

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN", "").strip()
API_ID = int(os.getenv("API_ID", "0").strip())
API_HASH = os.getenv("API_HASH", "").strip()

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class LoginStates(StatesGroup):
    waiting_for_num = State()
    waiting_for_code = State()

@dp.message(Command("start"))
async def start(message: Message):
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🛠 Настроить аккаунты")]], resize_keyboard=True)
    await message.answer("Бот готов. Нажми кнопку для авторизации:", reply_markup=kb)

@dp.message(F.text == "🛠 Настроить аккаунты")
async def start_login(message: Message, state: FSMContext):
    await message.answer("Введи номер с плюсом (например +1...):")
    await state.set_state(LoginStates.waiting_for_num)

@dp.message(LoginStates.waiting_for_num)
async def process_num(message: Message, state: FSMContext):
    phone = message.text
    if not os.path.exists("sessions"): os.makedirs("sessions")
    
    # Создаем клиента с эмуляцией Android устройства
    client = TelegramClient("sessions/session_1", API_ID, API_HASH, 
                            device_model="Pixel 7", 
                            system_version="Android 13")
    
    await client.connect()
    try:
        sent = await client.send_code_request(phone)
        await state.update_data(client=client, phone=phone, phone_code_hash=sent.phone_code_hash)
        await message.answer("✅ Запрос ушел! Проверь официальный Telegram (чат с Telegram). Введи код:")
        await state.set_state(LoginStates.waiting_for_code)
        print(f"DEBUG: Код успешно запрошен для {phone}")
    except Exception as e:
        await message.answer(f"❌ ОШИБКА: {str(e)}")
        print(f"DEBUG CRITICAL: {e}")

@dp.message(LoginStates.waiting_for_code)
async def process_code(message: Message, state: FSMContext):
    data = await state.get_data()
    client = data['client']
    try:
        await client.sign_in(data['phone'], message.text, phone_code_hash=data['phone_code_hash'])
        await message.answer("✅ Успешно! Аккаунт привязан.")
        await client.disconnect()
        await state.clear()
    except Exception as e:
        await message.answer(f"❌ ОШИБКА КОДА: {str(e)}")
        print(f"DEBUG CODE ERROR: {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
