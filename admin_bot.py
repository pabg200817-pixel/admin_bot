import asyncio, os
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PasswordHashInvalidError

# Инициализация
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

class LoginStates(StatesGroup):
    waiting_for_num = State()
    waiting_for_code = State()
    waiting_for_password = State()

main_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🛠 Настроить аккаунты")]], resize_keyboard=True)

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("Ну чё, готов к работе? Жми кнопку и погнали, фермер:", reply_markup=main_kb)

@dp.message(F.text == "🛠 Настроить аккаунты")
async def start_login(message: Message, state: FSMContext):
    await message.answer("Давай номер 1-го аккаунта США (с плюсом, например +1...):")
    await state.update_data(count=1)
    await state.set_state(LoginStates.waiting_for_num)

@dp.message(LoginStates.waiting_for_num)
async def process_num(message: Message, state: FSMContext):
    if not os.path.exists("sessions"): os.makedirs("sessions")
    data = await state.get_data()
    count = data['count']
    phone = message.text
    
    # Создаем клиента
    client = TelegramClient(f"sessions/session_{count}", int(os.getenv("API_ID")), os.getenv("API_HASH"))
    await client.connect()
    
    try:
        await client.send_code_request(phone)
        await state.update_data(current_client=client, current_phone=phone)
        await message.answer("Код улетел. Пиши его сюда, не тупи:")
        await state.set_state(LoginStates.waiting_for_code)
    except Exception as e:
        await message.answer(f"Ебать, какая-то хуйня при отправке кода: {e}")

@dp.message(LoginStates.waiting_for_code)
async def process_code(message: Message, state: FSMContext):
    data = await state.get_data()
    client = data['current_client']
    try:
        await client.sign_in(data['current_phone'], message.text)
        await finish_login(message, state, client, data['count'])
    except PhoneCodeInvalidError:
        await message.answer("Хуйню ввел, код неверный! Пиши еще раз, внимательнее:")
    except SessionPasswordNeededError:
        await message.answer("На акке стоит облачный пароль, вводи его, умник:")
        await state.set_state(LoginStates.waiting_for_password)

@dp.message(LoginStates.waiting_for_password)
async def process_password(message: Message, state: FSMContext):
    data = await state.get_data()
    client = data['current_client']
    try:
        await client.sign_in(password=message.text)
        await finish_login(message, state, client, data['count'])
    except PasswordHashInvalidError:
        await message.answer("Да ты заебал, пароль неверный! Пробуй еще раз:")

async def finish_login(message, state, client, count):
    await client.disconnect()
    if count < 5:
        await state.update_data(count=count + 1)
        await message.answer(f"✅ Аккаунт {count} привязал. Давай номер {count + 1}-го:")
        await state.set_state(LoginStates.waiting_for_num)
    elif count == 5:
        await message.answer("Все 5 рабочих готовы. Остался последний — ТЕХНИЧКА! Давай её номер:")
        await state.update_data(count=6)
        await state.set_state(LoginStates.waiting_for_num)
    else:
        await message.answer("🎉 Всё готово, ферма настроена! Можешь идти пить пиво.")
        await state.clear()

async def main(): 
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__": 
    asyncio.run(main())
