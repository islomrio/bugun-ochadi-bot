from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import os
import requests
import hashlib
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
    users = context.application.bot_data.setdefault("users", {})
    users.setdefault(update.effective_chat.id, None)
    keyboard = [
    ["Юнусабад", "Чиланзар"],
    ["Мирабад", "Мирзо-Улугбек"],
    ["Шайхантахур", "Алмазар"],
    ["Сергелий", "Яккасарай"],
    ["Яшнабад", "Учтепа"],
    ["Бектемир", "Янгихаёт"]
]

    await update.message.reply_text(
    "BUGUN O'CHADI MONITOR\n\nВыберите свой район:",
    reply_markup=ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )
)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 Монитор активен")
async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚨 Тестовое уведомление. Всё работает.")
async def choose_district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text not in DISTRICTS:
        return

    users = context.application.bot_data.setdefault("users", {})
    users[update.effective_chat.id] = text

    await update.message.reply_text(
        f"✅ Район сохранён: {text}\n\nТеперь буду присылать уведомления только по этому району."
    )
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
sent_hashes = set()
async def monitor(context: ContextTypes.DEFAULT_TYPE):
    global last_states, sent_hashes

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
                msg_hash = hashlib.md5(f"{name}:{current_state}".encode()).hexdigest()
                if msg_hash in sent_hashes:
                    continue
                sent_hashes.add(msg_hash)
                users = context.application.bot_data.get("users", {})

            for chat_id, district in users.items():
                aliases = DISTRICTS.get(district, [])

                if any(alias.lower() in text for alias in aliases):
                    await context.bot.send_message(
                        chat_id,
                        f"🚨 {name}\n\nОбнаружено изменение по району {district}.\n{url}"
                    )

        except Exception as e:
            print(e)

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("test", test))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, choose_district))
app.job_queue.run_repeating(monitor, interval=60, first=10)

app.run_polling()
