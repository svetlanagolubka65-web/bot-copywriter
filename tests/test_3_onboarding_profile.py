"""Функция 3: онбординг новых/старых пользователей и профиль (бот приватный,
владелец всегда один — Светлана, поэтому пол зафиксирован как "f" без выбора)
(bot.start, bot.save_user_profile, bot.py:20-52, 262-291)."""
import pytest
from unittest.mock import AsyncMock

import bot
from conftest import FakeContext, FakeUpdate


def test_new_user_becomes_known_after_save(isolate_user_storage):
    assert bot.is_new_user(999) is True
    bot.save_user(999)
    assert bot.is_new_user(999) is False


def test_user_profile_roundtrip(isolate_user_storage):
    assert bot.load_user_profile(555) is None
    bot.save_user_profile(555, "Марина", "f")
    profile = bot.load_user_profile(555)
    assert profile == {"name": "Марина", "gender": "f"}


@pytest.mark.asyncio
async def test_start_onboards_new_user_directly_without_gender_choice(isolate_user_storage, monkeypatch):
    onboarding_mock = AsyncMock()
    monkeypatch.setattr(bot, "send_onboarding", onboarding_mock)
    update = FakeUpdate(text="/start", user_id=111, first_name="Ирина")
    context = FakeContext()

    await bot.start(update, context)

    assert bot.is_new_user(111) is False
    update.effective_chat.send_message.assert_awaited_once()
    onboarding_mock.assert_awaited_once_with(update.effective_chat, "Ирина")
    assert context.user_data["gender"] == "f"
    assert bot.load_user_profile(111) == {"name": "Ирина", "gender": "f"}
    update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_start_greets_returning_user_without_onboarding(isolate_user_storage, monkeypatch):
    bot.save_user(222)
    onboarding_mock = AsyncMock()
    monkeypatch.setattr(bot, "send_onboarding", onboarding_mock)
    update = FakeUpdate(text="/start", user_id=222, first_name="Ирина")
    context = FakeContext()

    await bot.start(update, context)

    onboarding_mock.assert_not_awaited()
    update.message.reply_text.assert_awaited_once()
