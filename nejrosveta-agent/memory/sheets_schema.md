# Google Sheets — схема памяти агента

**ID таблицы:** заполни после создания → `GOOGLE_SHEETS_ID` в `.env`

---

## Лист 1: `news_archive`

Архив использованных новостей — нужен для дедупликации.

| Колонка | Тип | Описание |
|---------|-----|----------|
| `date` | Дата (ДД.ММ.ГГГГ) | Когда новость была обработана |
| `title` | Текст | Заголовок новости |
| `url` | Текст | Ссылка (по ней проверяем дубли) |
| `source` | Текст | Источник (OpenAI, Google AI, и т.д.) |
| `used` | TRUE/FALSE | TRUE = пост по этой новости был одобрен |

---

## Лист 2: `style_memory`

Архив одобренных и отклонённых постов — обучает агента голосу Светланы.

| Колонка | Тип | Описание |
|---------|-----|----------|
| `date` | Дата | Когда пост был создан |
| `format` | Текст | format1_news / format2_tool / format3_story |
| `post_text` | Текст | Полный текст поста |
| `approved` | TRUE/FALSE | TRUE = Светлана нажала ✅ |
| `reject_reason` | Текст | Причина отказа (если нажала ❌ + написала почему) |

---

## Лист 3: `content_balance`

Счётчик форматов по неделям — не даёт одному формату доминировать.

| Колонка | Тип | Описание |
|---------|-----|----------|
| `week` | Текст | Неделя в формате 2026-W25 |
| `format1_count` | Число | Сколько раз использовался формат 1 |
| `format2_count` | Число | Сколько раз использовался формат 2 |
| `format3_count` | Число | Сколько раз использовался формат 3 |

---

## Лист 4: `sources_config`

Конфигурация источников и текущего курса — редактируется вручную.

| Колонка | Тип | Описание |
|---------|-----|----------|
| `type` | Текст | RSS или API |
| `name` | Текст | Название источника |
| `url` | Текст | URL RSS-ленты или API |
| `active` | TRUE/FALSE | TRUE = использовать |
| `course_name` | Текст | Название текущего курса (для CTA в format3) |
| `course_url` | Текст | Ссылка на курс |

### Начальные данные для `sources_config`

| type | name | url | active | course_name | course_url |
|------|------|-----|--------|-------------|------------|
| RSS | OpenAI Blog | https://openai.com/blog/rss.xml | TRUE | | |
| RSS | Google AI Blog | https://blog.google/technology/ai/rss/ | TRUE | | |
| RSS | Hugging Face | https://huggingface.co/blog/feed.xml | TRUE | | |
| RSS | MIT Tech Review | https://www.technologyreview.com/feed/ | TRUE | | |
| API | GNews | https://gnews.io/api/v4/search?q=artificial+intelligence&lang=en&token={GNEWS_API_KEY} | TRUE | Название курса | https://ссылка-на-курс |

> **Важно:** Заполни `course_name` и `course_url` в последней строке — агент подтянет их автоматически для CTA в формате 3.
