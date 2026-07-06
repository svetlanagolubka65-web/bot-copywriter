"""Функция 4: действия с готовым текстом — доработать/новый вариант/хэштеги/меню
(bot.handle_callback, bot.py:463-534)."""
import pytest
from unittest.mock import AsyncMock, MagicMock

import bot
from conftest import FakeCallbackUpdate, FakeContext
from test_1_generation import make_groq_response


@pytest.mark.asyncio
async def test_regenerate_calls_generation_again(monkeypatch):
    generate_mock = AsyncMock()
    monkeypatch.setattr(bot, "generate_from_answers", generate_mock)
    update = FakeCallbackUpdate("regenerate")
    context = FakeContext({"last_result": "старый текст"})

    await bot.handle_callback(update, context)

    generate_mock.assert_awaited_once()
    update.callback_query.message.reply_text.assert_awaited()


@pytest.mark.asyncio
async def test_refine_sets_waiting_flag_without_calling_groq(monkeypatch):
    create_mock = MagicMock()
    monkeypatch.setattr(bot.groq_client.chat.completions, "create", create_mock)
    update = FakeCallbackUpdate("refine")
    context = FakeContext({"last_result": "текст для доработки"})

    await bot.handle_callback(update, context)

    assert context.user_data["waiting_refine"] is True
    create_mock.assert_not_called()


@pytest.mark.asyncio
async def test_hashtags_without_prior_result_shows_message_and_skips_groq(monkeypatch):
    create_mock = MagicMock()
    monkeypatch.setattr(bot.groq_client.chat.completions, "create", create_mock)
    update = FakeCallbackUpdate("hashtags")
    context = FakeContext({})  # last_result отсутствует

    await bot.handle_callback(update, context)

    create_mock.assert_not_called()
    args, _ = update.callback_query.message.reply_text.await_args
    assert "не найден" in args[0].lower()


@pytest.mark.asyncio
async def test_hashtags_groq_failure_reports_error_not_crash(monkeypatch):
    monkeypatch.setattr(
        bot.groq_client.chat.completions, "create",
        MagicMock(side_effect=RuntimeError("timeout"))
    )
    update = FakeCallbackUpdate("hashtags")
    context = FakeContext({"last_result": "готовый пост"})

    await bot.handle_callback(update, context)

    last_call_args, _ = update.callback_query.message.reply_text.await_args
    assert "Не получилось" in last_call_args[0]


@pytest.mark.asyncio
async def test_main_menu_preserves_profile_but_clears_flow_state():
    update = FakeCallbackUpdate("main_menu")
    context = FakeContext({
        "name": "Оля",
        "gender": "m",
        "tov": "мой стиль письма",
        "content_type": "📝 Написать пост",
        "question_step": 2,
        "answers": {"topic": "x"},
        "last_result": "текст",
        "waiting_refine": True,
    })

    await bot.handle_callback(update, context)

    assert context.user_data == {"name": "Оля", "gender": "m", "tov": "мой стиль письма"}
