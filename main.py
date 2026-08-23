from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
import requests

TOKEN = os.getenv("BOT_TOKEN")

# СЮДА ПОТОМ ВСТАВИМ ССЫЛКУ ДЛЯ МОНИТОРИНГА
CHECK_URL = "https://example.com"

last_state = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chats = context.application.bot_data.setdefault("chats", set())
    chats.add(update.effective_chat.id)

    await update.message.reply_text(
        "BUGUN O'CHADI MONITOR\n\nБот работает."
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 Монитор активен")

async def monitor(context: ContextTypes.DEFAULT_TYPE):
    global last_state

    try:
        response = requests.get(CHECK_URL, timeout=20)
        current_state = response.text

        if last_state is None:
            last_state = current_state
            return

        if current_state != last_state:
            last_state = current_state

            for chat_id in context.application.bot_data.get("chats", set()):
                await context.bot.send_message(
                    chat_id,
                    "🚨 На сайте обнаружено изменение!"
                )
    except Exception as e:
        print(e)

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("status", status))

app.job_queue.run_repeating(monitor, interval=60, first=10)

app.run_polling()
