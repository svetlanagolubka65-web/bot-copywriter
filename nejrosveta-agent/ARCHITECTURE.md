# Архитектура: НейроСвета ИИ-Агент

## Общая схема

```
Расписание 08:00 МСК
        │
        ▼
   Agent 1 (Сборщик)
   RSS × 4 источника
   Фильтр 24ч + дедупликация
   Claude → топ-3 новости
        │
        ▼
   Agent 2 (Редактор)
   Google Sheets → стиль Светланы (last 10 постов)
   Google Sheets → текущий курс (название + ссылка)
   Claude × 3 → format1 + format2 + format3
   Валидация длины + наличия CTA
        │
        ▼
   Agent 3 (Планировщик)
   Проверка баланса форматов (content_balance)
   Telegram → 3 поста с кнопками
        │
        ▼
   Светлана нажимает ✅ / 🔄 / ❌
        │
        ▼
   Google Sheets → сохранение результата
```

## Три агента

### Agent 1 — Сборщик (`agent1_collector.json`)
- Schedule Trigger 07:45 МСК
- RSS Feed из 4 источников (OpenAI, Google AI, Hugging Face, MIT Tech Review)
- GNews API (запасной источник)
- Фильтр: только за последние 24 часа
- Google Sheets Read → `news_archive` → исключить уже использованные URL
- Claude: выбрать топ-3 по релевантности для русскоязычной ИИ-аудитории
- Если 0 новостей → Telegram-уведомление Светлане, не падение

### Agent 2 — Редактор (`agent2_editor.json`)
- Получает топ-3 новости от Agent 1
- Google Sheets Read → `style_memory` (последние 10 одобренных постов — few-shot примеры)
- Google Sheets Read → `sources_config` (актуальный курс + ссылка)
- Claude × 3 параллельно: генерирует format1 + format2 + format3
- Валидация: длина 600–1500 символов, format3 содержит CTA
- При провале валидации — retry (max 2 попытки)

### Agent 3 — Планировщик (`agent3_planner.json`)
- Google Sheets Read → `content_balance` → проверить, какой формат нужен сегодня
- Отправляет 3 поста в Telegram с inline-кнопками
- Обрабатывает нажатия:
  - ✅ → пишет пост в `style_memory` + URL в `news_archive`
  - ❌ → запрашивает причину → пишет `reject_reason` в `style_memory`
  - 🔄 → вызывает Agent 2 для перегенерации одного формата
- Обновляет `content_balance`

## Три формата постов

| Формат | Стиль | Длина | Продажа |
|--------|-------|-------|---------|
| Format 1: Горячая новость | Эксперт думает вслух | 800–1200 симв. | Нет |
| Format 2: Инструмент/Лайфхак | Структурированное руководство | 600–1000 симв. | Мягкая |
| Format 3: История + курс | Личная история Светланы | 1000–1500 симв. | Да (CTA) |

## Google Sheets — структура памяти (4 листа)

| Лист | Колонки | Назначение |
|------|---------|-----------|
| `news_archive` | date, title, url, source, used | Дедупликация новостей |
| `style_memory` | date, format, post_text, approved, reject_reason | Few-shot примеры голоса Светланы |
| `content_balance` | week, format1_count, format2_count, format3_count | Баланс форматов по неделям |
| `sources_config` | type, name, url, active, course_name, course_url | RSS-источники + активный курс |

## RSS-источники

| Источник | URL |
|----------|-----|
| OpenAI Blog | `https://openai.com/blog/rss.xml` |
| Google AI | `https://blog.google/technology/ai/rss/` |
| Hugging Face | `https://huggingface.co/blog/feed.xml` |
| MIT Tech Review | `https://www.technologyreview.com/feed/` |

## Деплой

- **Dockerfile** — образ на базе `n8nio/n8n:latest`, часовой пояс Europe/Moscow
- **railway.toml** — builder DOCKERFILE, healthcheck `/healthz`, restart on failure
- Все workflow хранятся в `n8n/workflows/` как JSON — импортируются через n8n UI
