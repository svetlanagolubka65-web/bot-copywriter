"""Функция 1: генерация контента через Groq API (bot.generate_from_answers, bot.py:334)."""
import pytest
from unittest.mock import MagicMock

import bot
from conftest import FakeMessage, FakeContext


def make_groq_response(text):
    resp = MagicMock()
    resp.choices = [MagicMock(message=MagicMock(content=text))]
    return resp


@pytest.mark.asyncio
async def test_success_path_stores_result_and_replies(monkeypatch):
    monkeypatch.setattr(
        bot.groq_client.chat.completions, "create",
        MagicMock(return_value=make_groq_response("Готовый пост про запуск курса"))
    )
    message = FakeMessage()
    context = FakeContext({
        "content_type": "📝 Написать пост",
        "answers": {"topic": "запуск курса", "audience": "предприниматели", "tone": "🔥 Вдохновляющий"},
        "gender": "f",
    })

    await bot.generate_from_answers(message, context)

    assert context.user_data["last_result"] == "Готовый пост про запуск курса"
    message.reply_text.assert_awaited_once()
    args, kwargs = message.reply_text.await_args
    assert args[0] == "Готовый пост про запуск курса"
    assert "reply_markup" in kwargs


@pytest.mark.asyncio
async def test_groq_exception_falls_back_gracefully(monkeypatch):
    monkeypatch.setattr(
        bot.groq_client.chat.completions, "create",
        MagicMock(side_effect=RuntimeError("Groq API down"))
    )
    message = FakeMessage()
    context = FakeContext({
        "content_type": "📝 Написать пост",
        "answers": {"topic": "тема", "audience": "аудитория", "tone": "😊 Дружелюбный"},
    })

    await bot.generate_from_answers(message, context)

    assert "last_result" not in context.user_data
    message.reply_text.assert_awaited_once()
    args, _ = message.reply_text.await_args
    assert "Не получилось" in args[0]


@pytest.mark.asyncio
async def test_incomplete_answers_crash_before_reaching_groq(monkeypatch):
    """RED (реальный баг): bot.py:339-342. Если в answers не хватает audience/tone,
    первый .format(**answers) бросает KeyError. Обработчик `except KeyError` пытается
    пересобрать промпт через .format(topic=answers.get("topic", ...), **answers) —
    но answers уже содержит ключ "topic", поэтому Python получает его дважды
    (именованным аргументом и через **answers) и падает с
    `TypeError: format() got multiple values for keyword argument 'topic'`.
    Это исключение ничем не перехватывается и вылетает из функции наружу —
    пользователь не получает вообще никакого ответа от бота."""
    message = FakeMessage()
    context = FakeContext({
        "content_type": "📝 Написать пост",
        "answers": {"topic": "тема без остальных ответов"},
    })

    with pytest.raises(TypeError, match="multiple values"):
        await bot.generate_from_answers(message, context)
