from fpdf import FPDF
import os

class PDF(FPDF):
    def header(self):
        pass
    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(180, 180, 180)
        self.cell(0, 10, f"Страница {self.page_no()}", align="C")

pdf = PDF()
pdf.add_page()

FONT_DIR = r"C:\Windows\Fonts"
pdf.add_font("Arial", "",  os.path.join(FONT_DIR, "arial.ttf"),  uni=True)
pdf.add_font("Arial", "B", os.path.join(FONT_DIR, "arialbd.ttf"), uni=True)
pdf.add_font("Arial", "I", os.path.join(FONT_DIR, "ariali.ttf"),  uni=True)

GOLD   = (180, 120, 20)
DARK   = (40,  40,  40)
GRAY   = (120, 120, 120)
WHITE  = (255, 255, 255)
LIGHT  = (250, 246, 238)
LINE   = (220, 200, 160)

W = pdf.w - 2 * pdf.l_margin

# ── Шапка ────────────────────────────────────────────────────────────────────
pdf.set_fill_color(*GOLD)
pdf.rect(0, 0, pdf.w, 38, "F")

pdf.set_xy(15, 8)
pdf.set_font("Arial", "B", 20)
pdf.set_text_color(*WHITE)
pdf.cell(W, 10, "Памятка сессии с Клодом", ln=True)

pdf.set_x(15)
pdf.set_font("Arial", "I", 10)
pdf.set_text_color(255, 240, 200)
pdf.cell(W, 8, "Проверь каждый блок перед началом работы", ln=True)

pdf.ln(6)

# ── Вспомогательные функции ───────────────────────────────────────────────────

def block_title(num, title, color=GOLD):
    pdf.set_fill_color(*color)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(W, 8, f"  Блок {num}: {title}", ln=True, fill=True)
    pdf.ln(1)

def item(text, sub=False):
    x = pdf.get_x()
    y = pdf.get_y()
    # квадратик-чекбокс
    size = 4.5
    ox = pdf.l_margin + (6 if sub else 0)
    pdf.set_draw_color(*LINE)
    pdf.set_fill_color(*WHITE)
    pdf.rect(ox, y + 1.5, size, size, "FD")
    # текст
    pdf.set_xy(ox + size + 3, y)
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(*DARK)
    indent = ox + size + 3 - pdf.l_margin
    pdf.cell(W - indent, 7, text, ln=True)

def note(text):
    pdf.set_x(pdf.l_margin + 3)
    pdf.set_font("Arial", "I", 8.5)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(W - 3, 5, text)
    pdf.ln(1)

def sep():
    pdf.ln(3)
    pdf.set_draw_color(*LINE)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + W, pdf.get_y())
    pdf.ln(3)

# ── БЛОК 1 ────────────────────────────────────────────────────────────────────
block_title(1, "Перед началом сессии")
item("Открыть CLAUDE.md — прочитать структуру и правила")
item("Открыть Plan.md — найти первый TODO или BLOCKED")
item("Сверить: какая сейчас фаза проекта (0–6)?")
sep()

# ── БЛОК 2 ────────────────────────────────────────────────────────────────────
block_title(2, "Бот @my_ai_svethelp_bot")
item("Бот отвечает в Telegram (написать /start)")
item("BOT_TOKEN и GROQ_API_KEY заполнены в .env")
item("users.json не в git (есть в .gitignore)")
note("Если бот не отвечает — запустить: python bot.py")
sep()

# ── БЛОК 3 ────────────────────────────────────────────────────────────────────
block_title(3, "НейроСвета агент (n8n)")
item("ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN, GOOGLE_SHEETS_ID заполнены в nejrosveta-agent/.env")
item("n8n запускается: npx n8n start → localhost:5678")
item("3 workflow импортированы в n8n (agent1, agent2, agent3)")
item("Google Sheets создана и содержит 4 листа по схеме")
note("Схема Sheets: nejrosveta-agent/memory/sheets_schema.md")
sep()

# ── БЛОК 4 ────────────────────────────────────────────────────────────────────
block_title(4, "Документация актуальна")
item("README.md соответствует текущему коду")
item("ARCHITECTURE.md описывает реальную архитектуру")
item(".env.example содержит все нужные переменные (без значений)")
note("Правило: после каждого изменения кода — обновить документы.")
sep()

# ── БЛОК 5 ────────────────────────────────────────────────────────────────────
block_title(5, "Git")
item("git status чистый (нет незакоммиченных изменений)")
item(".env не в git — проверить: он есть в .gitignore")
item("Последний коммит понятно описывает что сделано")
sep()

# ── БЛОК 6 ────────────────────────────────────────────────────────────────────
pdf.set_fill_color(*LIGHT)
pdf.set_draw_color(*GOLD)

# Рамка блока 6
bx = pdf.l_margin
by = pdf.get_y()
pdf.set_font("Arial", "B", 11)
pdf.set_text_color(*GOLD)
pdf.cell(W, 8, "  Блок 6: Главный промпт для Клода", ln=True, fill=True, border=1)

pdf.set_fill_color(*LIGHT)
pdf.set_x(pdf.l_margin)
pdf.set_font("Arial", "I", 9)
pdf.set_text_color(100, 70, 10)
pdf.multi_cell(W, 6,
    "Если хоть один пункт выше не отмечен — скопируй этот промпт и отправь Клоду:",
    fill=True, border="LR")

pdf.set_x(pdf.l_margin)
pdf.set_font("Arial", "", 10)
pdf.set_text_color(*DARK)

prompt_text = (
    'Прочитай CLAUDE.md и Plan.md в корне проекта. Найди первую задачу со статусом TODO '
    'или BLOCKED в таблице прогресса. Проверь текущее состояние .env (без вывода значений), '
    'git status, и запущен ли бот. После этого скажи — что именно сейчас нужно сделать '
    'и с чего начнём эту сессию.'
)
pdf.set_fill_color(255, 252, 240)
pdf.multi_cell(W, 6, prompt_text, fill=True, border="LR")

pdf.set_x(pdf.l_margin)
pdf.set_font("Arial", "", 1)
pdf.cell(W, 3, "", ln=True, fill=True, border="LRB")

pdf.ln(8)

# ── Напоминание в низу ────────────────────────────────────────────────────────
pdf.set_font("Arial", "I", 9)
pdf.set_text_color(*GRAY)
pdf.cell(W, 6,
    "Фазы: 0-Фундамент  1-Сборщик  2-Редактор  3-TG Бот  4-Деплой  5-Голос  6-TG Парсер",
    align="C", ln=True)

OUT = r"c:\Users\Светлана\Desktop\проекты с HTML\Памятка_Клод.pdf"
pdf.output(OUT)
print(f"PDF создан: {OUT}")
