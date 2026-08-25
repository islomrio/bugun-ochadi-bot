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

SESSION = "bugun_session"

SOURCE_CHANNELS = [
    "minenergy_uz",
    "AO_Hududgaztaminot",
    "uzsuv_chat",
]

bot = Bot(BOT_TOKEN)

client = TelegramClient(
    SESSION,
    API_ID,
    API_HASH,
)

user_regions = {}
last_messages = set()

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
    low = text.lower()
    for r in REGIONS:
        if r.lower() in low:
            return r
    return None


def detect_type(text):
    low = text.lower()

    if any(x in low for x in [
        "elektr",
        "электр",
        "svet",
        "свет",
        "tok",
        "электроэнерг",
    ]):
        return "⚡ Свет"

    if any(x in low for x in [
        "gaz",
        "газ",
    ]):
        return "🔥 Газ"

    if any(x in low for x in [
        "suv",
        "вода",
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

    if media:
        try:
            await bot.send_photo(
                CHANNEL_ID,
                media,
                caption=text,
            )
            return
        except Exception:
            pass

    await bot.send_message(
        CHANNEL_ID,
        text,
    )


@client.on(events.NewMessage(chats=SOURCE_CHANNELS))
async def new_post(event):
    text = event.raw_text or ""

    if not text.strip():
        return

    region = detect_region(text)
    outage = detect_type(text)

    caption = f"{outage}\n"

    if region:
        caption += f"📍 Район: {region}\n"

    caption += f"\n{text}"

    media = None

    try:
        if event.photo:
            media = await event.download_media(file=bytes)
    except Exception:
        media = None

    await publish(caption, media)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "BUGUN O'CHADI\n\n"
        "Напишите свой район.\n\n"
        "Например:\n"
        "Юнусабад"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.id
    region = user_regions.get(user, "не выбран")

    await update.message.reply_text(
        f"🟢 Монитор активен\n"
        f"📍 Район: {region}"
    )


async def save_region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    if text.startswith("/"):
        return

    user_regions[update.effective_user.id] = text

    await update.message.reply_text(
        f"✅ Район сохранён: {text}\n\n"
        "Теперь новые отключения будут автоматически отслеживаться."
    )


async def startup(app: Application):
    try:
        await client.connect()

        if not await client.is_user_authorized():
            logging.error("Telethon не авторизован.")
            return

        logging.info("Telethon подключён.")
    except Exception as e:
        logging.error(f"Ошибка запуска Telethon: {e}")


async def shutdown(app: Application):
    await client.disconnect()


async def run_telethon():
    await client.start()
    await client.run_until_disconnected()


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
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            save_region,
        )
    )

    asyncio.get_event_loop().create_task(run_telethon())

    app.run_polling(drop_pending_updates=True, close_loop=False)


if __name__ == "__main__":
    main()
