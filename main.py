import os
import re
import json
import hashlib
import logging
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ======================================
# НАСТРОЙКИ
# ======================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

CHECK_INTERVAL = 60
CARD_TEMPLATE = "F50D7071-D459-4E81-BDA8-A30C0A0BDA56.png"
CACHE_FILE = "storage.json"

DISTRICTS = {
    "Юнусабад": ["yunusobod","yunusabad","юнусабад"],
    "Чиланзар": ["chilonzor","chilanzar","чиланзар"],
    "Мирабад": ["mirobod","mirabad","мирабад"],
    "Мирзо-Улугбек": ["mirzo ulugbek","mirzo-ulugbek","мирзо улугбек"],
    "Шайхантахур": ["shayxontohur","шайхантахур"],
    "Алмазар": ["olmazor","алмазар"],
    "Сергелий": ["sergeli","сергелий"],
    "Яккасарай": ["yakkasaroy","яккасарай"],
    "Яшнабад": ["yashnobod","яшнабад"],
    "Учтепа": ["uchtepa","учтепа"],
    "Бектемир": ["bektemir","бектемир"],
    "Янгихаёт": ["yangihayot","янгихаёт"],
}

# Официальные источники

SOURCES = {
    "⚡ Свет": "https://www.het.uz/en/lists/category/33",
    "💧 Вода": "https://veoliaenergy.uz/ru",
}

# ======================================
# КЭШ
# ======================================

last_states = {}

def load_cache():

    if not os.path.exists(CACHE_FILE):
        return {"sent":[]}

    try:
        with open(CACHE_FILE,"r",encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"sent":[]}


def save_cache(cache):

    with open(CACHE_FILE,"w",encoding="utf-8") as f:
        json.dump(cache,f,ensure_ascii=False,indent=2)


cache = load_cache()

MAX_CACHE = 300

def remember_hash(h):

    if h not in cache["sent"]:
        cache["sent"].append(h)
        cache["sent"]=cache["sent"][-MAX_CACHE:]
        save_cache(cache)

# ======================================
# КАРТОЧКА
# ======================================

def create_card(service,district,reason="",time_text=""):

    template=os.path.join(
        os.path.dirname(__file__),
        CARD_TEMPLATE
    )

    img=Image.open(template).convert("RGB")

    draw=ImageDraw.Draw(img)

    try:
        title=ImageFont.truetype("DejaVuSans-Bold.ttf",54)
        text=ImageFont.truetype("DejaVuSans-Bold.ttf",42)
        small=ImageFont.truetype("DejaVuSans.ttf",30)
    except:
        title=ImageFont.load_default()
        text=ImageFont.load_default()
        small=ImageFont.load_default()

    draw.text((250,338),service.upper(),fill="white",font=title)
    draw.text((250,545),district.upper(),fill="white",font=text)

    if time_text:
        draw.text((120,760),f"🕒 {time_text}",fill="white",font=small)

    if reason:
        draw.text((120,820),reason[:60],fill="white",font=small)

    path="/tmp/card.png"
    img.save(path)

    return path

# ======================================
# ПАРСЕР
# ======================================

def clean_text(text):

    return re.sub(r"\s+"," ",text).strip()


def detect_district(text):

    text=text.lower()

    for district,aliases in DISTRICTS.items():

        if any(a in text for a in aliases):
            return district

    return None


def extract_time(text):

    m=re.search(
        r"\d{1,2}[:.]\d{2}\s*[-–]\s*\d{1,2}[:.]\d{2}",
        text
    )

    if m:
        return m.group(0)

    return ""


def extract_reason(service):

    if "Свет" in service:
        return "Плановые работы"

    if "Вода" in service:
        return "Технические работы"

    return "Официальное сообщение"


def parse_official_page(service,url):

    r=requests.get(
        url,
        timeout=20,
        headers={"User-Agent":"Mozilla/5.0"}
    )

    if r.status_code!=200:
        raise Exception(f"HTTP {r.status_code}")

    soup=BeautifulSoup(r.text,"lxml")

    text=clean_text(
        soup.get_text(" ",strip=True)
    )

    district=detect_district(text)

    if not district:
        return None

    return {
        "service":service,
        "district":district,
        "time":extract_time(text),
        "reason":extract_reason(service),
        "hash":hashlib.md5(text.encode()).hexdigest()
    }

# ======================================
# TELEGRAM
# ======================================

async def send_card(context,chat_id,data):

    card=create_card(
        data["service"],
        data["district"],
        data["reason"],
        data["time"]
    )

    caption=(
        f"{data['service']}\n\n"
        f"📍 Район: {data['district']}\n"
    )

    if data["time"]:
        caption+=f"🕒 Время: {data['time']}\n"

    caption+=(
        f"🛠 Причина: {data['reason']}\n\n"
        "Источник: официальный оператор\n"
        "#BugunOchadi"
    )

    with open(card,"rb") as photo:

        await context.bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=caption
        )

# ======================================
# КОМАНДЫ
# ======================================

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    users=context.application.bot_data.setdefault("users",{})

    users.setdefault(
        update.effective_chat.id,
        None
    )

    keyboard=[
        ["Юнусабад","Чиланзар"],
        ["Мирабад","Мирзо-Улугбек"],
        ["Шайхантахур","Алмазар"],
        ["Сергелий","Яккасарай"],
        ["Яшнабад","Учтепа"],
        ["Бектемир","Янгихаёт"],
    ]

    await update.message.reply_text(
        "BUGUN O'CHADI\n\nВыберите район:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        )
    )


async def status(update:Update,context:ContextTypes.DEFAULT_TYPE):

    users=context.application.bot_data.setdefault("users",{})

    district=users.get(
        update.effective_chat.id,
        "не выбран"
    )

    await update.message.reply_text(
        f"🟢 Монитор активен\n📍 Район: {district}"
    )


async def choose_district(update:Update,context:ContextTypes.DEFAULT_TYPE):

    district=update.message.text

    if district not in DISTRICTS:
        return

    users=context.application.bot_data.setdefault("users",{})

    users[update.effective_chat.id]=district

    await update.message.reply_text(
        f"✅ Район сохранён: {district}"
    )


async def test(update:Update,context:ContextTypes.DEFAULT_TYPE):

    data={
        "service":"⚡ Свет",
        "district":"Юнусабад",
        "time":"09:00–17:00",
        "reason":"Плановые работы"
    }

    await send_card(
        context,
        update.effective_chat.id,
        data
    )

    if CHANNEL_ID:
        await send_card(
            context,
            CHANNEL_ID,
            data
        )
        # ======================================
# МОНИТОР
# ======================================

async def monitor(context: ContextTypes.DEFAULT_TYPE):

    users = context.application.bot_data.setdefault("users", {})

    for service, url in SOURCES.items():

        try:
            data = parse_official_page(service, url)

            if not data:
                continue

            # Если состояние страницы не изменилось — пропускаем
            if last_states.get(service) == data["hash"]:
                continue

            last_states[service] = data["hash"]

            # Защита от дублей после перезапуска
            if data["hash"] in cache["sent"]:
                continue

            remember_hash(data["hash"])

            # Публикация в канал
            if CHANNEL_ID:
                try:
                    await send_card(context, CHANNEL_ID, data)
                    logging.info(f"Канал: опубликовано {service}")
                except Exception as e:
                    logging.error(f"Ошибка канала: {e}")

            # Личные уведомления только нужному району
            for chat_id, district in users.items():

                if district == data["district"]:
                    try:
                        await send_card(context, chat_id, data)
                    except Exception as e:
                        logging.error(f"Ошибка пользователю {chat_id}: {e}")

        except Exception as e:
            logging.error(f"{service}: {e}")


# ======================================
# ДОПОЛНИТЕЛЬНЫЕ КОМАНДЫ
# ======================================

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "📡 BUGUN O'CHADI\n\n"
        "Источники:\n"
        "⚡ HET (официальный список)\n"
        "💧 Veolia (официальные новости)\n\n"
        "Газ временно не подключён автоматически,\n"
        "потому что у Hududgaz нет стабильного публичного списка отключений."
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):

    users = context.application.bot_data.setdefault("users", {})

    users[update.effective_chat.id] = None

    await update.message.reply_text(
        "♻️ Район сброшен.\n\nИспользуйте /start."
    )


# ======================================
# ИНИЦИАЛИЗАЦИЯ
# ======================================

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("test", test))
app.add_handler(CommandHandler("info", info))
app.add_handler(CommandHandler("reset", reset))

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        choose_district
    )
)

app.job_queue.run_repeating(
    monitor,
    interval=CHECK_INTERVAL,
    first=15
)

logging.info("BUGUN O'CHADI запущен.")

app.run_polling(
    drop_pending_updates=True
)
