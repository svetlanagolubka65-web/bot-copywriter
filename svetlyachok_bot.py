import asyncio
import json
import os
import random
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

load_dotenv()

SVETLYACHOK_BOT_TOKEN = os.getenv("SVETLYACHOK_BOT_TOKEN")
ACCESS_CODE = os.getenv("ACCESS_CODE", "").strip()
CONSULT_LINK_URL = os.getenv("CONSULT_LINK_URL", "").strip()
LESSONS_URL = os.getenv("LESSONS_URL", "").strip()
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

ACCESS_FILE = "svetlyachok_access.json"


# --- Доступ по коду курса ---
# Код общий на весь поток (см. ACCESS_CODE в .env). Если код не задан — бот открыт всем
# (удобно для локальной проверки), как и ADMIN_IDS в bot.py/intake_bot.py.

def load_allowed_users() -> set:
    if os.path.exists(ACCESS_FILE):
        with open(ACCESS_FILE, "r") as f:
            return set(json.load(f))
    return set()


def grant_access(user_id: int):
    allowed = load_allowed_users()
    allowed.add(user_id)
    with open(ACCESS_FILE, "w") as f:
        json.dump(list(allowed), f)


def has_access(user_id: int) -> bool:
    return not ACCESS_CODE or user_id in load_allowed_users()


# --- Контент разделов ---
# Промпты ниже — стартовый пример, чтобы разделы не были пустыми.
# Дополняй/заменяй своими под реальные темы курса.

SECTIONS = {
    "image": {
        "emoji": "🖼",
        "title": "Создать картинку",
        "intro": "Выберите готовый промпт — скопируйте текст целиком и вставьте в Kandinsky, Шедеврум или Midjourney.",
        "items": [
            (
                "Тёплый портрет",
                "Портрет женщины с добрыми глазами и лёгкой улыбкой, мягкий тёплый свет, "
                "стиль классической масляной живописи, высокая детализация, спокойный фон.",
            ),
            (
                "Праздничная открытка",
                "Праздничная открытка с весенними цветами и золотыми лентами, место для текста "
                "оставить пустым по центру, яркие тёплые тона, реалистичный стиль.",
            ),
        ],
    },
    "video": {
        "emoji": "🎥",
        "title": "Сделать видео",
        "intro": "Готовые идеи для видео из фото — сервисы вроде Kling или Pika оживляют одну фотографию по описанию.",
        "items": [
            (
                "Оживить фото",
                "Оживи это фото: лёгкая улыбка, спокойный поворот головы, мягкое покачивание волос "
                "на ветру, без резких движений, сохранить лицо и одежду без изменений.",
            ),
            (
                "Видео-поздравление",
                "Короткое видео 5 секунд: человек на фото радостно машет рукой в камеру на фоне "
                "праздничных огней, тёплое освещение, плавное движение.",
            ),
        ],
    },
    "song": {
        "emoji": "🎵",
        "title": "Написать песню",
        "intro": "Готовые заготовки для Suno — впишите своё имя, повод или детали вместо примера.",
        "items": [
            (
                "Песня на день рождения",
                "Тёплая душевная песня на день рождения для мамы, тёплый женский вокал, "
                "акустическая гитара, куплет о её доброте и заботе, припев с пожеланием счастья.",
            ),
            (
                "Песня-посвящение",
                "Лирическая песня-посвящение близкому человеку, спокойный мужской вокал, "
                "фортепиано, тема благодарности и тёплых воспоминаний.",
            ),
        ],
    },
    "chatgpt": {
        "emoji": "💬",
        "title": "Освоить ChatGPT",
        "intro": (
            "Мини-урок: как писать запросы, чтобы ChatGPT понимал с первого раза.\n\n"
            "1️⃣ Скажите, кто вы и для чего нужен результат — «Я бабушка, хочу написать поздравление внуку».\n"
            "2️⃣ Опишите, что должно получиться — тон, длину, детали.\n"
            "3️⃣ Если ответ не подошёл — напишите «сделай короче» или «сделай теплее», ChatGPT переделает.\n\n"
            "Попробуйте прямо сейчас: откройте chat.openai.com и напишите первую фразу своими словами.",
        ),
        "items": [],
    },
    "lesson": {
        "emoji": "📚",
        "title": "Найти урок",
        "intro": None,
        "items": [],
    },
    "network": {
        "emoji": "🤖",
        "title": "Выбрать нейросеть",
        "intro": (
            "Коротко, что для чего использовать:\n\n"
            "✍️ Текст, письма, идеи — ChatGPT\n"
            "🖼 Картинки — Kandinsky, Шедеврум, Midjourney\n"
            "🎵 Музыка и песни — Suno\n"
            "🎥 Видео из фото — Kling, Pika\n\n"
            "Если не уверены — нажмите «👩 Позвать Светлану», подскажу лично.",
        ),
        "items": [],
    },
}

MAIN_MENU_BUTTONS = [
    ["🖼 Создать картинку", "🎥 Сделать видео"],
    ["🎵 Написать песню", "💬 Освоить ChatGPT"],
    ["📚 Найти урок", "💡 Получить промпт"],
    ["🤖 Выбрать нейросеть", "👩 Позвать Светлану"],
]

BUTTON_TO_SECTION = {
    "🖼 Создать картинку": "image",
    "🎥 Сделать видео": "video",
    "🎵 Написать песню": "song",
    "💬 Освоить ChatGPT": "chatgpt",
    "📚 Найти урок": "lesson",
    "🤖 Выбрать нейросеть": "network",
}

GREETING = (
    "Здравствуйте! 👋 Я Светлячок — помощник «НейроСветы».\n"
    "Что вы хотите сделать сегодня? Выберите на клавиатуре ниже 👇"
)


def main_menu_keyboard():
    return ReplyKeyboardMarkup(MAIN_MENU_BUTTONS, resize_keyboard=True)


def items_keyboard(section_key: str):
    section = SECTIONS[section_key]
    keyboard = [
        [InlineKeyboardButton(title, callback_data=f"item_{section_key}_{i}")]
        for i, (title, _) in enumerate(section["items"])
    ]
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_menu")])
    return InlineKeyboardMarkup(keyboard)


def back_menu_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="back_menu")]])


async def _notify_admins(context: ContextTypes.DEFAULT_TYPE, text: str):
    for chat_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id, text)
        except Exception:
            pass


# --- Доступ: код курса ---

async def _ask_for_code(chat, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "awaiting_code"
    await chat.send_message(
        "Этот бот доступен участникам курса «НейроСвета».\n"
        "Введите код доступа, который дала вам Светлана:"
    )


async def _check_code(chat, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    if text.strip().lower() == ACCESS_CODE.lower():
        grant_access(user_id)
        context.user_data["mode"] = None
        await chat.send_message("Код верный, добро пожаловать! 🎉")
        await chat.send_message(GREETING, reply_markup=main_menu_keyboard())
    else:
        await chat.send_message("Такой код не найден. Проверьте, пожалуйста, и введите ещё раз:")


# --- Разделы ---

async def _show_section(chat, section_key: str):
    section = SECTIONS[section_key]
    intro = section["intro"]

    if section_key == "lesson":
        if LESSONS_URL:
            await chat.send_message(
                f"Здесь собраны уроки и материалы курса:\n{LESSONS_URL}",
                reply_markup=back_menu_keyboard(),
            )
        else:
            await chat.send_message(
                "Ссылка на уроки скоро появится здесь. Пока можно спросить нужную тему у Светланы.",
                reply_markup=back_menu_keyboard(),
            )
        return

    if not section["items"]:
        await chat.send_message(intro, reply_markup=back_menu_keyboard())
        return

    await chat.send_message(intro, reply_markup=items_keyboard(section_key))


async def _show_item(chat, section_key: str, index: int):
    section = SECTIONS[section_key]
    if index < 0 or index >= len(section["items"]):
        await _show_section(chat, section_key)
        return
    title, prompt = section["items"][index]
    await chat.send_message(
        f"{section['emoji']} *{title}*\n\n{prompt}",
        parse_mode="Markdown",
        reply_markup=back_menu_keyboard(),
    )


async def _show_random_prompt(chat):
    all_items = [
        (key, title, prompt)
        for key, section in SECTIONS.items()
        for title, prompt in section["items"]
    ]
    if not all_items:
        await chat.send_message("Пока промптов нет — загляните позже.", reply_markup=back_menu_keyboard())
        return
    key, title, prompt = random.choice(all_items)
    emoji = SECTIONS[key]["emoji"]
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 Ещё промпт", callback_data="random_prompt")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_menu")],
    ])
    await chat.send_message(f"{emoji} *{title}*\n\n{prompt}", parse_mode="Markdown", reply_markup=keyboard)


async def _call_svetlana(chat, context: ContextTypes.DEFAULT_TYPE, user_label: str):
    if CONSULT_LINK_URL:
        text = f"Вот ссылка на запись к Светлане — выберите удобное время:\n{CONSULT_LINK_URL}"
    else:
        text = "Напишите Светлане лично — она ответит вам в этом же Telegram."
    await chat.send_message(text, reply_markup=back_menu_keyboard())
    await _notify_admins(context, f"👩 {user_label} нажал(а) «Позвать Светлану» в Светлячке.")


# --- Команды ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    chat = update.effective_chat
    user_id = update.effective_user.id

    if not has_access(user_id):
        await _ask_for_code(chat, context)
        return

    await chat.send_message(GREETING, reply_markup=main_menu_keyboard())


# --- Основная логика сообщений ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user
    username = getattr(user, "username", None)
    user_label = f"@{username}" if username else (user.first_name or "участник")
    chat = update.message.chat

    if not has_access(user.id):
        if context.user_data.get("mode") == "awaiting_code":
            await _check_code(chat, context, user.id, text)
        else:
            await _ask_for_code(chat, context)
        return

    if text == "💡 Получить промпт":
        await _show_random_prompt(chat)
        return

    if text == "👩 Позвать Светлану":
        await _call_svetlana(chat, context, user_label)
        return

    section_key = BUTTON_TO_SECTION.get(text)
    if section_key:
        await _show_section(chat, section_key)
        return

    await chat.send_message(GREETING, reply_markup=main_menu_keyboard())


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    chat = query.message.chat

    if action == "back_menu":
        await chat.send_message(GREETING, reply_markup=main_menu_keyboard())
        return

    if action == "random_prompt":
        await _show_random_prompt(chat)
        return

    if action.startswith("item_"):
        _, section_key, index = action.split("_", 2)
        await _show_item(chat, section_key, int(index))
        return


def main():
    asyncio.set_event_loop(asyncio.new_event_loop())
    app = Application.builder().token(SVETLYACHOK_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Светлячок запущен. Нажми Ctrl+C чтобы остановить.")
    app.run_polling()


if __name__ == "__main__":
    main()
