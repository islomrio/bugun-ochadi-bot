import os
import asyncio
import logging

from telegram import Bot, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
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

SOURCE_CHANNELS = [
    "minenergy_uz",
    "AO_Hududgaztaminot",
    "uzsuv_chat",
]

bot = Bot(BOT_TOKEN)

client = TelegramClient(
    StringSession(STRING_SESSION),
    API_ID,
    API_HASH,
)

last_messages = set()
user_regions = {}

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
]


def detect_region(text):
    text = text.lower()
    for r in REGIONS:
        if r.lower() in text:
            return r
    return None


def detect_type(text):
    text = text.lower()

    if any(x in text for x in [
        "электр",
        "свет",
        "tok",
        "elektr",
        "электроэнерг",
    ]):
        return "⚡ Свет"

    if any(x in text for x in [
        "газ",
        "gaz",
    ]):
        return "🔥 Газ"

    if any(x in text for x in [
        "вода",
        "suv",
        "водоснаб",
    ]):
        return "💧 Вода"

    return "📢 Сообщение"


async def publish(text, media=None):
    if text in last_messages:
        return

    last_messages.add(text)

    if len(last_messages) > 300:
        last_messages.clear()
        last_messages.add(text)

    try:
        if media:
            await bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=media,
                caption=text,
            )
        else:
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=text,
            )
    except Exception as e:
        logging.error(f"Ошибка публикации: {e}")


@client.on(events.NewMessage(chats=SOURCE_CHANNELS))
async def new_post(event):
    text = event.raw_text or ""

    if not text.strip():
        return

    region = detect_region(text)
    outage = detect_type(text)

    message = f"{outage}\n"

    if region:
        message += f"📍 Район: {region}\n"

    message += f"\n{text}"

    media = None

    try:
        if event.photo:
            media = await event.download_media(file=bytes)
    except Exception:
        media = None

    await publish(message, media)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Добро пожаловать в BUGUN O'CHADI.\n\n"
        "Напишите свой район.\n\n"
        "Например:\n"
        "Юнусабад"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    region = user_regions.get(update.effective_user.id, "не выбран")

    await update.message.reply_text(
        f"🟢 Монитор работает.\n"
        f"📍 Район: {region}"
    )


async def save_region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    text = update.message.text.strip()

    if text.startswith("/"):
        return

    user_regions[update.effective_user.id] = text

    await update.message.reply_text(
        f"✅ Район сохранён: {text}\n\n"
        "Теперь новые отключения будут автоматически отслеживаться."
    )


async def comments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    text = update.message.text.lower()

    if "свет" in text:
        await update.message.reply_text(
            "⚡ Проверяю последние отключения света..."
        )
        return

    if "газ" in text:
        await update.message.reply_text(
            "🔥 Проверяю последние отключения газа..."
        )
        return

    if "вода" in text:
        await update.message.reply_text(
            "💧 Проверяю последние отключения воды..."
        )
        return

    region = detect_region(text)

    if region:
        await update.message.reply_text(
            f"📍 Проверяю отключения в районе {region}..."
        )
        return

    await update.message.reply_text(
        "Напишите: свет, газ, вода или название района."
    )


async def run_telethon():
    try:
        await client.connect()
        logging.info("Telethon запущен.")
        await client.run_until_disconnected()
    except Exception as e:
        logging.error(f"Ошибка Telethon: {e}")


async def startup(app: Application):
    asyncio.create_task(run_telethon())


async def shutdown(app: Application):
    await client.disconnect()


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

    # Личные сообщения
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE
            & filters.TEXT
            & ~filters.COMMAND,
            save_region,
        )
    )

    # Комментарии группы обсуждений
    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS
            & filters.TEXT
            & ~filters.COMMAND,
            comments,
        )
    )

    app.run_polling(
        drop_pending_updates=True,
        close_loop=False,
    )


if __name__ == "__main__":
    main()
