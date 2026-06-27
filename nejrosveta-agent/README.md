# НейроСвета ИИ-Агент

Персональный ИИ-агент для Светланы Голубевой (@GolubkaSveta). Каждое утро в 08:00 МСК собирает новости об ИИ, генерирует 3 поста в авторском стиле и присылает на выбор в Telegram. Светлана одобряет пост сама — агент не публикует автономно.

## Что делает

1. **08:00 МСК** — автоматически запускается по расписанию
2. **Agent 1** собирает новости из RSS за последние 24 часа, убирает дубли, отдаёт топ-3
3. **Agent 2** генерирует 3 поста через Claude в стиле Светланы (3 разных формата)
4. **Agent 3** отправляет посты в Telegram с кнопками: ✅ Опубликовать / 🔄 Переписать / ❌ Пропустить
5. Одобренный пост сохраняется в Google Sheets как пример стиля

## Стек

| Компонент | Инструмент |
|-----------|-----------|
| Оркестратор | n8n self-hosted |
| Хостинг | Railway.app (~$5–10/мес) |
| ИИ-модель | Anthropic Claude (Opus) |
| Источники новостей | RSS-ленты + GNews API |
| Память | Google Sheets (4 листа) |
| Интерфейс | Telegram Bot API |

## Как запустить локально

**Требования:** Node.js ≥ 18

```bash
# Установить n8n
npm install -g n8n

# Заполнить переменные окружения
cp .env.example .env
# → открыть .env и вставить ключи

# Запустить n8n
npx n8n start
# → открыть http://localhost:5678

# Импортировать workflows через интерфейс n8n:
# Settings → Import from file → выбрать agent1_collector.json, agent2_editor.json, agent3_planner.json
```

## Нужные ключи (.env)

| Переменная | Где получить |
|-----------|-------------|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) → API Keys |
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) → /newbot |
| `GOOGLE_SHEETS_ID` | URL таблицы: `docs.google.com/spreadsheets/d/{ID}` |
| `GNEWS_API_KEY` | [gnews.io](https://gnews.io) (free: 100 запросов/день) |
| `N8N_ENCRYPTION_KEY` | Любая строка 32+ символа: `openssl rand -hex 32` |

## Деплой на Railway

```bash
# Установить Railway CLI
npm install -g @railway/cli

# Войти и задеплоить
railway login
railway up
```

Переменные окружения добавить в Railway → Settings → Variables.

## Статус проекта

- ✅ Фаза 1–3: Агенты написаны и готовы к импорту
- 🔄 Фаза 4: Деплой на Railway
- 🔲 v2: Голосовой ввод (Whisper), парсер TG-каналов конкурентов

Подробнее: [Plan.md](../Plan.md)
