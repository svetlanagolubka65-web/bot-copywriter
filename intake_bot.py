import asyncio
import os
from dotenv import load_dotenv
from groq import Groq
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

load_dotenv()

INTAKE_BOT_TOKEN = os.getenv("INTAKE_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

groq_client = Groq(api_key=GROQ_API_KEY)


# --- Услуги (в синхроне с .comp-item в index.html) ---

SERVICES = {
    "texts": {
        "emoji": "✍️",
        "title": "Генерация и редактирование текстов",
        "desc": "Посты, статьи, офферы — помогаю создавать контент быстро и точно под вашу задачу.",
        "includes": [
            "3–5 постов или статей под вашу аудиторию и цель",
            "2 круга правок — дорабатываем, пока не устроит",
            "Срок: от 3 дней",
        ],
        "price": "от 4 500 ₽ за пакет",
    },
    "prompts": {
        "emoji": "🔮",
        "title": "Создание промптов под конкретные задачи",
        "desc": "Разрабатываю промпты, чтобы ИИ давал нужный результат с первого раза.",
        "includes": [
            "Разбираем вашу задачу и собираем рабочие промпты под неё",
            "Личная библиотека промптов, которой пользуетесь дальше сами",
            "Срок: 1 встреча, 60 минут",
        ],
        "price": "от 2 500 ₽ / 60 минут",
    },
    "consult": {
        "emoji": "🎧",
        "title": "Консультации по ChatGPT и AI-сервисам",
        "desc": "Объясняю как использовать инструменты под ваши конкретные цели и задачи.",
        "includes": [
            "Разбор вашей задачи и подбор подходящих инструментов",
            "Готовые рекомендации, а не общая теория",
            "Срок: 60 минут, первые 20 — бесплатно",
        ],
        "price": "от 2 500 ₽ / 60 минут",
    },
    "automation": {
        "emoji": "⚙️",
        "title": "Ускорение работы и автоматизация рутины",
        "desc": "Нахожу где ИИ сэкономит вам часы каждую неделю — внедряю и показываю.",
        "includes": [
            "2–3 занятия: находим, что в вашей работе можно отдать ИИ",
            "Настройка инструментов под ваши задачи",
            "Через неделю работаете с ИИ самостоятельно",
        ],
        "price": "от 7 900 ₽ за пакет «Быстрый старт»",
    },
    "training": {
        "emoji": "🎓",
        "title": "Помощь в обучении и подготовке презентаций",
        "desc": "Создаём обучающие материалы и профессиональные презентации с помощью ИИ.",
        "includes": [
            "Готовим структуру и текст презентации вместе с ИИ",
            "Показываю инструменты для дизайна слайдов",
            "Срок: 60 минут на разбор задачи",
        ],
        "price": "от 2 500 ₽ / 60 минут",
    },
    "visual": {
        "emoji": "🎨",
        "title": "AI-визуал: открытки, картинки, фильмы",
        "desc": "Создаю поздравительные открытки, короткие ролики и визуальный контент с помощью нейросетей.",
        "includes": [
            "Индивидуальный сюжет и несколько вариантов на выбор",
            "Доработка деталей до нужного результата",
            "Срок: 1–3 дня",
        ],
        "price": "от 1 500 ₽",
    },
    "song": {
        "emoji": "🎵",
        "title": "Персональные песни на заказ",
        "desc": "Создаю уникальную песню под конкретного человека или событие с помощью AI.",
        "includes": [
            "Уникальный текст и мелодия под человека или событие",
            "Несколько вариантов на выбор",
            "Срок: 2–3 дня",
        ],
        "price": "от 3 500 ₽",
    },
}

GENERAL_FAQ = [
    (
        "Как проходит бесплатная консультация?",
        "Пишете мне в Telegram, коротко описываете задачу. Я отвечаю в течение дня, и мы созваниваемся "
        "или общаемся в переписке — как вам удобнее. За 15–20 минут разбираем задачу, и я честно говорю, "
        "чем могу помочь и сколько это будет стоить. Никаких навязываний — если ИИ вам не нужен, так и скажу.",
    ),
    (
        "Я совсем не разбираюсь в технологиях. Точно получится?",
        "Да. Большинство моих клиентов до первой встречи ни разу не открывали ChatGPT. Объясняю простым "
        "языком, без теории — сразу на ваших рабочих примерах. Если что-то не поняли, разбираем ещё раз, "
        "это входит в стоимость.",
    ),
    (
        "Чем ваша песня или открытка лучше бесплатных нейросетей?",
        "Нейросеть выдаёт первый попавшийся вариант. Я пишу персональный сюжет под конкретного человека, "
        "генерирую несколько версий, отбираю лучшую и дорабатываю детали. Вы получаете готовый подарок без "
        "своего времени и без «кривых рук» на картинке.",
    ),
    (
        "Как оплатить и есть ли гарантии?",
        "Оплата картой или переводом. Для пакетов — 50% предоплата, остаток после сдачи работы. В текстовые "
        "и визуальные пакеты включены правки: работаем, пока результат не устроит.",
    ),
    (
        "Сколько времени занимает работа?",
        "Консультация — в течение 1–2 дней после обращения. Открытка — 1–2 дня, песня — 2–3 дня, текстовый "
        "пакет — от 3 дней в зависимости от объёма. Срочные заказы обсуждаются отдельно.",
    ),
    (
        "Вы работаете с компаниями?",
        "Да — настраиваю рабочие процессы с ИИ для небольших команд: контент-планы, шаблоны документов, "
        "обучение сотрудников. Напишите, обсудим формат.",
    ),
]

BRIEF_QUESTIONS = [
    {"key": "task", "text": "Опишите вашу задачу своими словами — что нужно сделать?"},
    {"key": "deadline", "text": "Какие у вас сроки?"},
    {"key": "budget", "text": "Ориентировочный бюджет? Если не знаете — так и напишите."},
]

NO_ANSWER_MARKERS = ("уточню у светланы", "не уверен", "не знаю точного ответа")


def _build_knowledge_base() -> str:
    lines = ["Услуги и цены (используй только эти цифры, ничего не выдумывай):", ""]
    for svc in SERVICES.values():
        lines.append(f"— {svc['title']}: {svc['desc']} {svc['price']}. " + " ".join(svc["includes"]))
    lines.append("")
    lines.append("Общие вопросы и ответы:")
    for q, a in GENERAL_FAQ:
        lines.append(f"— {q} {a}")
    return "\n".join(lines)


KNOWLEDGE_BASE = _build_knowledge_base()

QA_SYSTEM_PROMPT = (
    "Ты — помощник Светланы Голубевой, эксперта по ИИ. Отвечай на вопросы клиентов только на основе "
    "фактов ниже, коротко и по-русски. Если вопрос выходит за пределы этих фактов или ты не уверен в ответе — "
    "прямо напиши: «Точно не отвечу — уточню у Светланы», не придумывай цифры и детали.\n\n" + KNOWLEDGE_BASE
)


# --- Клавиатуры ---

def services_keyboard():
    keyboard = [
        [InlineKeyboardButton(f"{svc['emoji']} {svc['title']}", callback_data=f"svc_{slug}")]
        for slug, svc in SERVICES.items()
    ]
    return InlineKeyboardMarkup(keyboard)


def service_card_keyboard(slug: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❓ Задать вопрос", callback_data=f"ask_{slug}")],
        [InlineKeyboardButton("✍️ Оставить заявку", callback_data=f"brief_{slug}")],
    ])


def after_answer_keyboard(slug: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❓ Ещё вопрос", callback_data=f"ask_{slug}")],
        [InlineKeyboardButton("✍️ Оставить заявку", callback_data=f"brief_{slug}")],
        [InlineKeyboardButton("🏠 Начало", callback_data="main_menu")],
    ])


def main_menu_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Начало", callback_data="main_menu")]])


def _service_card_text(slug: str) -> str:
    svc = SERVICES[slug]
    includes = "\n".join(f"• {item}" for item in svc["includes"])
    return (
        f"{svc['emoji']} *{svc['title']}*\n\n"
        f"{svc['desc']}\n\n"
        f"{includes}\n\n"
        f"💰 {svc['price']}"
    )


async def _show_service_card(chat, slug: str):
    await chat.send_message(
        _service_card_text(slug), parse_mode="Markdown", reply_markup=service_card_keyboard(slug)
    )


async def _show_services_list(chat):
    await chat.send_message(
        "Какая услуга вас интересует?", reply_markup=services_keyboard()
    )


async def _notify_admins(context: ContextTypes.DEFAULT_TYPE, text: str):
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, text, parse_mode="Markdown")
        except Exception:
            pass


# --- Команды ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    slug = context.args[0] if context.args else None
    chat = update.effective_chat

    greeting = (
        "Привет! Я Консультант Светланы — Светик 🤖\n"
        "Отвечу на ваши вопросы об услугах. Пишите в свободной форме."
    )

    if slug in SERVICES:
        context.user_data["slug"] = slug
        await chat.send_message(greeting)
        await _show_service_card(chat, slug)
    else:
        await chat.send_message(greeting)
        await _show_services_list(chat)


# --- Режим свободных вопросов (Q&A) ---

async def _answer_question(chat, context: ContextTypes.DEFAULT_TYPE, question: str):
    slug = context.user_data.get("slug")
    user = context.user_data.get("user_label", "клиент")

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": QA_SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            temperature=0.3,
            max_tokens=400,
        )
        answer = response.choices[0].message.content
    except Exception:
        answer = None

    if answer is None or any(marker in answer.lower() for marker in NO_ANSWER_MARKERS):
        await _notify_admins(
            context,
            f"❓ Бот не смог ответить {user}.\nУслуга: {SERVICES.get(slug, {}).get('title', '—')}\n"
            f"Вопрос: {question}",
        )
        if answer is None:
            answer = "Не получилось ответить — передала вопрос Светлане, она ответит вам сама."

    await chat.send_message(answer, reply_markup=after_answer_keyboard(slug))


# --- Режим сбора брифа ---

async def _ask_next_brief_question(chat, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("question_step", 0)

    if step >= len(BRIEF_QUESTIONS):
        await _finish_brief(chat, context)
        return

    await chat.send_message(BRIEF_QUESTIONS[step]["text"])


async def _finish_brief(chat, context: ContextTypes.DEFAULT_TYPE):
    slug = context.user_data.get("slug")
    answers = context.user_data.get("answers", {})
    user = context.user_data.get("user_label", "клиент")
    svc = SERVICES.get(slug, {})

    brief_lines = [f"✍️ Новая заявка от {user}", f"Услуга: {svc.get('title', '—')}"]
    for q in BRIEF_QUESTIONS:
        brief_lines.append(f"{q['text']} {answers.get(q['key'], '—')}")

    await _notify_admins(context, "\n".join(brief_lines))

    await chat.send_message(
        "Спасибо! Передала заявку Светлане, она свяжется с вами в Telegram в ближайшее время 🙌",
        reply_markup=main_menu_keyboard(),
    )
    context.user_data["mode"] = None


# --- Основная логика сообщений ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user
    username = getattr(user, "username", None)
    context.user_data["user_label"] = f"@{username}" if username else (user.first_name or "клиент")

    mode = context.user_data.get("mode")

    if mode == "qa":
        await _answer_question(update.message.chat, context, text)
        return

    if mode == "brief":
        step = context.user_data.get("question_step", 0)
        key = BRIEF_QUESTIONS[step]["key"]
        context.user_data.setdefault("answers", {})[key] = text
        context.user_data["question_step"] = step + 1
        await _ask_next_brief_question(update.message.chat, context)
        return

    await _show_services_list(update.message.chat)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    user = update.effective_user
    username = getattr(user, "username", None)
    context.user_data["user_label"] = f"@{username}" if username else (user.first_name or "клиент")

    chat = query.message.chat

    if action.startswith("svc_"):
        slug = action[4:]
        if slug not in SERVICES:
            await _show_services_list(chat)
            return
        context.user_data["mode"] = None
        context.user_data["slug"] = slug
        await _show_service_card(chat, slug)
        return

    if action.startswith("ask_"):
        slug = action[4:]
        if slug not in SERVICES:
            await _show_services_list(chat)
            return
        context.user_data["mode"] = "qa"
        context.user_data["slug"] = slug
        await chat.send_message("Напишите ваш вопрос — отвечу сразу:")
        return

    if action.startswith("brief_"):
        slug = action[6:]
        if slug not in SERVICES:
            await _show_services_list(chat)
            return
        context.user_data["mode"] = "brief"
        context.user_data["slug"] = slug
        context.user_data["question_step"] = 0
        context.user_data["answers"] = {}
        await _ask_next_brief_question(chat, context)
        return

    if action == "main_menu":
        context.user_data.clear()
        await _show_services_list(chat)
        return


def main():
    asyncio.set_event_loop(asyncio.new_event_loop())
    app = Application.builder().token(INTAKE_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот-консультант запущен. Нажми Ctrl+C чтобы остановить.")
    app.run_polling()


if __name__ == "__main__":
    main()
