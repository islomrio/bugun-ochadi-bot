from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
import requests

TOKEN = os.getenv("BOT_TOKEN")
DISTRICTS = {
    "Юнусабад": ["yunusobod", "yunusabad", "юнусабад"],
    "Чиланзар": ["chilonzor", "chilanzar", "чиланзар"],
    "Мирабад": ["mirobod", "mirabad", "мирабад"],
    "Мирзо-Улугбек": ["mirzo ulugbek", "mirzo-ulugbek", "мирзо улугбек"],
    "Шайхантахур": ["shayxontohur", "shaykhantakhur", "шайхантахур"],
    "Алмазар": ["olmazor", "almazar", "алмазар"],
    "Сергелий": ["sergeli", "сергелий"],
    "Яккасарай": ["yakkasaroy", "якасарай", "яккасарай"],
    "Яшнабад": ["yashnobod", "яшнабад"],
    "Учтепа": ["uchtepa", "учтепа"],
    "Бектемир": ["bektemir", "бектемир"],
    "Янгихаёт": ["yangihayot", "янгихаёт"]
}
# СЮДА ПОТОМ ВСТАВИМ ССЫЛКУ ДЛЯ МОНИТОРИНГА
CHECK_URL = "https://www.het.uz/en/lists"

last_state = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chats = context.application.bot_data.setdefault("chats", set())
    chats.add(update.effective_chat.id)

    await update.message.reply_text(
        "BUGUN O'CHADI MONITOR\n\nБот работает."
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 Монитор активен")
async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚨 Тестовое уведомление. Всё работает.")
KEYWORDS = [
    "bugun o‘chadi",
    "bugun o'chadi",
    "bugun",
    "o‘chiriladi",
    "o'chiriladi",
    "отключение",
    "отключат"
]
SOURCES = {
    "⚡ Свет": "https://www.het.uz/en/lists",
    "💧 Вода": "https://veoliaenergy.uz/",
    "🔥 Газ": "https://hududgaz.uz/"
}

last_states = {}

async def monitor(context: ContextTypes.DEFAULT_TYPE):
    global last_states

    for name, url in SOURCES.items():
        try:
            response = requests.get(url, timeout=20)
            text = response.text.lower()
            current_state = "|".join([k for k in KEYWORDS if k in text]) 

            if url not in last_states:
                last_states[url] = current_state
                continue

            if current_state != last_states[url]:
                last_states[url] = current_state

                for chat_id in context.application.bot_data["chats"]:
                    await context.bot.send_message(
                        chat_id,
                        f"🚨 {name}\n\nОбнаружено изменение на официальном сайте.\n{url}"
                    )

        except Exception as e:
            print(e)

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("test", test))
app.job_queue.run_repeating(monitor, interval=60, first=10)

app.run_polling()
