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

logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Хранилище клиентов
clients = {}

def get_client(name):
    # Файлы сессий ищем в /tmp/ (там есть права на запись)
    if name not in clients:
        clients[name] = TelegramClient(f"/tmp/{name}", API_ID, API_HASH)
    return clients[name]

class BotStates(StatesGroup):
    choosing_acc = State()
    waiting_for_group_name = State()

@dp.message(F.text == "/start")
async def start(message: Message):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📱 Выбрать аккаунт")],
        [KeyboardButton(text="➕ Создать группу")]
    ], resize_keyboard=True)
    await message.answer("Бот запущен. Выберите аккаунт для управления.", reply_markup=kb)

@dp.message(F.text == "📱 Выбрать аккаунт")
async def show_accounts(message: Message):
    await message.answer("Напишите имя аккаунта (например: acc1, acc2...):")

@dp.message(F.text.regexp(r'acc[1-6]'))
async def select_acc(message: Message, state: FSMContext):
    await state.update_data(current_acc=message.text)
    await message.answer(f"✅ Аккаунт {message.text} выбран.")

@dp.message(F.text == "➕ Создать группу")
async def ask_group(message: Message, state: FSMContext):
    data = await state.get_data()
    if 'current_acc' not in data:
        await message.answer("⚠️ Сначала выберите аккаунт!")
        return
    await message.answer("Введите название группы:")
    await state.set_state(BotStates.waiting_for_group_name)

@dp.message(BotStates.waiting_for_group_name)
async def process_group(message: Message, state: FSMContext):
    data = await state.get_data()
    acc_name = data['current_acc']
    client = get_client(acc_name)
    
    try:
        if not client.is_connected():
            await client.connect()
            
        await client(CreateChannelRequest(title=message.text, about="Группа от бота"))
        await message.answer(f"✅ Группа '{message.text}' создана через {acc_name}")
    except Exception as e:
        await message.answer(f"❌ Ошибка {acc_name}: {str(e)}")
    await state.clear()

async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
