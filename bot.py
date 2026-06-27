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


# --- Хранилище пользователей ---

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


# --- Типы контента с уточняющими вопросами ---

CONTENT_TYPES = {
    "📝 Написать пост": {
        "questions": [
            {
                "key": "topic",
                "text": (
                    "📝 *Написать пост*\n\n"
                    "О чём будет пост? Напиши тему:\n\n"
                    "_Например: «как я бросила найм и открыла своё дело»_"
                )
            },
            {
                "key": "audience",
                "text": "Для кого этот пост?\n\n_Например: предприниматели, мамы в декрете, студенты_"
            },
            {
                "key": "tone",
                "text": "Выбери тон поста:",
                "buttons": ["🔥 Вдохновляющий", "😊 Дружелюбный", "💼 Серьёзный", "😏 Провокационный"]
            },
        ],
        "prompt": (
            "Напиши вовлекающий пост для Telegram/Instagram. "
            "Тема: {topic}. Аудитория: {audience}. Тон: {tone}. "
            "Длина 150–250 слов, живой язык, начни с цепляющего заголовка, "
            "закончи вопросом к аудитории. Добавь 2–3 эмодзи."
        ),
        "label": "пост"
    },
    "🎙 Голосовой ввод": {
        "questions": [
            {
                "key": "audience",
                "text": "Голос принят! Для кого этот пост?\n\n_Например: предприниматели, мамы, фрилансеры_"
            },
            {
                "key": "tone",
                "text": "Выбери тон:",
                "buttons": ["🔥 Вдохновляющий", "😊 Дружелюбный", "💼 Серьёзный", "😏 Провокационный"]
            },
        ],
        "prompt": (
            "Напиши вовлекающий пост для Telegram/Instagram. "
            "Тема: {topic}. Аудитория: {audience}. Тон: {tone}. "
            "Длина 150–250 слов, живой язык, начни с цепляющего заголовка, "
            "закончи вопросом к аудитории. Добавь 2–3 эмодзи."
        ),
        "label": "пост из голоса"
    },
    "📖 Описание курса": {
        "questions": [
            {
                "key": "topic",
                "text": "📖 *Описание курса*\n\nНазвание или тема курса:"
            },
            {
                "key": "audience",
                "text": "Для кого этот курс?\n\n_Например: начинающие предприниматели, дизайнеры, мамы_"
            },
            {
                "key": "result",
                "text": "Главный результат — что получит студент после курса?\n\n_Например: первый клиент, готовое портфолио_"
            },
        ],
        "prompt": (
            "Напиши продающее описание онлайн-курса. "
            "Курс: {topic}. Для кого: {audience}. Главный результат: {result}. "
            "Включи: для кого курс, что получит студент, 3–4 ключевых блока, призыв записаться. "
            "Длина 150–250 слов. Тон вдохновляющий."
        ),
        "label": "описание курса"
    },
    "🎬 Сторис-сценарий": {
        "questions": [
            {
                "key": "topic",
                "text": "🎬 *Сторис-сценарий*\n\nТема сторис:"
            },
            {
                "key": "goal",
                "text": "Что должен сделать зритель после сторис?\n\n_Например: написать в директ, перейти по ссылке, сохранить пост_"
            },
        ],
        "prompt": (
            "Напиши сценарий для Instagram/Telegram Stories. "
            "Тема: {topic}. Целевое действие зрителя: {goal}. "
            "Сделай 4–5 слайдов с текстом для каждого. "
            "Слайд 1 — крючок, последний — призыв к действию. Каждый слайд 1–2 предложения."
        ),
        "label": "сценарий сторис"
    },
    "💡 Заголовки": {
        "questions": [
            {
                "key": "topic",
                "text": "💡 *Заголовки*\n\nТема для заголовков:"
            },
            {
                "key": "style",
                "text": "Стиль заголовков:",
                "buttons": ["🎯 Конкретные", "❓ Вопросом", "🔢 С числами", "😱 Интригующие"]
            },
        ],
        "prompt": (
            "Придумай 7 цепляющих заголовков. "
            "Тема: {topic}. Стиль: {style}. "
            "Разные форматы. Каждый заголовок с новой строки, пронумеруй."
        ),
        "label": "заголовки"
    },
    "📊 Моя история": {
        "questions": [
            {
                "key": "topic",
                "text": "📊 *Моя история*\n\nКратко расскажи свою историю или идею:"
            },
            {
                "key": "message",
                "text": "Что хочешь донести до читателя? Главная мысль?\n\n_Например: «любой может начать», «ошибки — это нормально»_"
            },
        ],
        "prompt": (
            "Напиши вдохновляющую личную историю для социальных сетей. "
            "Основа: {topic}. Главная мысль: {message}. "
            "Структура: точка А (было плохо/непонятно) → поворот → результат → вывод для читателя. "
            "Длина 150–250 слов. Тон искренний и личный."
        ),
        "label": "история"
    },
}

HELP_TEXT = (
    "❓ *Как пользоваться ботом*\n\n"
    "1️⃣ Выбери формат кнопкой внизу\n"
    "2️⃣ Ответь на 2–3 вопроса о теме и аудитории\n"
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
        f"👋 Привет, {name}!\n\nЯ ИИ-помощник — создаю контент для *любой темы* 🤖\n\n"
        "Напишу посты, описания курсов, сценарии сторис и заголовки — "
        "для любой ниши и аудитории.\n\n"
        "Задам 2–3 уточняющих вопроса и создам текст именно под тебя 🚀",
        parse_mode="Markdown"
    )

    await chat.send_message(
        "🎨 *Хочешь чтобы бот писал в твоём стиле?*\n\n"
        "Используй команду /settov — отправь 2–3 примера своих постов, "
        "и я запомню твой голос и манеру письма.\n\n"
        "Напиши /settov чтобы настроить прямо сейчас, "
        "или пропусти и начни пользоваться сразу.",
        parse_mode="Markdown"
    )

    await chat.send_message(
        "⚡️ *Быстрый старт — 3 шага:*\n\n"
        "1️⃣ Нажми кнопку внизу — например *«📝 Написать пост»*\n"
        "2️⃣ Ответь на 2–3 вопроса о теме и аудитории\n"
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
            f"👋 Привет, {name}! Я ИИ-помощник — жду твой запрос 🤖\n\nВыбери формат и отвечай на вопросы — создадим контент ✍️",
            reply_markup=MAIN_MENU
        )


async def settov_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["waiting_tov"] = True
    await update.message.reply_text(
        "🎨 *Настройка твоего стиля (Tone of Voice)*\n\n"
        "Отправь 2–3 примера своих постов или текстов — одним или несколькими сообщениями.\n\n"
        "Я запомню как ты пишешь: твои любимые слова, длину предложений, эмодзи, структуру.\n\n"
        "После этого все тексты буду писать в твоём стиле 🙌\n\n"
        "✏️ Отправляй примеры прямо сейчас:",
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown", reply_markup=MAIN_MENU)


# --- Логика вопросов ---

async def ask_next_question(message, context: ContextTypes.DEFAULT_TYPE):
    """Задаёт следующий вопрос или запускает генерацию."""
    content_type = context.user_data.get("content_type")
    step = context.user_data.get("question_step", 0)
    questions = CONTENT_TYPES[content_type]["questions"]

    if step >= len(questions):
        await message.reply_text("Генерирую... ⏳")
        await generate_from_answers(message, context)
        return

    question = questions[step]

    if "buttons" in question:
        keyboard = [[InlineKeyboardButton(btn, callback_data=f"qans_{btn}")] for btn in question["buttons"]]
        markup = InlineKeyboardMarkup(keyboard)
        await message.reply_text(question["text"], parse_mode="Markdown", reply_markup=markup)
    else:
        await message.reply_text(question["text"], parse_mode="Markdown", reply_markup=MAIN_MENU)


async def save_answer_and_continue(message, context: ContextTypes.DEFAULT_TYPE, answer: str):
    """Сохраняет ответ и переходит к следующему вопросу."""
    content_type = context.user_data.get("content_type")
    step = context.user_data.get("question_step", 0)
    questions = CONTENT_TYPES[content_type]["questions"]

    key = questions[step]["key"]
    context.user_data.setdefault("answers", {})[key] = answer
    context.user_data["question_step"] = step + 1

    await ask_next_question(message, context)


# --- Генерация ---

async def generate_from_answers(message, context: ContextTypes.DEFAULT_TYPE):
    """Генерирует контент на основе собранных ответов."""
    content_type = context.user_data.get("content_type", "📝 Написать пост")
    answers = context.user_data.get("answers", {})
    cfg = CONTENT_TYPES.get(content_type, CONTENT_TYPES["📝 Написать пост"])

    try:
        prompt = cfg["prompt"].format(**answers)
    except KeyError:
        prompt = cfg["prompt"].format(topic=answers.get("topic", "произвольная тема"), **answers)

    tov = context.user_data.get("tov", "")
    system = (
        "Ты — профессиональный копирайтер. "
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
        context.user_data["last_topic"] = answers.get("topic", "")

        await message.reply_text(result, reply_markup=result_keyboard())

    except Exception:
        await message.reply_text(
            "Не получилось создать текст — попробуй ещё раз или выбери другую тему.",
            reply_markup=MAIN_MENU
        )


# --- Основная логика сообщений ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # 1. Помощь
    if text == "❓ Помощь":
        await update.message.reply_text(HELP_TEXT, parse_mode="Markdown", reply_markup=MAIN_MENU)
        return

    # 2. Сбор примеров стиля (ToV)
    if context.user_data.get("waiting_tov"):
        tov = context.user_data.get("tov", "")
        tov += "\n\n" + text
        context.user_data["tov"] = tov.strip()
        await update.message.reply_text(
            "✅ Пример добавлен! Можешь прислать ещё или начать создавать контент — "
            "теперь буду писать в твоём стиле 🎨",
            reply_markup=MAIN_MENU
        )
        context.user_data["waiting_tov"] = False
        return

    # 3. Доработка текста
    if context.user_data.get("waiting_refine"):
        context.user_data["waiting_refine"] = False
        refine_request = text
        answers = context.user_data.get("answers", {})
        content_type = context.user_data.get("content_type", "📝 Написать пост")
        cfg = CONTENT_TYPES.get(content_type, CONTENT_TYPES["📝 Написать пост"])

        try:
            base_prompt = cfg["prompt"].format(**answers)
        except KeyError:
            base_prompt = cfg["prompt"].format(topic=answers.get("topic", "тема"), **answers)

        prompt = f"{base_prompt}\n\nПользователь просит доработать: {refine_request}"
        tov = context.user_data.get("tov", "")
        system = (
            "Ты — профессиональный копирайтер. Пиши живо, по-русски. Без воды. "
            "Автор — женщина, пиши от женского лица."
            + (f"\n\nСтиль автора:\n{tov}" if tov else "")
        )
        await update.message.reply_text("Дорабатываю... ✏️")
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
            await update.message.reply_text(result, reply_markup=result_keyboard())
        except Exception:
            await update.message.reply_text("Не получилось. Попробуй ещё раз.", reply_markup=MAIN_MENU)
        return

    # 4. Выбор типа контента — начинаем новый поток вопросов
    if text in CONTENT_TYPES:
        context.user_data["content_type"] = text
        context.user_data["question_step"] = 0
        context.user_data["answers"] = {}
        await ask_next_question(update.message, context)
        return

    # 5. Ответ на текстовый вопрос в потоке
    content_type = context.user_data.get("content_type")
    if content_type:
        step = context.user_data.get("question_step", 0)
        questions = CONTENT_TYPES.get(content_type, {}).get("questions", [])
        if step < len(questions) and "buttons" not in questions[step]:
            await save_answer_and_continue(update.message, context, text)
            return

    # 6. По умолчанию — создаём пост на введённую тему
    context.user_data["content_type"] = "📝 Написать пост"
    context.user_data["answers"] = {"topic": text}
    context.user_data["question_step"] = 1
    await ask_next_question(update.message, context)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action = query.data

    # Ответ на вопрос с кнопками
    if action.startswith("qans_"):
        answer = action[5:]
        await save_answer_and_continue(query.message, context, answer)
        return

    last_result = context.user_data.get("last_result", "")

    if action == "regenerate":
        await query.message.reply_text("Генерирую новый вариант... 🔄")
        await generate_from_answers(query.message, context)

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

        await update.message.reply_text(f"🎙 Услышала: *{topic}*", parse_mode="Markdown")

        # Тема уже есть из голоса — задаём оставшиеся вопросы
        context.user_data["content_type"] = "🎙 Голосовой ввод"
        context.user_data["answers"] = {"topic": topic}
        context.user_data["question_step"] = 0
        context.user_data["last_topic"] = topic

        await ask_next_question(update.message, context)

    except Exception:
        await update.message.reply_text("Не смогла обработать голосовое. Попробуй ещё раз или напиши текстом.")


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("settov", settov_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен. Нажми Ctrl+C чтобы остановить.")
    app.run_polling()


if __name__ == "__main__":
    main()
