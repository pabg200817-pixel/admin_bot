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

# Словарь для хранения активных клиентов
clients = {}

def get_client(name):
    # Создает сессию для конкретного имени (например, 'acc1', 'acc2'...)
    if name not in clients:
        clients[name] = TelegramClient(f"/tmp/{name}", API_ID, API_HASH)
    return clients[name]

class BotStates(StatesGroup):
    choosing_acc = State()
    waiting_for_group_name = State()

@dp.message(F.text == "/start")
async def start(message: Message):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📱 Управление аккаунтами")],
        [KeyboardButton(text="➕ Создать группу")]
    ], resize_keyboard=True)
    await message.answer("Бот готов к работе с несколькими аккаунтами.", reply_markup=kb)

@dp.message(F.text == "📱 Управление аккаунтами")
async def show_accounts(message: Message):
    await message.answer("Выберите аккаунт (acc1, acc2... acc6):")

@dp.message(F.text.startswith("acc"))
async def select_acc(message: Message, state: FSMContext):
    acc_name = message.text
    await state.update_data(current_acc=acc_name)
    await message.answer(f"Аккаунт {acc_name} выбран.")

@dp.message(F.text == "➕ Создать группу")
async def ask_group(message: Message, state: FSMContext):
    data = await state.get_data()
    if 'current_acc' not in data:
        await message.answer("Сначала выберите аккаунт (напишите acc1, acc2 и т.д.)")
        return
    await message.answer("Введите название группы:")
    await state.set_state(BotStates.waiting_for_group_name)

@dp.message(BotStates.waiting_for_group_name)
async def process_group(message: Message, state: FSMContext):
    data = await state.get_data()
    acc_name = data['current_acc']
    client = get_client(acc_name)
    
    try:
        await client.connect()
        await client(CreateChannelRequest(title=message.text, about="Группа от бота"))
        await message.answer(f"✅ Группа создана через {acc_name}")
    except Exception as e:
        await message.answer(f"❌ Ошибка {acc_name}: {e}")
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
