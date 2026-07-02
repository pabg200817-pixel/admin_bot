import asyncio
import os
import random
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command

from telethon import TelegramClient
from telethon.tl.functions.channels import CreateChannelRequest, TogglePreHistoryHiddenRequest, InviteToChannelRequest
from telethon.tl.functions.channels import EditPhotoRequest
from telethon.tl.functions.contacts import AddContactRequest
from telethon.tl.types import InputChatUploadedPhoto
from telethon.errors import SessionPasswordNeededError

# ================= НАСТРОЙКИ АДМИН-БОТА =================
BOT_TOKEN = "8781400378:AAH1Sp7FD5jwSGqmOTnRjW-Ls5qbsqUQgl4"
ADMIN_ID = 7614240146

# Ключи с сайта my.telegram.org
API_ID = 38329884       
API_HASH = "d2e11c97c57678871380a3f24e2b8a0" 

GROUPS_COUNT = 4              
DELAY_CREATE_GROUP = 15       
DELAY_INVITE = 3  
# ========================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class SetupPipeline(StatesGroup):
    waiting_for_name = State()
    waiting_for_photo = State()
    waiting_for_main_targets = State()  
    waiting_for_phone = State()
    waiting_for_tg_code = State()
    waiting_for_password = State()

runtime_config = {
    "group_name": "",
    "photo_path": "avatar.jpg",
    "main_targets": [],  
    "current_phone": "",
    "client": None,
    "accounts_processed": 0
}

# Маты и подколы на случай тупняков
FUCKUP_PHRASES = [
    "Ты че, ебать, исполняешь? Сделай нормально, как просили!",
    "Бля, ну че за хуйню ты мне скинул? Глаза разуй!",
    "Сука, опять пальцы кривые? Читай че на экране написано, еблан!",
    "Пиздец, ну ты и выдал... Давай по новой, всё хуйня!",
    "Ты че, дурак бля? Нахуя ты мне это шлешь?"
]

def get_admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Очистить всё и Сбросить")]],
        resize_keyboard=True
    )

async def reset_all_data(state: FSMContext, message: Message):
    await state.clear()
    runtime_config["group_name"] = ""
    runtime_config["main_targets"] = []
    runtime_config["current_phone"] = ""
    runtime_config["accounts_processed"] = 0
    if runtime_config["client"]:
        try: await runtime_config["client"].disconnect()
        except: pass
        runtime_config["client"] = None
    if os.path.exists(runtime_config["photo_path"]):
        try: os.remove(runtime_config["photo_path"])
        except: pass
            
    await message.answer(
        "🗑️ **Всё пошло по пизде! Сбросил нахуй все настройки.**\n\n"
        "Шаг 1: Рожай новое базовое **название** для групп:",
        reply_markup=get_admin_keyboard()
    )
    await state.set_state(SetupPipeline.waiting_for_name)

@dp.message(F.text == "❌ Очистить всё и Сбросить", F.from_user.id == ADMIN_ID)
async def global_reset(message: Message, state: FSMContext):
    await reset_all_data(state, message)

@dp.message(Command("start"), F.from_user.id == ADMIN_ID)
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    runtime_config["accounts_processed"] = 0
    await message.answer(
        "⚙️ **Конвейер хуярит на полную. Я готов.**\n\n"
        "Шаг 1: Отправь базовое **название** для новых групп:",
        reply_markup=get_admin_keyboard()
    )
    await state.set_state(SetupPipeline.waiting_for_name)

@dp.message(SetupPipeline.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    if not message.text or message.text.startswith('/'):
        await message.answer(f"⚠️ {random.choice(FUCKUP_PHRASES)}\nНапиши нормальное текстовое название!")
        return
    runtime_config["group_name"] = message.text
    await message.answer("🖼️ Шаг 2: Заебень мне **картинку** для аватарки чатов (скинь как обычное фото):")
    await state.set_state(SetupPipeline.waiting_for_photo)

# Обработка ошибки, если на шаге фото скинули текст
@dp.message(SetupPipeline.waiting_for_photo, ~F.photo)
async def process_photo_error(message: Message):
    await message.answer(f"⚠️ {random.choice(FUCKUP_PHRASES)}\nЯ просил **ФОТОГРАФИЮ**, сука! Картинку мне пришли, а не этот высер текстовый.")

@dp.message(SetupPipeline.waiting_for_photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    await bot.download(photo, destination=runtime_config["photo_path"])
    await message.answer(
        "👥 **Шаг 3: Твоя банда из 6 аккаунтов**\n\n"
        "Скидывай список **НОМЕРОВ ТЕЛЕФОНОВ** твоих 6 аккаунтов (включая русский).\n"
        "Каждый номер с новой строки в формате `+380...` или `+7...`. Не тупи!"
    )
    await state.set_state(SetupPipeline.waiting_for_main_targets)

@dp.message(SetupPipeline.waiting_for_main_targets)
async def process_targets(message: Message, state: FSMContext):
    if not message.text or "+" not in message.text:
        await message.answer(f"⚠️ {random.choice(FUCKUP_PHRASES)}\nГде номера телефонов через плюс, бля? Отправь нормальный список:")
        return
    lines = message.text.split("\n")
    runtime_config["main_targets"] = [line.strip().replace(" ", "") for line in lines if line.strip()]
    if not runtime_config["main_targets"]:
        await message.answer("❌ Список пустой, ёбаный рот! Отправь номера нормально:")
        return
    await message.answer(
        f"✅ Принял {len(runtime_config['main_targets'])} симок твоей шоблы.\n\n"
        f"📱 **Шаг 4:** Теперь гони **НОМЕР ТЕЛЕФОНА** первого рабочего аккаунта из AyuGram (с него начнем хуярить чаты):"
    )
    await state.set_state(SetupPipeline.waiting_for_phone)

@dp.message(SetupPipeline.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.text.strip().replace(" ", "")
    if not phone.startswith('+'):
        await message.answer(f"⚠️ {random.choice(FUCKUP_PHRASES)}\nНомер должен начинаться с плюса (`+`), олень!")
        return
    runtime_config["current_phone"] = phone
    await message.answer(f"⏳ Подключаюсь к этой симке {phone}...")
    
    session_name = f"session_{phone.replace('+', '')}"
    client = TelegramClient(session_name, API_ID, API_HASH, device_model="Redmi 10 2022", system_version="Android 12", app_version="10.3.2")
    await client.connect()
    runtime_config["client"] = client
    
    if await client.is_user_authorized():
        await message.answer("✅ Этот аккаунт уже сука авторизован! Погнали сразу делать группы...")
        await state.clear()
        asyncio.create_task(create_groups_logic(message, state))
    else:
        await client.send_code_request(phone)
        await message.answer(f"📩 Код улетел в AyuGram на номер {phone}.\n\n**Пиши КОД сюда быстрей:**")
        await state.set_state(SetupPipeline.waiting_for_tg_code)

@dp.message(SetupPipeline.waiting_for_tg_code)
async def process_tg_code(message: Message, state: FSMContext):
    code = message.text.strip()
    client = runtime_config["client"]
    phone = runtime_config["current_phone"]
    try:
        await client.sign_in(phone, code)
        await message.answer("✅ Зашёл успешно, сука! Начинаю закидывать контакты...")
        await state.clear()
        asyncio.create_task(create_groups_logic(message, state))
    except SessionPasswordNeededError:
        await message.answer("🔒 Бля, на аккаунте висит **ОБЛАЧНЫЙ ПАРОЛЬ**. Пиши его сюда:")
        await state.set_state(SetupPipeline.waiting_for_password)
    except Exception as e:
        await message.answer(f"❌ {random.choice(FUCKUP_PHRASES)}\nОшибка кода: {e}. Давай нормальный код:")

@dp.message(SetupPipeline.waiting_for_password)
async def process_password(message: Message, state: FSMContext):
    password = message.text.strip()
    client = runtime_config["client"]
    try:
        await client.sign_in(password=password)
        await message.answer("✅ Пароль подошел, ура нахуй! Запускаю создание...")
        await state.clear()
        asyncio.create_task(create_groups_logic(message, state))
    except Exception as e:
        await message.answer(f"❌ Хуёвый пароль! Ошибка: {e}. Рожай правильный:")

async def create_groups_logic(message: Message, state: FSMContext):
    client = runtime_config["client"]
    phone = runtime_config["current_phone"]
    target_phones = runtime_config["main_targets"]
    
    await message.answer(f"👥 Запихиваю твои 6 акков в контакты этой симки...")
    for t_phone in target_phones:
        try:
            await client(AddContactRequest(id=t_phone, first_name="Свой Акк", last_name="", phone=t_phone, add_phone_privacy_exception=True))
            await asyncio.sleep(1)
        except Exception as e: print(f"Ошибка контакта: {e}")
            
    await message.answer("✅ Контакты вбиты. Начинаю клепать 4 группы...")

    for i in range(GROUPS_COUNT):
        try:
            current_name = f"{runtime_config['group_name']} {random.randint(100, 999)}"
            result = await client(CreateChannelRequest(title=current_name, about="", megagroup=True))
            group = result.chats[0]
            
            await client(TogglePreHistoryHiddenRequest(channel=group, enabled=False))
            
            if os.path.exists(runtime_config["photo_path"]):
                uploaded_photo = await client.upload_file(runtime_config["photo_path"])
                await client(EditPhotoRequest(channel=group, photo=InputChatUploadedPhoto(uploaded_photo)))
            
            await message.answer(f"📦 Группа {i+1}/{GROUPS_COUNT} ('{current_name}') готова.")
            await asyncio.sleep(DELAY_INVITE)
            
            if target_phones:
                try:
                    await client(InviteToChannelRequest(channel=group, users=target_phones))
                    await message.answer(f"➕ Вся твоя банда из 6 акков залетела в чат!")
                except Exception as invite_err:
                    await message.answer(f"⚠️ Ошибка инвайта: {invite_err}")

        except Exception as e:
            await message.answer(f"❌ Пиздец, ошибка: {e}")
            if "FLOOD_WAIT" in str(e): break
            
        if i < GROUPS_COUNT - 1:
            await asyncio.sleep(DELAY_CREATE_GROUP)
            
    await client.disconnect()
    runtime_config["accounts_processed"] += 1
    
    if runtime_config["accounts_processed"] < 5:
        await message.answer(
            f"📊 Аккаунт {phone} отработал своё.\nВсего готово рабочих симок: {runtime_config['accounts_processed']}/5.\n\n"
            f"📱 **ШЕФ, ДАВАЙ СЛЕДУЮЩИЙ НОМЕР ИЗ AYUGRAM:**"
        )
        await state.set_state(SetupPipeline.waiting_for_phone)
    else:
        await message.answer("🎉 Охуеть, конвейер полностью отработал круг! Все 5 аккаунтов сделали грязь.", reply_markup=get_admin_keyboard())

async def main(): await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())