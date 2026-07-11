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
LEADS_CHAT_ID = os.getenv("LEADS_CHAT_ID")
NOTIFY_CHAT_IDS = [int(LEADS_CHAT_ID)] if LEADS_CHAT_ID else ADMIN_IDS

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

# --- AI-фотосессии (специальный флоу для услуги "visual") ---
# Готовые промпты для Gemini — тексты и источник дублируются в prompts/photo_styles.md,
# при правке держать оба места в синхроне.

PHOTO_STYLES = {
    "beach": {
        "title": "🏖 Пляж на закате",
        "prompt": (
            "Сгенерируй молодую женщину на песчаном пляже среди крупных прибрежных валунов — средний план, "
            "акцент на силуэте и фактуре одежды. Ракурс — фронтальный с лёгким поворотом в три четверти, "
            "камера на уровне талии, имитация съёмки со смартфона. Поза расслабленная: корпус чуть развёрнут, "
            "одна нога выставлена вперёд, руки аккуратно придерживают полу расстёгнутой рубашки. Одежда — "
            "свободная белая рубашка мужского кроя, удлинённая, с закатанными рукавами, надета как мини-платье. "
            "Макияж естественный, едва заметный, подчёркивающий свежесть образа. Прическа — распущенные "
            "волнистые волосы, свободно обрамляющие лицо. Маникюр лаконичный, нейтральный. Выражение лица — "
            "спокойное, с лёгкой полуулыбкой, взгляд направлен чуть в сторону от камеры. Освещение тёплое, "
            "закатное: золотистые лучи мягко ложатся на кожу и ткань, глубокие тени подчёркивают рельеф камней "
            "и текстуру песка. Стиль изображения — реалистичная fashion-фотография в эстетике прибрежного "
            "минимализма. Фон — живописный пляж с массивными тёмными валунами, на заднем плане — пологий склон "
            "холма, покрытый зеленью, и спокойная гладь моря. Атмосфера умиротворённая, наполненная ощущением "
            "свободы и естественной красоты.\n"
            "vertical 9:16, smartphone photo, realistic environment, ultra realistic skin texture. Сохрани "
            "черты лица и идентичность без изменений, не изменяй форму лица, нос, губы, глаза и структуру кожи"
        ),
    },
    "evening": {
        "title": "👗 Вечернее платье",
        "prompt": (
            "Сгенерируй молодую женщину в вечернем наряде на фоне ночного города — средний план, акцент на "
            "силуэте платья и мягком свете витрин. Ракурс — фронтальный с лёгким поворотом в три четверти, "
            "камера на уровне груди, имитация съёмки со смартфона. Поза уверенная: корпус слегка развёрнут, "
            "одна рука придерживает клатч, другая свободно опущена, вес перенесён на одну ногу. Одежда — "
            "приталенное вечернее платье до пола из струящейся ткани, глубокий цвет (изумрудный или бордовый), "
            "тонкие бретели. Макияж вечерний, выразительный: акцент на глазах, естественные губы. Прическа — "
            "собранные волосы с несколькими выпущенными прядями у лица. Маникюр — классический глянцевый, "
            "в тон образу. Выражение лица — уверенное, с лёгкой полуулыбкой, взгляд направлен в камеру. "
            "Освещение — тёплые огни города и витрин, мягкие блики на ткани платья, лёгкое боке на заднем "
            "плане. Стиль изображения — реалистичная fashion-фотография в эстетике вечернего city-style. Фон — "
            "ночная городская улица с подсвеченными витринами и размытыми огнями машин вдалеке. Атмосфера "
            "роскоши, лёгкости и вечернего праздника.\n"
            "vertical 9:16, smartphone photo, realistic environment, ultra realistic skin texture. Сохрани "
            "черты лица и идентичность без изменений, не изменяй форму лица, нос, губы, глаза и структуру кожи"
        ),
    },
    "business": {
        "title": "💼 Деловой образ",
        "prompt": (
            "Сгенерируй молодую женщину в деловом костюме в современном офисном интерьере — средний план, "
            "акцент на силуэте костюма и уверенной осанке. Ракурс — фронтальный с лёгким поворотом в три "
            "четверти, камера на уровне груди, имитация съёмки со смартфона. Поза собранная: корпус прямой, "
            "руки скрещены свободно перед собой или одна рука в кармане брюк, взгляд направлен уверенно "
            "вперёд. Одежда — приталенный брючный костюм классического кроя (бежевый, серый или чёрный), "
            "белая базовая блуза. Макияж естественный, деловой, без ярких акцентов. Прическа — гладкая "
            "укладка или собранные волосы. Маникюр лаконичный, нейтральный. Выражение лица — спокойное, "
            "уверенное, лёгкая доброжелательная улыбка. Освещение мягкое, дневное, из больших окон офиса — "
            "рассеянный естественный свет. Стиль изображения — реалистичная fashion-фотография в эстетике "
            "делового портрета. Фон — светлый опен-спейс офиса с панорамными окнами, на заднем плане размытые "
            "силуэты мебели и городского пейзажа за стеклом. Атмосфера профессиональная, собранная, атмосфера "
            "успеха.\n"
            "vertical 9:16, smartphone photo, realistic environment, ultra realistic skin texture. Сохрани "
            "черты лица и идентичность без изменений, не изменяй форму лица, нос, губы, глаза и структуру кожи"
        ),
    },
    "studio": {
        "title": "📸 Студийный портрет",
        "prompt": (
            "Сгенерируй портрет молодой женщины в студийных условиях — крупный план (по грудь), акцент на "
            "лице, взгляде и фактуре кожи. Ракурс — фронтальный с лёгким поворотом в три четверти, камера на "
            "уровне глаз, имитация профессиональной портретной съёмки. Поза естественная: плечи слегка "
            "развёрнуты от камеры, взгляд направлен прямо в объектив. Одежда — однотонный трикотажный топ "
            "или водолазка спокойного оттенка, не отвлекающая от лица. Макияж выразительный, но естественный: "
            "акцент на глазах и скулах. Прическа — аккуратно уложенные волосы, подчёркивающие черты лица. "
            "Маникюр лаконичный. Выражение лица — спокойное, сосредоточенное, с едва уловимой полуулыбкой. "
            "Освещение — классическая студийная схема (мягкий рисующий свет спереди-сбоку, лёгкий контровой "
            "свет для объёма волос), тени мягкие, растушёванные. Стиль изображения — реалистичный студийный "
            "портрет, глубокая резкость на лице. Фон — однотонный студийный фон (серый, бежевый или "
            "тёмно-графитовый) с лёгким градиентом. Атмосфера спокойная, уверенная, портретная.\n"
            "vertical 9:16, smartphone photo, realistic environment, ultra realistic skin texture. Сохрани "
            "черты лица и идентичность без изменений, не изменяй форму лица, нос, губы, глаза и структуру кожи"
        ),
    },
    "casual": {
        "title": "🌿 Повседневный образ, на природе",
        "prompt": (
            "Сгенерируй молодую женщину на прогулке в парке или лесу — средний план, акцент на естественности "
            "позы и мягком дневном свете. Ракурс — фронтальный с лёгким поворотом в три четверти, камера на "
            "уровне талии, имитация съёмки со смартфона. Поза непринуждённая: корпус в лёгком движении (шаг "
            "вперёд), одна рука убирает прядь волос или держит стаканчик кофе. Одежда — повседневный образ: "
            "удобные джинсы или брюки, оверсайз-свитер или худи спокойного оттенка, лёгкая куртка накинута на "
            "плечи. Макияж лёгкий, дневной, естественный. Прическа — распущенные волосы или небрежный хвост. "
            "Маникюр лаконичный. Выражение лица — живое, тёплая искренняя улыбка, взгляд чуть в сторону от "
            "камеры. Освещение мягкое, естественное дневное, лёгкие блики сквозь листву деревьев. Стиль "
            "изображения — реалистичная lifestyle-фотография в эстетике повседневности. Фон — зелёный парк "
            "или лес с тропинкой, вдалеке размытые силуэты деревьев и солнечные блики. Атмосфера лёгкая, "
            "свежая, наполненная спокойствием и естественностью.\n"
            "vertical 9:16, smartphone photo, realistic environment, ultra realistic skin texture. Сохрани "
            "черты лица и идентичность без изменений, не изменяй форму лица, нос, губы, глаза и структуру кожи"
        ),
    },
}

CUSTOM_PROMPT_TEMPLATE = (
    "Сгенерируй фотореалистичное фото человека по референсному фото — {description}. Ракурс — фронтальный "
    "с лёгким поворотом в три четверти, имитация съёмки со смартфона. Естественные макияж и причёска, поза "
    "непринуждённая, выражение лица живое. Освещение мягкое, естественное, подчёркивающее фактуру кожи и "
    "одежды.\n"
    "vertical 9:16, smartphone photo, realistic environment, ultra realistic skin texture. Сохрани черты "
    "лица и идентичность без изменений, не изменяй форму лица, нос, губы, глаза и структуру кожи."
)

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


def visual_type_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📸 Фото по вашему фото", callback_data="vtype_photo")],
        [InlineKeyboardButton("💌 Открытка", callback_data="vtype_card")],
        [InlineKeyboardButton("🎬 Ролик", callback_data="vtype_reel")],
    ])


VISUAL_SUBTYPE_LABELS = {"card": "Открытка", "reel": "Ролик"}


def photo_style_keyboard():
    keyboard = [
        [InlineKeyboardButton(style["title"], callback_data=f"style_{key}")]
        for key, style in PHOTO_STYLES.items()
    ]
    keyboard.append([InlineKeyboardButton("✍️ Своё описание", callback_data="style_custom")])
    return InlineKeyboardMarkup(keyboard)


def photo_done_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ Готово, отправить", callback_data="photo_done")]])


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


async def _notify_admins(context: ContextTypes.DEFAULT_TYPE, text: str, parse_mode: str = "Markdown"):
    for chat_id in NOTIFY_CHAT_IDS:
        try:
            if parse_mode:
                await context.bot.send_message(chat_id, text, parse_mode=parse_mode)
            else:
                await context.bot.send_message(chat_id, text)
        except Exception:
            pass


async def _notify_admins_photo(context: ContextTypes.DEFAULT_TYPE, file_id: str, caption: str = None):
    for chat_id in NOTIFY_CHAT_IDS:
        try:
            await context.bot.send_photo(chat_id, file_id, caption=caption)
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


async def chatid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_chat.send_message(f"ID этого чата: {update.effective_chat.id}")


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
    subtype = context.user_data.get("visual_subtype")

    brief_lines = [f"✍️ Новая заявка от {user}", f"Услуга: {svc.get('title', '—')}"]
    if subtype:
        brief_lines.append(f"Тип: {subtype}")
    for q in BRIEF_QUESTIONS:
        brief_lines.append(f"{q['text']} {answers.get(q['key'], '—')}")

    await _notify_admins(context, "\n".join(brief_lines))

    await chat.send_message(
        "Спасибо! Передала заявку Светлане, она свяжется с вами в Telegram в ближайшее время 🙌",
        reply_markup=main_menu_keyboard(),
    )
    context.user_data["mode"] = None


# --- Подтип услуги "visual": фото / открытка / ролик ---

async def _ask_visual_type(chat, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "visual_type"
    context.user_data["slug"] = "visual"
    await chat.send_message("Что хотите заказать?", reply_markup=visual_type_keyboard())


# --- Режим заказа AI-фото (услуга "visual", подтип "фото") ---

async def _start_photo_order(chat, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "photo_style"
    context.user_data["slug"] = "visual"
    await chat.send_message(
        "Отлично! Выберите стиль фотосессии или опишите свой:",
        reply_markup=photo_style_keyboard(),
    )


async def _ask_for_photos(chat, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "photo_upload"
    context.user_data["photo_count"] = 0
    await chat.send_message(
        "Пришлите одно или несколько своих фото (по одному сообщению) — хорошего качества, "
        "без фильтров и сильной обработки.\n\nКогда закончите — нажмите кнопку ниже.",
        reply_markup=photo_done_keyboard(),
    )


async def _finish_photo_order(chat, context: ContextTypes.DEFAULT_TYPE):
    style_label = context.user_data.get("photo_style", "—")
    prompt_text = context.user_data.get("photo_prompt")
    if prompt_text:
        # Без parse_mode: свой текст стиля (custom) может содержать символы,
        # которые сломают разбор Markdown и «тихо» уронят уведомление.
        message = f"🎨 Готовый промпт для генерации\nСтиль: {style_label}\n\n{prompt_text}"
        await _notify_admins(context, message, parse_mode=None)

    await chat.send_message(
        "Спасибо! Светлана подготовит фото в выбранном стиле и пришлёт лично в этот чат 🙌",
        reply_markup=main_menu_keyboard(),
    )
    # Полный сброс состояния заказа — иначе повторный тап по «старой» кнопке
    # «✅ Готово, отправить» (Telegram не отключает клавиатуру на старых
    # сообщениях) снова пройдёт проверку photo_count > 0 и продублирует
    # уведомление админам с устаревшим промптом.
    context.user_data["mode"] = None
    context.user_data["photo_count"] = 0
    context.user_data.pop("photo_style", None)
    context.user_data.pop("photo_prompt", None)


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

    if mode == "photo_custom_wait":
        context.user_data["photo_style"] = text
        context.user_data["photo_prompt"] = CUSTOM_PROMPT_TEMPLATE.replace("{description}", text)
        await _ask_for_photos(update.message.chat, context)
        return

    await _show_services_list(update.message.chat)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("mode") != "photo_upload":
        return

    user = update.effective_user
    username = getattr(user, "username", None)
    context.user_data["user_label"] = f"@{username}" if username else (user.first_name or "клиент")

    count = context.user_data.get("photo_count", 0) + 1
    context.user_data["photo_count"] = count

    style = context.user_data.get("photo_style", "—")
    caption = (
        f"🎨 Заказ AI-фото от {context.user_data['user_label']}\nСтиль: {style}"
        if count == 1 else None
    )
    file_id = update.message.photo[-1].file_id
    await _notify_admins_photo(context, file_id, caption=caption)

    await update.message.chat.send_message(
        f"Фото получено ({count}). Пришлите ещё или нажмите «✅ Готово, отправить».",
        reply_markup=photo_done_keyboard(),
    )


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
        if slug == "visual":
            await _ask_visual_type(chat, context)
            return
        context.user_data["mode"] = "brief"
        context.user_data["slug"] = slug
        context.user_data["question_step"] = 0
        context.user_data["answers"] = {}
        await _ask_next_brief_question(chat, context)
        return

    if action.startswith("vtype_"):
        vtype = action[6:]
        if vtype == "photo":
            await _start_photo_order(chat, context)
            return
        context.user_data["mode"] = "brief"
        context.user_data["slug"] = "visual"
        context.user_data["question_step"] = 0
        context.user_data["answers"] = {}
        context.user_data["visual_subtype"] = VISUAL_SUBTYPE_LABELS.get(vtype, "Видео/открытка")
        await _ask_next_brief_question(chat, context)
        return

    if action.startswith("style_"):
        key = action[6:]
        if key == "custom":
            context.user_data["mode"] = "photo_custom_wait"
            await chat.send_message(
                "Опишите, какой результат хотите получить — сцена, одежда, настроение (текстом):"
            )
            return
        style = PHOTO_STYLES.get(key)
        if not style:
            await _show_services_list(chat)
            return
        context.user_data["photo_style"] = style["title"]
        context.user_data["photo_prompt"] = style["prompt"]
        await _ask_for_photos(chat, context)
        return

    if action == "photo_done":
        if context.user_data.get("mode") != "photo_upload":
            # Старая/повторная кнопка вне активного заказа — молча игнорируем,
            # чтобы не дублировать уведомление админам (см. _finish_photo_order).
            return
        if context.user_data.get("photo_count", 0) == 0:
            await chat.send_message("Сначала пришлите хотя бы одно фото 🙂")
            return
        await _finish_photo_order(chat, context)
        return

    if action == "main_menu":
        context.user_data.clear()
        await _show_services_list(chat)
        return


def main():
    asyncio.set_event_loop(asyncio.new_event_loop())
    app = Application.builder().token(INTAKE_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("chatid", chatid_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот-консультант запущен. Нажми Ctrl+C чтобы остановить.")
    app.run_polling()


if __name__ == "__main__":
    main()
