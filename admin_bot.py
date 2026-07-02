import asyncio, os, logging
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.filters import Command
from telethon import TelegramClient

logging.basicConfig(level=logging.INFO)

# Убираем пробелы, если они случайно попали в Railway
TOKEN = os.getenv("BOT_TOKEN", "").strip()
API_ID = os.getenv("API_ID", "").strip()
API_HASH = os.getenv("API_HASH", "").strip()

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class LoginStates(StatesGroup):
    waiting_for_num = State()
    waiting_for_code = State()

@dp.message(Command("start"))
async def start(message: Message):
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🛠 Настроить аккаунты")]], resize_keyboard=True)
    await message.answer("Бот запущен. Нажми кнопку:", reply_markup=kb)

@dp.message(F.text == "🛠 Настроить аккаунты")
async def start_login(message: Message, state: FSMContext):
    await message.answer("Введи номер (с плюсом, например +1...):")
    await state.set_state(LoginStates.waiting_for_num)

@dp.message(LoginStates.waiting_for_num)
async def process_num(message: Message, state: FSMContext):
    phone = message.text
    if not os.path.exists("sessions"): os.makedirs("sessions")
    
    # Используем API_ID и HASH прямо здесь
    try:
        client = TelegramClient("sessions/session_1", int(API_ID), API_HASH)
        await client.connect()
        await client.send_code_request(phone)
        await state.update_data(client=client, phone=phone)
        await message.answer("Код отправлен. Введи его:")
        await state.set_state(LoginStates.waiting_for_code)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

@dp.message(LoginStates.waiting_for_code)
async def process_code(message: Message, state: FSMContext):
    data = await state.get_data()
    client = data['client']
    try:
        await client.sign_in(data['phone'], message.text)
        await message.answer("✅ Успешно!")
        await client.disconnect()
        await state.clear()
    except Exception as e:
        await message.answer(f"Ошибка кода: {e}")

async def main(): await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())
