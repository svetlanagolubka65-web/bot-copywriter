"""Функция 2: многошаговый флоу вопросов
(bot.ask_next_question / save_answer_and_continue / handle_message, bot.py:300-461)."""
import pytest
from unittest.mock import AsyncMock

import bot
from conftest import FakeMessage, FakeContext, FakeUpdate


@pytest.mark.asyncio
async def test_full_flow_reaches_generation_after_last_question(monkeypatch):
    generate_mock = AsyncMock()
    monkeypatch.setattr(bot, "generate_from_answers", generate_mock)

    message = FakeMessage()
    context = FakeContext({"content_type": "🎬 Сторис-сценарий", "question_step": 0, "answers": {}})

    await bot.save_answer_and_continue(message, context, "тема сторис")
    assert context.user_data["question_step"] == 1
    assert context.user_data["answers"]["topic"] == "тема сторис"
    generate_mock.assert_not_awaited()

    await bot.save_answer_and_continue(message, context, "перейти по ссылке")
    assert context.user_data["question_step"] == 2
    assert context.user_data["answers"]["goal"] == "перейти по ссылке"
    generate_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_switching_content_type_mid_flow_resets_progress():
    update = FakeUpdate(text="🎠 Карусель")
    context = FakeContext({
        "content_type": "📝 Написать пост",
        "question_step": 1,
        "answers": {"topic": "старая тема"},
    })

    await bot.handle_message(update, context)

    assert context.user_data["content_type"] == "🎠 Карусель"
    assert context.user_data["question_step"] == 0
    assert context.user_data["answers"] == {}


@pytest.mark.asyncio
async def test_free_text_reply_to_button_question_preserves_progress(monkeypatch):
    """Фикс bot.py:447-453: ветка №5 в handle_message больше не требует отсутствия
    кнопок у текущего вопроса ("buttons" not in questions[step] убрано). Теперь
    свободный текст, присланный вместо клика по кнопке (шаг "тон" в формате
    "Написать пост"), принимается как ответ на активный вопрос — topic и audience,
    собранные на предыдущих шагах, больше не теряются."""
    generate_mock = AsyncMock()
    monkeypatch.setattr(bot, "generate_from_answers", generate_mock)

    update = FakeUpdate(text="пусть будет позитивный")
    context = FakeContext({
        "content_type": "📝 Написать пост",
        "question_step": 2,  # шаг с кнопками (тон)
        "answers": {"topic": "как я запустила курс", "audience": "новички"},
    })

    await bot.handle_message(update, context)

    assert context.user_data["answers"]["topic"] == "как я запустила курс"
    assert context.user_data["answers"]["audience"] == "новички"
    assert context.user_data["answers"]["tone"] == "пусть будет позитивный"
    assert context.user_data["question_step"] == 3
    generate_mock.assert_awaited_once()
