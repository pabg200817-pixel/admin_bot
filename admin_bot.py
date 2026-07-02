import asyncio, os, logging
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.filters import Command
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PasswordHashInvalidError

# Логируем всё в консоль Railway
logging.basicConfig(level=logging.INFO)

# Получаем данные
TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

bot = Bot(token=TOKEN)
dp = Dispatcher()

class LoginStates(StatesGroup):
    waiting_for_num = State()
    waiting_for_code = State()
    waiting_for_password = State()

main_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🛠 Настроить аккаунты")]], resize_keyboard=True)

@dp.message(Command("start"))
async def start(message: Message):
    if not API_ID or not API_HASH:
        await message.answer("⚠️ ОШИБКА: Не настроены API_ID или API_HASH в переменных Railway!")
    await message.answer("Привет! Фермер, нажми кнопку для настройки:", reply_markup=main_kb)

@dp.message(F.text == "🛠 Настроить аккаунты")
async def start_login(message: Message, state: FSMContext):
    await message.answer("Введи номер 1-го аккаунта (с плюсом, например +1...):")
    await state.update_data(count=1)
    await state.set_state(LoginStates.waiting_for_num)

@dp.message(LoginStates.waiting_for_num)
async def process_num(message: Message, state: FSMContext):
    if not os.path.exists("sessions"): os.makedirs("sessions")
    data = await state.get_data()
    count = data['count']
    phone = message.text
    
    # Пытаемся создать клиент
    try:
        client = TelegramClient(f"sessions/session_{count}", int(API_ID), API_HASH)
        await client.connect()
        await client.send_code_request(phone)
        await state.update_data(current_client=client, current_phone=phone)
        await message.answer("Код отправлен! Введи его (просто цифры):")
        await state.set_state(LoginStates.waiting_for_code)
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")

@dp.message(LoginStates.waiting_for_code)
async def process_code(message: Message, state: FSMContext):
    data = await state.get_data()
    client = data['current_client']
    try:
        await client.sign_in(data['current_phone'], message.text)
        await finish_login(message, state, client, data['count'])
    except PhoneCodeInvalidError:
        await message.answer("Код неверный. Попробуй еще раз:")
    except SessionPasswordNeededError:
        await message.answer("Нужен облачный пароль (2FA):")
        await state.set_state(LoginStates.waiting_for_password)

@dp.message(LoginStates.waiting_for_password)
async def process_password(message: Message, state: FSMContext):
    data = await state.get_data()
    client = data['current_client']
    try:
        await client.sign_in(password=message.text)
        await finish_login(message, state, client, data['count'])
    except PasswordHashInvalidError:
        await message.answer("Пароль неверный:")

async def finish_login(message, state, client, count):
    session_file = f"sessions/session_{count}.session"
    await client.disconnect()
    
    # Отправляем файл тебе
    await message.answer_document(FSInputFile(session_file), caption=f"✅ Аккаунт {count} привязан!")
    
    if count < 6:
        next_count = count + 1
        await state.update_data(count=next_count)
        await message.answer(f"Давай номер {next_count}-го аккаунта:")
        await state.set_state(LoginStates.waiting_for_num)
    else:
        await message.answer("🎉 Всё готово! Ферма настроена.")
        await state.clear()

async def main(): await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())
