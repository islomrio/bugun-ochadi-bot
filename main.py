from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
import requests
import hashlib
import os

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
DISTRICTS = {
    "Юнусабад": ["yunusobod", "yunusabad", "юнусабад"],
    "Чиланзар": ["chilonzor", "chilanzar", "чиланзар"],
    "Мирабад": ["mirobod", "mirabad", "мирабад"],
    "Мирзо-Улугбек": ["mirzo ulugbek", "mirzo-ulugbek", "мирзо улугбек"],
    "Шайхантахур": ["shayxontohur", "shaykhantakhur", "шайхантахур"],
    "Алмазар": ["olmazor", "almazar", "алмазар"],
    "Сергелий": ["sergeli", "сергелий"],
    "Яккасарай": ["yakkasaroy", "яккасарай"],
    "Яшнабад": ["yashnobod", "яшнабад"],
    "Учтепа": ["uchtepa", "учтепа"],
    "Бектемир": ["bektemir", "бектемир"],
    "Янгихаёт": ["yangihayot", "янгихаёт"],
}

SOURCES = {
    "⚡ Свет": "https://www.het.uz/en/lists",
    "💧 Вода": "https://veoliaenergy.uz/",
    "🔥 Газ": "https://hududgaz.uz/",
}

last_states = {}
sent_hashes = set()

# ---------- Карточка ----------

def create_card(service, district):
    img = Image.new("RGB", (1080, 1350), (10, 22, 45))
    draw = ImageDraw.Draw(img)

    try:
        title = ImageFont.truetype("DejaVuSans-Bold.ttf", 80)
        text = ImageFont.truetype("DejaVuSans.ttf", 42)
    except:
        title = ImageFont.load_default()
        text = ImageFont.load_default()

    draw.rectangle((0, 0, 1080, 220), fill=(225, 55, 55))

    draw.text((50, 45), service, fill="white", font=title)
    draw.text((50, 290), f"Район: {district}", fill="white", font=text)
    draw.text((50, 370), "Плановое отключение", fill="white", font=text)

    draw.text((50, 1180), "BUGUN O'CHADI", fill=(255, 215, 0), font=title)

    path = "/tmp/card.png"
    img.save(path)
    return path

# ---------- Команды ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    users = context.application.bot_data.setdefault("users", {})
    users.setdefault(update.effective_chat.id, None)

    keyboard = [
        ["Юнусабад", "Чиланзар"],
        ["Мирабад", "Мирзо-Улугбек"],
        ["Шайхантахур", "Алмазар"],
        ["Сергелий", "Яккасарай"],
        ["Яшнабад", "Учтепа"],
        ["Бектемир", "Янгихаёт"],
    ]

    await update.message.reply_text(
        "BUGUN O'CHADI MONITOR\n\nВыберите район:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 Монитор активен")

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    card = create_card("⚡ Свет", "Юнусабад")
    with open(card, "rb") as photo:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=photo,
            caption="Тестовая карточка.",
        )

async def choose_district(update: Update, context: ContextTypes.DEFAULT_TYPE):

    district = update.message.text

    if district not in DISTRICTS:
        return

    users = context.application.bot_data.setdefault("users", {})
    users[update.effective_chat.id] = district

    await update.message.reply_text(
        f"✅ Район сохранён: {district}"
    )

# ---------- Монитор ----------

async def monitor(context: ContextTypes.DEFAULT_TYPE):

    users = context.application.bot_data.setdefault("users", {})

    for service, url in SOURCES.items():

        try:
            response = requests.get(
                url,
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0"},
            )

            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")
            text = soup.get_text(" ", strip=True).lower()

            state = hashlib.md5(text.encode()).hexdigest()

            if last_states.get(url) == state:
                continue

            last_states[url] = state

            for chat_id, district in users.items():

                if not district:
                    continue

                aliases = DISTRICTS.get(district, [])

                if any(alias in text for alias in aliases):

                    msg_hash = hashlib.md5(
                        f"{chat_id}:{url}:{state}".encode()
                    ).hexdigest()

                    if msg_hash in sent_hashes:
                        continue

                    sent_hashes.add(msg_hash)

                    card = create_card(service, district)

                    with open(card, "rb") as photo:
                        await context.bot.send_photo(
                            chat_id=chat_id,
                            photo=photo,
                            caption=f"{service}: найдено новое обновление.",
                        )

        except Exception as e:
            print(f"[{service}] {e}")

# ---------- Запуск ----------

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("test", test))
app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, choose_district)
)

app.job_queue.run_repeating(
    monitor,
    interval=60,
    first=10,
)

app.run_polling(drop_pending_updates=True)
