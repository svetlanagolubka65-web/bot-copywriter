import os
import json
from dotenv import load_dotenv
from groq import Groq
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
USERS_FILE = "users.json"

groq_client = Groq(api_key=GROQ_API_KEY)


# --- Хранилище пользователей (новый / вернувшийся) ---

def load_users() -> set:
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_user(user_id: int):
    users = load_users()
    users.add(user_id)
    with open(USERS_FILE, "w") as f:
        json.dump(list(users), f)

def is_new_user(user_id: int) -> bool:
    return user_id not in load_users()


# --- Меню ---

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["📝 Написать пост", "🎙 Голосовой ввод"],
        ["📖 Описание курса", "🎬 Сторис-сценарий"],
        ["💡 Заголовки", "📊 Моя история"],
        ["❓ Помощь"],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выбери формат или напиши тему..."
)

CONTENT_TYPES = {
    "📝 Написать пост": {
        "ask": (
            "📝 *Написать пост*\n\n"
            "Напиши тему — и я создам готовый пост для Telegram или Instagram.\n\n"
            "Примеры тем:\n"
            "• «как начать вайбкодить без знания кода»\n"
            "• «почему ИИ меняет правила игры для фрилансеров»\n"
            "• «мой первый проект за 2 часа без программиста»\n\n"
            "✏️ Напиши свою тему:"
        ),
        "prompt": "Напиши вовлекающий пост для Telegram/Instagram на тему вайбкодинга. Тема: {topic}. Длина 150–250 слов, живой тон, начни с цепляющего заголовка, закончи вопросом к аудитории. Добавь 2–3 эмодзи.",
        "label": "пост"
    },
    "🎙 Голосовой ввод": {
        "ask": (
            "🎙 *Голосовой ввод*\n\n"
            "Надиктуй тему голосом — я расшифрую и создам пост.\n\n"
            "Как записать голосовое:\n"
            "• На телефоне — нажми и *удержи* значок 🎤 в поле ввода\n"
            "• Говори тему 5–15 секунд\n"
            "• Отпусти — сообщение отправится автоматически\n\n"
            "🎤 Записывай!"
        ),
        "prompt": "Напиши вовлекающий пост для Telegram/Instagram на тему вайбкодинга. Тема: {topic}. Длина 150–250 слов, живой тон, начни с цепляющего заголовка, закончи вопросом к аудитории. Добавь 2–3 эмодзи.",
        "label": "пост из голоса"
    },
    "📖 Описание курса": {
        "ask": (
            "📖 *Описание курса*\n\n"
            "Напиши название или тему курса — я составлю продающее описание.\n\n"
            "Примеры:\n"
            "• «Вайбкодинг для предпринимателей»\n"
            "• «Автоматизация бизнеса с ИИ за 30 дней»\n"
            "• «Создай своего ИИ-ассистента без кода»\n\n"
            "✏️ Напиши название курса:"
        ),
        "prompt": "Напиши продающее описание онлайн-курса по вайбкодингу. Курс: {topic}. Включи: для кого курс, что получит студент, 3–4 ключевых блока, призыв записаться. Длина 150–250 слов. Тон вдохновляющий.",
        "label": "описание курса"
    },
    "🎬 Сторис-сценарий": {
        "ask": (
            "🎬 *Сторис-сценарий*\n\n"
            "Напиши тему или идею — я напишу готовый сценарий из 4–5 слайдов.\n\n"
            "Примеры:\n"
            "• «как я автоматизировала рутину за выходные»\n"
            "• «3 инструмента ИИ которые экономят 5 часов в неделю»\n"
            "• «почему я перестала бояться программирования»\n\n"
            "✏️ Напиши тему сторис:"
        ),
        "prompt": "Напиши сценарий для Instagram/Telegram Stories на тему вайбкодинга. Тема: {topic}. Сделай 4–5 слайдов с текстом для каждого. Слайд 1 — крючок, последний — призыв к действию. Каждый слайд 1–2 предложения.",
        "label": "сценарий сторис"
    },
    "💡 Заголовки": {
        "ask": (
            "💡 *Заголовки*\n\n"
            "Напиши тему — я придумаю 7 цепляющих заголовков для постов, статей или писем.\n\n"
            "Примеры тем:\n"
            "• «вайбкодинг для новичков»\n"
            "• «автоматизация без программиста»\n"
            "• «как ИИ пишет код вместо тебя»\n\n"
            "✏️ Напиши тему:"
        ),
        "prompt": "Придумай 7 цепляющих заголовков для контента про вайбкодинг. Тема: {topic}. Используй разные форматы: вопрос, число, провокация, обещание результата. Каждый заголовок с новой строки, пронумеруй.",
        "label": "заголовки"
    },
    "📊 Моя история": {
        "ask": (
            "📊 *Моя история*\n\n"
            "Расскажи коротко свой путь или идею — я оформлю в вдохновляющую историю для соцсетей.\n\n"
            "Примеры:\n"
            "• «боялась технологий, теперь автоматизирую всё подряд»\n"
            "• «потратила 3 года на найм программиста, а потом нашла вайбкодинг»\n"
            "• «первый проект за 2 часа без единой строчки кода»\n\n"
            "✏️ Расскажи свою историю или идею:"
        ),
        "prompt": "Напиши вдохновляющую личную историю про вайбкодинг для социальных сетей. Основа истории: {topic}. Структура: точка А (было плохо/страшно/непонятно) → поворот → результат → вывод для читателя. Длина 150–250 слов. Тон искренний и личный.",
        "label": "история"
    },
}

HELP_TEXT = (
    "❓ *Как пользоваться ботом*\n\n"
    "1️⃣ Выбери формат кнопкой внизу\n"
    "2️⃣ Напиши или надиктуй тему\n"
    "3️⃣ Получи готовый текст\n"
    "4️⃣ Скопируй и публикуй!\n\n"
    "━━━━━━━━━━━━━━━━\n"
    "📝 *Написать пост* — пост для Telegram/Instagram\n"
    "🎙 *Голосовой ввод* — надиктуй тему голосом\n"
    "📖 *Описание курса* — продающий текст про курс\n"
    "🎬 *Сторис-сценарий* — сценарий по слайдам\n"
    "💡 *Заголовки* — 7 цепляющих заголовков\n"
    "📊 *Моя история* — личная история для соцсетей\n\n"
    "━━━━━━━━━━━━━━━━\n"
    "🎨 *Свой стиль письма:*\n"
    "Команда /settov — загрузи свои примеры постов, "
    "и бот начнёт писать в твоём стиле\n\n"
    "После каждого текста появляются кнопки:\n"
    "✏️ Доработать — улучшить по твоим пожеланиям\n"
    "🔄 Новый текст — другой вариант на ту же тему\n"
    "📋 Скопировать — получить чистый текст\n"
    "🔙 Начать заново — вернуться в начало"
)


def result_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Доработать", callback_data="refine"),
            InlineKeyboardButton("🔄 Новый текст", callback_data="regenerate"),
        ],
        [
            InlineKeyboardButton("📋 Скопировать текст", callback_data="copy"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"),
        ],
        [
            InlineKeyboardButton("🔙 Начать заново", callback_data="restart"),
        ]
    ])


# --- Онбординг ---

async def send_onboarding(update: Update):
    chat = update.effective_chat
    name = update.effective_user.first_name or "друг"

    await chat.send_message(
        f"👋 Привет, {name}!\n\nЯ ИИ-помощник — жду твой запрос 🤖\n\n"
        "Я помогу создавать контент про *вайбкодинг*.\n\n"
        "Вайбкодинг — это когда ты описываешь задачу словами, а ИИ пишет код. "
        "Никакого программирования — только идеи и результат 🚀\n\n"
        "За несколько секунд я создам для тебя:\n"
        "📝 Посты для Telegram и Instagram\n"
        "📖 Описания курсов\n"
        "🎬 Сценарии для сторис\n"
        "💡 Цепляющие заголовки\n"
        "📊 Личные истории\n"
        "🎙 Всё это — даже голосом!",
        parse_mode="Markdown"
    )

    await chat.send_message(
        "🎨 *Хочешь чтобы бот писал в твоём стиле?*\n\n"
        "Используй команду /settov — отправь 2–3 примера своих постов, "
        "и я запомню твой голос и манеру письма.\n\n"
        "Тогда все тексты будут звучать именно как ты — "
        "не как робот, а как живой автор 🙌\n\n"
        "Напиши /settov чтобы настроить прямо сейчас, "
        "или пропусти и начни пользоваться сразу.",
        parse_mode="Markdown"
    )

    await chat.send_message(
        "⚡️ *Быстрый старт — 3 шага:*\n\n"
        "1️⃣ Нажми кнопку внизу — например *«📝 Написать пост»*\n"
        "2️⃣ Напиши тему — например: «как начать вайбкодить с нуля»\n"
        "3️⃣ Получи готовый текст и скопируй в свой канал!\n\n"
        "Если что-то непонятно — кнопка *«❓ Помощь»* всегда внизу 👇",
        parse_mode="Markdown",
        reply_markup=MAIN_MENU
    )


# --- Команды ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    user_id = update.effective_user.id

    if is_new_user(user_id):
        save_user(user_id)
        await send_onboarding(update)
    else:
        name = update.effective_user.first_name or "друг"
        await update.message.reply_text(
            f"👋 Привет, {name}! Я ИИ-помощник — жду твой запрос 🤖\n\nВыбери формат и напиши тему — создадим контент ✍️",
            reply_markup=MAIN_MENU
        )


async def settov_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["waiting_tov"] = True
    await update.message.reply_text(
        "🎨 *Настройка твоего стиля (Tone of Voice)*\n\n"
        "Отправь 2–3 примера своих постов или текстов — одним или несколькими сообщениями.\n\n"
        "Я запомню как ты пишешь: твои любимые слова, длину предложений, эмодзи, структуру.\n\n"
        "После этого все тексты бот будет писать в твоём стиле 🙌\n\n"
        "✏️ Отправляй примеры прямо сейчас:",
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown", reply_markup=MAIN_MENU)


# --- Основная логика ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "❓ Помощь":
        await update.message.reply_text(HELP_TEXT, parse_mode="Markdown", reply_markup=MAIN_MENU)
        return

    if text in CONTENT_TYPES:
        context.user_data["content_type"] = text
        context.user_data["last_topic"] = None
        await update.message.reply_text(
            CONTENT_TYPES[text]["ask"],
            parse_mode="Markdown",
            reply_markup=MAIN_MENU
        )
        return

    content_type = context.user_data.get("content_type", "📝 Написать пост")
    context.user_data["last_topic"] = text
    await update.message.reply_text("Генерирую... ⏳")
    await generate_content(update, context, topic=text, content_type=content_type)


async def generate_content(update: Update, context: ContextTypes.DEFAULT_TYPE, topic: str, content_type: str, refine_request: str = None):
    cfg = CONTENT_TYPES.get(content_type, CONTENT_TYPES["📝 Написать пост"])
    prompt = cfg["prompt"].format(topic=topic)

    if refine_request:
        prompt = f"{prompt}\n\nПользователь просит доработать: {refine_request}"

    tov = context.user_data.get("tov", "")
    system = (
        "Ты — профессиональный копирайтер по теме вайбкодинга. "
        "Вайбкодинг — создание программ через диалог с ИИ, без знания синтаксиса. "
        "Пиши живо, вдохновляюще, по-русски. Без воды и клише. "
        "Автор — женщина, всегда пиши от женского лица: «я создала», «я поняла», «я решила»."
        + (f"\n\nСтиль автора (пиши похоже на эти примеры):\n{tov}" if tov else "")
    )

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            temperature=0.85,
            max_tokens=700
        )
        result = response.choices[0].message.content
        context.user_data["last_result"] = result

        target = update.message or update.callback_query.message
        await target.reply_text(result, reply_markup=result_keyboard())

    except Exception:
        target = update.message or update.callback_query.message
        await target.reply_text(
            "Не получилось создать текст — попробуй ещё раз или выбери другую тему.",
            reply_markup=MAIN_MENU
        )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action = query.data
    topic = context.user_data.get("last_topic", "вайбкодинг")
    content_type = context.user_data.get("content_type", "📝 Написать пост")
    last_result = context.user_data.get("last_result", "")

    if action == "regenerate":
        await query.message.reply_text("Генерирую новый вариант... 🔄")
        await generate_content(update, context, topic=topic, content_type=content_type)

    elif action == "refine":
        context.user_data["waiting_refine"] = True
        await query.message.reply_text(
            "✏️ Напиши что улучшить — например:\n"
            "«сделай короче», «добавь юмор», «более официальный тон», «добавь CTA»"
        )

    elif action == "copy":
        if last_result:
            await query.message.reply_text("👇 Нажми и удержи на тексте ниже → выбери «Копировать»:")
            await query.message.reply_text(last_result)
        else:
            await query.message.reply_text("Текст не найден. Сгенерируй новый.")

    elif action == "main_menu":
        context.user_data.clear()
        await query.message.reply_text("🏠 Главное меню — выбери формат:", reply_markup=MAIN_MENU)

    elif action == "restart":
        context.user_data.clear()
        await query.message.reply_text(
            "🔙 Начинаем заново!\n\nВыбери формат кнопкой внизу ✍️",
            reply_markup=MAIN_MENU
        )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎙 Слышу тебя, расшифровываю...")
    try:
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        audio_bytes = await file.download_as_bytearray()

        transcription = groq_client.audio.transcriptions.create(
            file=("voice.ogg", bytes(audio_bytes)),
            model="whisper-large-v3",
            language="ru"
        )
        topic = transcription.text.strip()

        if not topic:
            await update.message.reply_text("Не смогла разобрать — попробуй ещё раз или напиши текстом.")
            return

        await update.message.reply_text(f"🎙 Услышала: *{topic}*\n\nГенерирую...", parse_mode="Markdown")
        content_type = context.user_data.get("content_type", "📝 Написать пост")
        context.user_data["last_topic"] = topic
        await generate_content(update, context, topic=topic, content_type=content_type)

    except Exception:
        await update.message.reply_text("Не смогла обработать голосовое. Попробуй ещё раз или напиши текстом.")


async def handle_refine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Собираем примеры стиля через /settov
    if context.user_data.get("waiting_tov"):
        tov = context.user_data.get("tov", "")
        tov += "\n\n" + update.message.text
        context.user_data["tov"] = tov.strip()
        await update.message.reply_text(
            "✅ Пример добавлен! Можешь прислать ещё или начать создавать контент — "
            "теперь буду писать в твоём стиле 🎨",
            reply_markup=MAIN_MENU
        )
        context.user_data["waiting_tov"] = False
        return

    if context.user_data.get("waiting_refine"):
        context.user_data["waiting_refine"] = False
        refine_request = update.message.text
        topic = context.user_data.get("last_topic", "вайбкодинг")
        content_type = context.user_data.get("content_type", "📝 Написать пост")
        await update.message.reply_text("Дорабатываю... ✏️")
        await generate_content(update, context, topic=topic, content_type=content_type, refine_request=refine_request)
        return

    await handle_message(update, context)


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("settov", settov_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_refine))
    print("Бот запущен. Нажми Ctrl+C чтобы остановить.")
    app.run_polling()


if __name__ == "__main__":
    main()
