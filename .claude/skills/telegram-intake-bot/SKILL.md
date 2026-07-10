---
name: telegram-intake-bot
description: Use when Светлана asks to build a new Telegram bot linked from a landing page (a "consultant"/intake bot that answers questions grounded in real pricing/FAQ and collects leads), or to deploy any Python Telegram bot in this repo to Railway. Covers the full playbook from code to live bot, based on how intake_bot.py (@Superkosultantbot) was built and shipped.
---

# Telegram intake-bot playbook

Основано на реальном опыте создания `intake_bot.py` (@Superkosultantbot) — бота-консультанта, на который ведут плашки услуг на лендинге `index.html`. Используй этот файл как чек-лист, если Светлана просит что-то похожее: новый бот, привязанный к лендингу/услугам, или деплой любого Python-бота в этом репо на Railway.

## Когда применять

- «Нужен бот, который отвечает на вопросы клиентов и/или собирает заявки» → раздел «Код бота».
- «Как задеплоить бота» / «бот не отвечает, он же нигде не запущен» → раздел «Деплой на Railway».
- «Бот падает при старте» на этой машине → см. «Известная проблема: Python 3.14».

## Код бота

Не выдумывай архитектуру с нуля — копируй паттерн из `bot.py` (уже есть в репозитории, протестирован, прошёл ревью):

- Стек: `python-telegram-bot` (async, `Application.builder()...run_polling()`), `groq` для генерации/ответов, `python-dotenv` для конфига. Все зависимости уже есть в `requirements.txt` — новых почти никогда не нужно.
- Пошаговый опрос (несколько уточняющих вопросов подряд) — паттерн `ask_next_question` / `save_answer_and_continue` из `bot.py:298-327`, с состоянием в `context.user_data`.
- Если бот отвечает на свободные вопросы через LLM — **обязательно грузи факты (цены, сроки, FAQ) в системный промпт из реального контента лендинга**, и явно вели модели говорить «не знаю, уточню у Светланы», а не выдумывать цифры. См. `KNOWLEDGE_BASE`/`QA_SYSTEM_PROMPT` в `intake_bot.py`.
- Единый интерфейс отправки: функции-хелперы принимают **chat**, а не message, и шлют через `chat.send_message(...)` — тогда один и тот же код работает и из `start()` (`update.effective_chat`), и из callback-хендлера (`query.message.chat`), и из обработчика текста (`update.message.chat`). См. `ARCHITECTURE.md` → «Единый интерфейс отправки сообщений».
- Токен бота — **новый**, отдельный от других ботов в репо (создаётся через @BotFather → `/newbot`), переменная вида `<ИМЯ>_BOT_TOKEN` в `.env`/`.env.example`. Не переиспользуй чужой `BOT_TOKEN`.
- Если нужны уведомления администратору (заявки, вопросы без ответа) — не хардкодь один Telegram ID. Сделай список через запятую (`ADMIN_IDS`), и по возможности — опциональную переменную вида `LEADS_CHAT_ID` для отдельной группы (см. «Группа для заявок» ниже). Одна и та же функция-хелпер типа `_notify_admins` должна перебирать список ID и слать каждому, не падая, если один из адресатов недоступен (`try/except` на каждой отправке).

### Группа для заявок вместо личных сообщений

Личные сообщения от бота смешивают тестовые сообщения владельца с реальными заявками клиентов — неудобно. Лучше сразу закладывать поддержку отдельной группы:

1. В коде: `LEADS_CHAT_ID = os.getenv("LEADS_CHAT_ID")`, и `NOTIFY_CHAT_IDS = [int(LEADS_CHAT_ID)] if LEADS_CHAT_ID else ADMIN_IDS` — если группа не настроена, откатываемся на личные ID.
2. Добавь служебную команду `/chatid`, которая отвечает `update.effective_chat.id` — это единственный надёжный способ узнать ID группы (через `getUpdates` его не вытащить, если бот уже развёрнут и сам всё «съедает» поллингом).
3. Светлана вручную: создаёт группу → добавляет туда бота → пишет в группе `/chatid` (именно с `/`, иначе Telegram Privacy Mode бота проигнорирует обычное сообщение) → присылает тебе ID (число вида `-1234567890`, **со знаком минус** — это легко потерять при копировании, проверяй явно).
4. Вписываешь ID в `LEADS_CHAT_ID` — локально в `.env` и на хостинге (переменные сервиса).

## Известная проблема: Python 3.14 + python-telegram-bot 21.5

На этой машине стоит Python 3.14, где `asyncio.get_event_loop()` больше не создаёт loop неявно — `Application.run_polling()` из PTB 21.5 падает с `RuntimeError: There is no current event loop in thread 'MainThread'` при каждом локальном запуске `python <bot>.py`. Это не баг твоего кода — чини сразу в `main()` любого нового бота:

```python
import asyncio

def main():
    asyncio.set_event_loop(asyncio.new_event_loop())
    app = Application.builder().token(TOKEN).build()
    ...
    app.run_polling()
```

Безвредно на любой версии Python, не требует смены зависимостей.

## Тесты

Копируй конвенции `tests/conftest.py` (`FakeChat`/`FakeMessage`/`FakeUpdate`/`FakeCallbackUpdate`, `AsyncMock` на `send_message`/`reply_text`, мок `groq_client.chat.completions.create` через `monkeypatch`). Для нового бота:
- В `conftest.py` добавь `os.environ.setdefault("<ИМЯ>_BOT_TOKEN", "test-token")` и любые новые переменные (например `LEADS_CHAT_ID`) **с пустым/тестовым значением** — иначе `load_dotenv()` подхватит реальный `.env` этой машины и тесты будут падать на настоящих значениях (проверено на практике, см. коммит про `LEADS_CHAT_ID`).
- Прогоняй `pytest tests/ -v` перед каждым коммитом.

## Деплой на Railway

У Светланы уже есть аккаунт Railway (`railway.app`) с проектом **`caring-commitment`**, подключённым к репозиторию `bot-copywriter` (GitHub: `svetlanagolubka65-web/bot-copywriter`). В нём уже живёт сервис **`bot-copywriter`** (запускает `bot.py`). **Не путай с проектом `soothing-eagerness`** — это другой, не связанный репозиторий (каталог/магазин, не бот).

Шаги для нового бота (делает **Светлана вручную**, ты — только пошагово диктуешь, что нажимать, по её скриншотам):

1. Открыть проект `caring-commitment` на дашборде Railway.
2. **«+ Add»** (кнопка в правом верхнем углу холста) → **«GitHub Repository»** → выбрать `svetlanagolubka65-web/bot-copywriter`.
3. В новом сервисе → **Settings → Deploy → Custom Start Command** → вписать `python <новый_файл>.py`.
4. **Variables** → Railway сам подсвечивает «Suggested Variables», найденные в коде (по `os.getenv(...)`), но со значениями-плейсхолдерами из `.env.example` — их нужно заменить на реальные (бери из локального `.env`). Лишние (например, `BOT_TOKEN` другого бота) — можно удалить крестиком, вреда не будет и если оставить.
5. **«Deploy»** (кнопка сверху, ⇧+Enter) → дождаться статуса **ACTIVE / Deployment successful**.
6. **Важно:** если до этого бот тестировался локально (`python <файл>.py` в фоне на этой машине) — обязательно останови локальный процесс после успешного деплоя, иначе два поллера на одном токене будут конфликтовать и бот перестанет отвечать. Проверка/остановка:
   ```powershell
   Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object { $_.CommandLine -like '*<файл>.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
   ```
7. Автодеплой на Railway уже настроен на `git push origin main` — после первого ручного деплоя все последующие изменения долетают сами, следующий `git push` подхватывается без повторного похода в Railway UI (но ей всё равно можно проверить статус на дашборде).

## Лендинг: ссылки на бота

Если бот открывается с конкретных элементов лендинга (плашки, кнопки) — используй Telegram deep link с параметром, а не голый `t.me/username`:
```
https://t.me/<username>?start=<slug>
```
Код в `start()` читает `context.args[0]` и показывает контент под конкретный `slug`. Это тот же паттерн, что и `?start=texts`, `?start=song` и т.д. в `intake_bot.py`.

**Перед тем как трогать `index.html`** — проверь `git status`/`git fetch origin` на расхождения: Светлана иногда правит лендинг напрямую через веб-интерфейс GitHub (коммиты «Add files via upload»), параллельно с работой в сессии. Если `git status -sb` показывает `[behind N]` — сначала `git pull`/`git merge`, разреши конфликты вручную (сохраняя обе стороны: её визуальные правки + твои ссылки), и только потом пуш.

## Документация

По правилу `CLAUDE.md`: после кода — сразу обнови `README.md` (короткое описание бота, ссылка на него, нужные ключи в `.env`) и `ARCHITECTURE.md` (схема флоу, ключевые структуры, ограничения — в первую очередь то, что дублируется вручную и может рассинхронизироваться, например тексты цен/FAQ между ботом и лендингом).

## Как общаться со Светланой при деплое

Она не разработчик — при работе с Railway/BotFather диктуй **очень конкретные, атомарные шаги** («нажмите вот эту кнопку»), проси скриншот на каждом шаге, не предполагай, что она знает термины (event loop, deep link, Procfile и т.п. — только если объясняешь). Не проси её делать несколько шагов сразу.
