import asyncio
import logging
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from telethon import TelegramClient
from telethon.tl.functions.contacts import SearchRequest

# ----------------------------------------------------
# SOZLAMALAR
# ----------------------------------------------------
BOT_TOKEN = "9123547350:AAFo_V41ltBa94Ps7Yxm_ZjElptwNcs_q3c"
API_ID = 37881267
API_HASH = "fd1edeb73b34fa0955df2a06f31620fd"

ADMIN_LOGIN = "admin"
ADMIN_PASSWORD = "superpassword123"

CONFIG = {
    "smm_url": "https://smm-panel-provider.com/api/v2",
    "smm_key": "",
    "smm_service_id": "",
    "smm_quantity": 500,
    "target_channel": "",
    "keywords": [],
    "check_interval": 180,  # 3 daqiqa
    "is_running": False,
}

USERS_DB = {ADMIN_LOGIN: ADMIN_PASSWORD}
AUTHORIZED_USERS = set()

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

userbot = TelegramClient("search_session", API_ID, API_HASH)


class AuthStates(StatesGroup):
  waiting_for_login = State()
  waiting_for_password = State()


class AdminStates(StatesGroup):
  adding_user_login = State()
  adding_user_password = State()
  setting_smm_key = State()
  setting_smm_service = State()
  setting_target_channel = State()
  setting_keywords = State()


def get_main_keyboard():
  return InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="▶️ Ishga tushirish", callback_data="start_monitoring"
              ),
              InlineKeyboardButton(
                  text="⏸ To'xtatish", callback_data="stop_monitoring"
              ),
          ],
          [
              InlineKeyboardButton(
                  text="⚙️ SMM API Sozlamalari", callback_data="smm_settings"
              ),
              InlineKeyboardButton(
                  text="🎯 Kanal va Kalit So'zlar", callback_data="target_settings"
              ),
          ],
          [
              InlineKeyboardButton(
                  text="📊 Status", callback_data="check_status"
              ),
              InlineKeyboardButton(
                  text="👤 Yangi Admin Yaratish", callback_data="add_new_user"
              ),
          ],
      ]
  )


def trigger_smm_boost():
  if not CONFIG["smm_key"] or not CONFIG["smm_service_id"]:
    return False

  payload = {
      "key": CONFIG["smm_key"],
      "action": "add",
      "service": CONFIG["smm_service_id"],
      "link": f"https://t.me/{CONFIG['target_channel']}",
      "quantity": CONFIG["smm_quantity"],
  }
  try:
    res = requests.post(CONFIG["smm_url"], data=payload, timeout=10)
    data = res.json()
    if "order" in data:
      return data["order"]
  except Exception as e:
    logging.error(f"SMM Error: {e}")
  return False


async def search_monitoring_loop():
  while True:
    if CONFIG["is_running"] and CONFIG["target_channel"] and CONFIG["keywords"]:
      try:
        if not userbot.is_connected():
          await userbot.connect()

        for kw in CONFIG["keywords"]:
          result = await userbot(SearchRequest(q=kw, limit=10))
          top_list = [
              chat.username.lower()
              for chat in result.chats
              if getattr(chat, "username", None)
          ]

          target = CONFIG["target_channel"].lower().replace("@", "")

          if target not in top_list[:3]:
            order_id = trigger_smm_boost()
            for user_id in AUTHORIZED_USERS:
              await bot.send_message(
                  user_id,
                  f"🚨 **OGOHLANTIRISH!**\n\nKanal `@{target}` kalit so'z:"
                  f" `{kw}` bo'yicha TOP-3 da emas!\n\n🚀 **Avto-Boost"
                  f" yuborildi.** Order ID: `{order_id}`",
              )
            break
      except Exception as e:
        logging.error(f"Search Loop Error: {e}")

    await asyncio.sleep(CONFIG["check_interval"])


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
  if message.from_user.id in AUTHORIZED_USERS:
    await message.answer(
        "👋 Xush kelibsiz! Boshqaruv paneli:", reply_markup=get_main_keyboard()
    )
  else:
    await message.answer("🔒 Loginingizni kiriting:")
    await state.set_state(AuthStates.waiting_for_login)


@dp.message(AuthStates.waiting_for_login)
async def process_login(message: types.Message, state: FSMContext):
  await state.update_data(login=message.text)
  await message.answer("🔑 Parolingizni kiriting:")
  await state.set_state(AuthStates.waiting_for_password)


@dp.message(AuthStates.waiting_for_password)
async def process_password(message: types.Message, state: FSMContext):
  user_data = await state.get_data()
  login = user_data.get("login")
  password = message.text

  if login in USERS_DB and USERS_DB[login] == password:
    AUTHORIZED_USERS.add(message.from_user.id)
    await state.clear()
    await message.answer(
        "✅ Muvaffaqiyatli kirdingiz!", reply_markup=get_main_keyboard()
    )
  else:
    await message.answer("❌ Noto'g'ri login yoki parol! Qayta /start bosing.")
    await state.clear()


@dp.callback_query()
async def process_callbacks(call: types.CallbackQuery, state: FSMContext):
  if call.from_user.id not in AUTHORIZED_USERS:
    await call.message.answer("🔒 Avval login qiling! /start bosing.")
    return

  data = call.data
  if data == "start_monitoring":
    CONFIG["is_running"] = True
    await call.message.edit_text(
        "🟢 Kuzatuv va Avto-Boost yoqildi!", reply_markup=get_main_keyboard()
    )
  elif data == "stop_monitoring":
    CONFIG["is_running"] = False
    await call.message.edit_text(
        "🔴 Kuzatuv to'xtatildi.", reply_markup=get_main_keyboard()
    )
  elif data == "check_status":
    status_text = (
        f"📊 **STATUS:**\n\n"
        f"• Holat: {'🟢 Faol' if CONFIG['is_running'] else '🔴 To\'xtatilgan'}\n"
        f"• Kanal: @{CONFIG['target_channel'] or 'Yo\'q'}\n"
        f"• Kalit so'zlar: {', '.join(CONFIG['keywords']) or 'Yo\'q'}\n"
        f"• SMM Service ID: {CONFIG['smm_service_id'] or 'Yo\'q'}\n"
    )
    await call.message.edit_text(
        status_text, reply_markup=get_main_keyboard()
    )
  elif data == "add_new_user":
    await call.message.answer("👤 Yangi admin LOGINini kiriting:")
    await state.set_state(AdminStates.adding_user_login)
  elif data == "smm_settings":
    await call.message.answer("⚙️ SMM Panel API Keyingizni kiriting:")
    await state.set_state(AdminStates.setting_smm_key)
  elif data == "target_settings":
    await call.message.answer(
        "🎯 Kanalingiz usernamesini kiriting (@ usiz):"
    )
    await state.set_state(AdminStates.setting_target_channel)


@dp.message(AdminStates.setting_smm_key)
async def save_smm_key(message: types.Message, state: FSMContext):
  CONFIG["smm_key"] = message.text
  await message.answer("SMM Service ID raqamini kiriting:")
  await state.set_state(AdminStates.setting_smm_service)


@dp.message(AdminStates.setting_smm_service)
async def save_smm_service(message: types.Message, state: FSMContext):
  CONFIG["smm_service_id"] = message.text
  await state.clear()
  await message.answer("✅ SMM Sozlandi!", reply_markup=get_main_keyboard())


@dp.message(AdminStates.setting_target_channel)
async def save_target_channel(message: types.Message, state: FSMContext):
  CONFIG["target_channel"] = message.text.replace("@", "")
  await message.answer("Kalit so'zlarni kiriting (vergul bilan):")
  await state.set_state(AdminStates.setting_keywords)


@dp.message(AdminStates.setting_keywords)
async def save_keywords(message: types.Message, state: FSMContext):
  CONFIG["keywords"] = [k.strip() for k in message.text.split(",")]
  await state.clear()
  await message.answer(
      "✅ Kalit so'zlar saqlandi!", reply_markup=get_main_keyboard()
  )


@dp.message(AdminStates.adding_user_login)
async def save_new_user_login(message: types.Message, state: FSMContext):
  await state.update_data(new_login=message.text)
  await message.answer("🔑 Yangi admin PAROLini kiriting:")
  await state.set_state(AdminStates.adding_user_password)


@dp.message(AdminStates.adding_user_password)
async def save_new_user_password(message: types.Message, state: FSMContext):
  data = await state.get_data()
  USERS_DB[data.get("new_login")] = message.text
  await state.clear()
  await message.answer(
      "✅ Yangi Admin yaratildi!", reply_markup=get_main_keyboard()
  )


async def main():
  asyncio.create_task(search_monitoring_loop())
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
