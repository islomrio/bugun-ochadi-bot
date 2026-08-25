import os
import asyncio
import logging
import sqlite3

from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from telethon import TelegramClient, events
from telethon.sessions import StringSession

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
STRING_SESSION = os.getenv("STRING_SESSION")

bot = Bot(BOT_TOKEN)
client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

# -------------------------
# База данных
# -------------------------

db = sqlite3.connect("bugun.db", check_same_thread=False)

db.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    region TEXT
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS votes(
    msg TEXT PRIMARY KEY,
    yes INTEGER DEFAULT 0,
    no INTEGER DEFAULT 0
)
""")

db.commit()

# -------------------------
# Источники Telegram
# -------------------------

SOURCE_CHANNELS = [
    "minenergy_uz",
    "AO_Hududgaztaminot",
    "portal_gov_uz",
    "MCHSUzbek",
    "huquqiyaxborot",
    "mitcuz",
    "Mintrans_uz",
    "uzagroministry",
    "madaniyatvazirligi",
    "iivuz",
    "mahallavaoilainfo",
    "ssvuz",
    "ecogovuz",
    "AntimonUz",
    "uzstataxborot",
    "kommunaluzb",
]

# -------------------------
# Районы
# -------------------------

REGIONS = [
    "Юнусабад",
    "Чиланзар",
    "Мирабад",
    "Мирзо-Улугбек",
    "Шайхантахур",
    "Яккасарай",
    "Учтепа",
    "Алмазар",
    "Сергелий",
    "Бектемир",
    "Янгихаёт",
    "Яшнабад",
]

last_messages = set()

# -------------------------
# Работа с SQLite
# -------------------------

def set_region(user_id, region):
    db.execute(
        "INSERT OR REPLACE INTO users VALUES(?,?)",
        (user_id, region)
    )
    db.commit()

def get_region(user_id):
    row = db.execute(
        "SELECT region FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()

    return row[0] if row else None

def all_users():
    return db.execute(
        "SELECT user_id,region FROM users"
    ).fetchall()

def vote(message, yes_vote):

    db.execute(
        "INSERT OR IGNORE INTO votes(msg) VALUES(?)",
        (message,)
    )

    if yes_vote:
        db.execute(
            "UPDATE votes SET yes=yes+1 WHERE msg=?",
            (message,)
        )
    else:
        db.execute(
            "UPDATE votes SET no=no+1 WHERE msg=?",
            (message,)
        )

    db.commit()

    return db.execute(
        "SELECT yes,no FROM votes WHERE msg=?",
        (message,)
    ).fetchone()

# -------------------------
# Клавиатуры
# -------------------------

def region_keyboard():

    rows = []
    row = []

    for region in REGIONS:

        row.append(
            InlineKeyboardButton(
                region,
                callback_data=f"region:{region}"
            )
        )

        if len(row) == 2:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    return InlineKeyboardMarkup(rows)

def post_keyboard():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📍 Мой район",
                callback_data="my_region"
            )
        ],
        [
            InlineKeyboardButton(
                "✅ Уже включили",
                callback_data="vote_yes"
            ),
            InlineKeyboardButton(
                "❌ Ещё нет",
                callback_data="vote_no"
            )
        ]
    ])

# -------------------------
# Определение района
# -------------------------

def detect_region(text):

    low = (text or "").lower()

    for region in REGIONS:

        if region.lower() in low:
            return region

    return None

def detect_type(text):

    low = (text or "").lower()

    if any(x in low for x in [
        "электр",
        "свет",
        "elektr",
        "tok",
        "электроэнерг"
    ]):
        return "⚡ Свет"

    if any(x in low for x in [
        "газ",
        "gaz"
    ]):
        return "🔥 Газ"

    if any(x in low for x in [
        "вода",
        "suv",
        "водоснаб"
    ]):
        return "💧 Вода"

    return "📢 Сообщение"

# -------------------------
# Публикация
# -------------------------

async def publish(text, media=None):

    if text in last_messages:
        return

    last_messages.add(text)

    if len(last_messages) > 500:
        last_messages.clear()
        last_messages.add(text)

    try:

        if media:

            await bot.send_photo(
                CHANNEL_ID,
                media,
                caption=text,
                reply_markup=post_keyboard()
            )

        else:

            await bot.send_message(
                CHANNEL_ID,
                text,
                reply_markup=post_keyboard()
            )

    except Exception as e:
        logging.error(e)

# -------------------------
# TELETHON
# -------------------------

@client.on(events.NewMessage(chats=SOURCE_CHANNELS))
async def new_post(event):
    text = event.raw_text or ""

    logging.info(f"📨 Новый пост из: {event.chat.username}")
    

    logging.info(f"📥 Новый пост: {event.chat.username or event.chat_id}")
    logging.info(f"📝 Первые 80 символов: {text[:80]}")
    

    if not text.strip():
        return

    region = detect_region(text)
    outage = detect_type(text)

    message = f"{outage}\n"

    if region:
        message += f"📍 Район: {region}\n"

    message += "\n" + text

    media = None

    try:

        if event.photo:
            media = await event.download_media(file=bytes)

    except Exception:
        media = None

    await publish(message, media)

    if region:

        for uid, my_region in all_users():

            if my_region != region:
                continue

            personal = "🎯 ВАШ РАЙОН\n\n" + message

            try:

                if media:

                    await bot.send_photo(
                        uid,
                        media,
                        caption=personal
                    )

                else:

                    await bot.send_message(
                        uid,
                        personal
                    )

            except Exception:
                pass

# -------------------------
# Команды
# -------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🚨 BUGUN O'CHADI\n\nВыберите свой район.",
        reply_markup=region_keyboard()
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        f"📍 Ваш район: {get_region(update.effective_user.id) or 'не выбран'}"
    )

# -------------------------
# Кнопки
# -------------------------

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query
    await q.answer()

    data = q.data

    if data.startswith("region:"):

        region = data.split(":",1)[1]

        set_region(q.from_user.id, region)

        await q.edit_message_text(
            f"✅ Район выбран: {region}",
            reply_markup=region_keyboard()
        )

        return

    text = q.message.caption or q.message.text or ""
    key = text or str(q.message.message_id)

    if data == "my_region":

        my = get_region(q.from_user.id)

        if not my:
            await q.answer(
                "Сначала выберите район.",
                show_alert=True
            )
            return

        post_region = detect_region(text)

        if not post_region:
            await q.answer(
                "Район не найден.",
                show_alert=True
            )

        elif post_region == my:
            await q.answer(
                "🎯 Это ваш район!",
                show_alert=True
            )

        else:
            await q.answer(
                f"Пост про {post_region}. Ваш район {my}.",
                show_alert=True
            )

        return

    yes, no = vote(key, data == "vote_yes")

    await q.answer(
        f"👍 {yes} | 👎 {no}",
        show_alert=True
    )

# -------------------------
# Комментарии
# -------------------------

async def comments(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    text = update.message.text.lower()

    if "свет" in text:
        await update.message.reply_text("⚡ Проверяйте последние публикации.")

    elif "газ" in text:
        await update.message.reply_text("🔥 Проверяйте последние публикации.")

    elif "вода" in text:
        await update.message.reply_text("💧 Проверяйте последние публикации.")

    else:

        region = detect_region(text)

        if region:
            await update.message.reply_text(
                f"📍 Проверяйте публикации по району {region}."
            )
        else:
            await update.message.reply_text(
                "Напишите район, свет, газ или вода."
            )

# -------------------------
# Закреплённое меню
# -------------------------

async def send_channel_menu():

    try:

        await bot.send_message(
            CHANNEL_ID,
            "🚨 BUGUN O'CHADI\n\nВыберите свой район.",
            reply_markup=region_keyboard()
        )

    except Exception as e:
        logging.error(e)

# -------------------------
# Запуск Telethon
# -------------------------

async def run_telethon():

    while True:

        try:

            if not client.is_connected():
                await client.connect()

            from telethon.tl.functions.channels import JoinChannelRequest

            for channel in SOURCE_CHANNELS:
                try:
                    await client(JoinChannelRequest(channel))
            logging.info(f"Подписался на {channel}")
                except Exception:
                    pass
        
            logging.info("Telethon подключён")

            await client.run_until_disconnected()

        except Exception as e:

            logging.error(e)

            await asyncio.sleep(10)

# -------------------------
# Startup
# -------------------------

async def startup(app):

    asyncio.create_task(run_telethon())

    await send_channel_menu()

async def shutdown(app):

    await client.disconnect()

# -------------------------
# MAIN
# -------------------------

def main():

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(startup)
        .post_shutdown(shutdown)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS
            & filters.TEXT
            & ~filters.COMMAND,
            comments
        )
    )

    app.run_polling(
        drop_pending_updates=True,
        close_loop=False
    )

if __name__ == "__main__":
    main()
