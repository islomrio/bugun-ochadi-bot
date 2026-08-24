from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import os
import requests
import hashlib
from PIL import Image, ImageDraw, ImageFont
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
def create_card(service, district, streets, time_text, reason, status):
    width, height = 1080, 1350

    colors = {
        "red": (225, 55, 55),
        "green": (25, 160, 70),
        "white": (160, 160, 160)
    }

    color = colors.get(status, colors["red"])

    img = Image.new("RGB", (width, height), (10, 22, 45))
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 70)
        big_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 120)
        text_font = ImageFont.truetype("DejaVuSans.ttf", 42)
        small_font = ImageFont.truetype("DejaVuSans.ttf", 34)
    except:
        title_font = ImageFont.load_default()
        big_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    draw.rectangle((0,0,1080,250), fill=color)

    draw.text((60,40),"ПОДТВЕРЖДЕНО",fill="white",font=small_font)
    draw.text((60,90),service,fill="white",font=big_font)
    draw.text((60,200),"Плановое отключение",fill="white",font=text_font)

    y=320

    for title,value in [
        ("РАЙОН",district),
        ("МАХАЛЛИ / УЛИЦЫ",streets),
        ("ВРЕМЯ",time_text),
        ("ПРИЧИНА",reason)
    ]:
        draw.text((70,y),title,fill=(140,140,140),font=small_font)
        draw.text((70,y+45),value,fill="white",font=text_font)
        y+=140

    draw.rectangle((0,980,1080,1065),fill=(20,35,70))
    draw.text((60,1005),"СТАТУС:",fill="white",font=text_font)
    draw.ellipse((300,1002,340,1042),fill=color)

    draw.text((360,1005),
              "ПОДТВЕРЖДЕНО" if status=="red"
              else "РАБОТЫ ЗАВЕРШЕНЫ"
              if status=="green"
              else "ПРОВЕРЯЕТСЯ",
              fill="white",font=text_font)

    draw.text((60,1105),"BUGUN O'CHADI",fill=(255,215,0),font=title_font)
    draw.text((60,1185),"⚡ Свет   💧 Вода   🔥 Газ",fill="white",font=text_font)

    path="/tmp/card.png"
    img.save(path)

    return path
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
