# ИИ-помощник по контенту — Telegram-бот

Бот для создания текстов в социальные сети. Задаёт уточняющие вопросы и генерирует готовый контент через Groq API (Llama 3.3 70B).

**Бот в Telegram:** [@my_ai_svethelp_bot](https://t.me/my_ai_svethelp_bot)

## Что умеет

| Кнопка | Что создаёт |
|--------|-------------|
| 📝 Написать пост | Пост для Telegram/Instagram (тема + аудитория + тон) |
| 🎙 Голосовой ввод | Расшифровывает голосовое и пишет пост |
| 📖 Описание курса | Продающий текст для онлайн-курса |
| 🎬 Сторис-сценарий | Сценарий из 4–5 слайдов |
| 💡 Заголовки | 7 цепляющих заголовков |
| 📊 Моя история | Личная история для соцсетей |

Дополнительно:
- `/settov` — загрузи примеры своих постов, бот запомнит твой стиль
- Кнопки после генерации: ✏️ Доработать / 🔄 Новый вариант / 📋 Скопировать

## Как запустить локально

**Требования:** Python 3.10+

```bash
# 1. Клонировать репозиторий
git clone https://github.com/svetlanagolubka65-web/bot-copywriter.git
cd bot-copywriter

# 2. Установить зависимости
pip install -r requirements.txt

# 3. Создать .env из шаблона и заполнить ключи
cp .env.example .env

# 4. Запустить
python bot.py
```

## Нужные ключи (.env)

| Переменная | Где получить |
|-----------|-------------|
| `BOT_TOKEN` | [@BotFather](https://t.me/BotFather) → /newbot |
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) → API Keys |
| `ADMIN_IDS` | Твой Telegram ID (узнать через [@userinfobot](https://t.me/userinfobot)) |

## Зависимости

```
python-telegram-bot==21.5
groq==0.11.0
httpx==0.27.2
python-dotenv==1.0.0
```

## Другие проекты в репозитории

- [`nejrosveta-agent/`](nejrosveta-agent/README.md) — ИИ-агент для автоматической публикации постов (n8n + Claude)
- [`tg-faberlik-catalog/`](tg-faberlik-catalog/README.md) — концепция Telegram Mini App для каталога Фаберлик
- `svetlana-landing.html` — лендинг Светланы Голубевой
- `aleks.html`, `vizitka.html` — HTML-визитки
