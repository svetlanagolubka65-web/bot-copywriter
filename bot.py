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
USERS_DATA_FILE = "users_data.json"

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


# --- Профили (имя + пол) ---

def load_user_profile(user_id: int):
    if os.path.exists(USERS_DATA_FILE):
        with open(USERS_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(str(user_id))
    return None

def save_user_profile(user_id: int, name: str, gender: str):
    data = {}
    if os.path.exists(USERS_DATA_FILE):
        with open(USERS_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    data[str(user_id)] = {"name": name, "gender": gender}
    with open(USERS_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# --- Меню ---

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["📝 Написать пост", "📖 Описание курса"],
        ["🎬 Сторис-сценарий", "💡 Заголовки"],
        ["📊 Моя история", "❓ Помощь"],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выбери формат или напиши тему..."
)

def gender_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👩 Женщина", callback_data="gender_f"),
            InlineKeyboardButton("👨 Мужчина", callback_data="gender_m"),
        ]
    ])


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
    "📖 *Описание курса* — продающий текст про курс\n"
    "🎬 *Сторис-сценарий* — сценарий по слайдам\n"
    "💡 *Заголовки* — 7 цепляющих заголовков\n"
    "📊 *Моя история* — личная история для соцсетей\n\n"
    "━━━━━━━━━━━━━━━━\n"
    "🎨 *Свой стиль письма:*\n"
    "Команда /settov — загрузи 2–3 примера своих постов, "
    "и бот начнёт писать в твоём стиле\n\n"
    "После каждого текста появляются кнопки:\n"
    "✏️ Доработать — улучшить по твоим пожеланиям\n"
    "🔄 Новый текст — другой вариант на ту же тему\n"
    "🏠 Главное меню — вернуться в начало"
)


def result_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Доработать", callback_data="refine"),
            InlineKeyboardButton("🔄 Новый текст", callback_data="regenerate"),
        ],
        [
            InlineKeyboardButton("#️⃣ Добавить хэштеги", callback_data="hashtags"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"),
        ],
    ])


def _gender_note(gender: str) -> str:
    if gender == "m":
        return "Автор — мужчина, всегда пиши от мужского лица: «я создал», «я понял», «я решил»."
    return "Автор — женщина, всегда пиши от женского лица: «я создала», «я поняла», «я решила»."


# --- Онбординг ---

async def send_onboarding(chat, name: str):
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
    user_id = update.effective_user.id
    tg_name = update.effective_user.first_name or "друг"

    tov = context.user_data.get("tov")
    context.user_data.clear()
    context.user_data["name"] = tg_name
    if tov:
        context.user_data["tov"] = tov

    if is_new_user(user_id):
        save_user(user_id)
        await update.effective_chat.send_message(
            f"Привет, {tg_name}! Я ИИ-помощник Светланы! Буду рад помочь! 🤖\n\n"
            "Прежде чем начнём — как к тебе обращаться в текстах?",
            reply_markup=gender_keyboard()
        )
    else:
        await update.message.reply_text(
            f"👋 Привет, {tg_name}! Снова рад тебя видеть 🤖\n\nВыбери формат и создадим контент ✍️",
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
    content_type = context.user_data.get("content_type")
    step = context.user_data.get("question_step", 0)
    questions = CONTENT_TYPES[content_type]["questions"]

    key = questions[step]["key"]
    context.user_data.setdefault("answers", {})[key] = answer
    context.user_data["question_step"] = step + 1

    await ask_next_question(message, context)


# --- Генерация ---

async def generate_from_answers(message, context: ContextTypes.DEFAULT_TYPE):
    content_type = context.user_data.get("content_type", "📝 Написать пост")
    answers = context.user_data.get("answers", {})
    cfg = CONTENT_TYPES.get(content_type, CONTENT_TYPES["📝 Написать пост"])

    try:
        prompt = cfg["prompt"].format(**answers)
    except KeyError:
        prompt = cfg["prompt"].format(topic=answers.get("topic", "произвольная тема"), **answers)

    tov = context.user_data.get("tov", "")
    gender = context.user_data.get("gender", "f")
    system = (
        "Ты — профессиональный копирайтер. "
        "Пиши живо, вдохновляюще, по-русски. Без воды и клише. "
        + _gender_note(gender)
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
        context.user_data["waiting_tov"] = False
        name = context.user_data.get("name", "")
        greeting = f"{name}, т" if name else "Т"
        await update.message.reply_text(
            f"✅ Пример добавлен! {greeting}еперь буду писать в твоём стиле 🎨\n\n"
            "Можешь прислать ещё или начать создавать контент.",
            reply_markup=MAIN_MENU
        )
        return

    # 3. Доработка текста
    if context.user_data.get("waiting_refine"):
        context.user_data["waiting_refine"] = False
        answers = context.user_data.get("answers", {})
        content_type = context.user_data.get("content_type", "📝 Написать пост")
        cfg = CONTENT_TYPES.get(content_type, CONTENT_TYPES["📝 Написать пост"])

        try:
            base_prompt = cfg["prompt"].format(**answers)
        except KeyError:
            base_prompt = cfg["prompt"].format(topic=answers.get("topic", "тема"), **answers)

        prompt = f"{base_prompt}\n\nПользователь просит доработать: {text}"
        tov = context.user_data.get("tov", "")
        gender = context.user_data.get("gender", "f")
        system = (
            "Ты — профессиональный копирайтер. Пиши живо, по-русски. Без воды. "
            + _gender_note(gender)
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

    # 4. Выбор типа контента
    if text in CONTENT_TYPES:
        context.user_data["content_type"] = text
        context.user_data["question_step"] = 0
        context.user_data["answers"] = {}
        await ask_next_question(update.message, context)
        return

    # 5. Ответ на вопрос в потоке (текстом — в том числе вместо кнопки)
    content_type = context.user_data.get("content_type")
    if content_type:
        step = context.user_data.get("question_step", 0)
        questions = CONTENT_TYPES.get(content_type, {}).get("questions", [])
        if step < len(questions):
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

    # Выбор пола при знакомстве
    if action.startswith("gender_"):
        gender = action.split("_")[1]  # "f" или "m"
        name = context.user_data.get("name", "")
        user_id = update.effective_user.id
        save_user_profile(user_id, name, gender)
        context.user_data["gender"] = gender
        await send_onboarding(query.message.chat, name)
        return

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

    elif action == "hashtags":
        if not last_result:
            await query.message.reply_text("Текст не найден. Сгенерируй новый.")
            return
        await query.message.reply_text("Подбираю хэштеги... #️⃣")
        try:
            system = "Ты — SMM-специалист. Подбери 7–10 релевантных хэштегов на русском и английском языке для поста в Telegram/Instagram. Только хэштеги, без пояснений, каждый с новой строки."
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"Пост:\n{last_result}"}
                ],
                temperature=0.7,
                max_tokens=200
            )
            hashtags = response.choices[0].message.content
            await query.message.reply_text(hashtags, reply_markup=result_keyboard())
        except Exception:
            await query.message.reply_text("Не получилось подобрать хэштеги.", reply_markup=MAIN_MENU)

    elif action == "main_menu":
        name = context.user_data.get("name")
        gender = context.user_data.get("gender")
        tov = context.user_data.get("tov")
        context.user_data.clear()
        if name:
            context.user_data["name"] = name
        if gender:
            context.user_data["gender"] = gender
        if tov:
            context.user_data["tov"] = tov
        greeting = f"{name}, в" if name else "В"
        await query.message.reply_text(
            f"🏠 {greeting}ыбери формат:",
            reply_markup=MAIN_MENU
        )



def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("settov", settov_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен. Нажми Ctrl+C чтобы остановить.")
    app.run_polling()


if __name__ == "__main__":
    main()
