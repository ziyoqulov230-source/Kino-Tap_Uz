import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ⚙️ ASOSIY SOZLAMALAR
TOKEN = "8807187482:AAFrPmtI_xWmHTF191K3RiMdIuOznrW8"  
ADMIN_ID = 6050634459  

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# 🗄 MULTI-QISM REJIMIDAGI BAZA SOZLAMASI
conn = sqlite3.connect("friend_bot_data.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("PRAGMA journal_mode=WAL;")

cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
# Bu yerda PRIMARY KEY olib tashlandi, chunki bitta kodga bir nechta kino yozish mumkin bo'ladi!
cursor.execute("""
CREATE TABLE IF NOT EXISTS films (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT,
    file_id TEXT,
    caption TEXT
)
""")
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
conn.commit()

try:
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('channels_id', '')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('channels_link', '')")
    conn.commit()
except Exception:
    pass

class AdminStates(StatesGroup):
    waiting_for_video = State()
    waiting_for_code = State()
    waiting_for_caption = State()
    waiting_for_channels_id = State()
    waiting_for_channels_link = State()
    waiting_for_del_code = State()  
    waiting_for_reklama = State()   

def get_setting(key):
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    res = cursor.fetchone()
    return res[0] if res else None

def set_setting(key, value):
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()

def add_user(user_id):
    try:
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
    except Exception:
        pass

async def check_all_subscriptions(user_id: int) -> bool:
    ids_str = get_setting("channels_id")
    if not ids_str or ids_str.strip() == "":
        return True
    channel_ids = [id.strip() for id in ids_str.split(",") if id.strip()]
    for ch_id in channel_ids:
        try:
            member = await bot.get_chat_member(chat_id=int(ch_id) if ch_id.startswith("-") else ch_id, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception as e:
            if "retry after" in str(e).lower():
                return True
            continue
    return True

@dp.message(CommandStart())
async def start_cmd(msg: types.Message):
    add_user(msg.from_user.id)
    args = msg.text.split()
    if len(args) > 1:
        code = args[1].strip()
        await send_movie_or_ask_sub(msg, code)
        return

    is_subscribed = await check_all_subscriptions(msg.from_user.id)
    if not is_subscribed:
        links_str = get_setting("channels_link")
        links = [l.strip() for l in links_str.split(",") if l.strip()]
        inline_keyboard = []
        for index, link in enumerate(links, start=1):
            inline_keyboard.append([InlineKeyboardButton(text=f"{index} - kanal ↗️", url=link)])
        inline_keyboard.append([InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="check_none")])
        await msg.answer("❌ Kechirasiz botimizdan foydalanishdan oldin ushbu kanallarga a'zo bo'lishingiz kerak.", reply_markup=InlineKeyboardMarkup(inline_keyboard=inline_keyboard))
        return

    await msg.answer(f"👋 Assalomu alaykum {msg.from_user.first_name} botimizga xush kelibsiz.\n\n✍ *Kino kodini yuboring.*", parse_mode="Markdown")
