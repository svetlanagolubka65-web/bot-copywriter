"""Функция 3: онбординг новых/старых пользователей и профиль имя+пол
(bot.start, bot.save_user_profile, bot.handle_callback gender_*, bot.py:20-52, 262-291, 469-477)."""
import pytest
from unittest.mock import AsyncMock

import bot
from conftest import FakeContext, FakeUpdate, FakeCallbackUpdate


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
async def test_start_asks_gender_for_new_user_before_onboarding(isolate_user_storage):
    update = FakeUpdate(text="/start", user_id=111, first_name="Ирина")
    context = FakeContext()

    await bot.start(update, context)

    assert bot.is_new_user(111) is False
    update.effective_chat.send_message.assert_awaited_once()
    _, kwargs = update.effective_chat.send_message.await_args
    assert kwargs["reply_markup"] == bot.gender_keyboard()
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


@pytest.mark.asyncio
async def test_gender_choice_completes_onboarding_and_persists(isolate_user_storage):
    """Фикс bot.py:266-272: start() для нового пользователя теперь сразу показывает
    gender_keyboard(). Клик по ней (эмулируется через handle_callback с
    action="gender_m") сохраняет профиль и запускает send_onboarding — то есть
    выбор пола реально достижим и его результат сохраняется."""
    update = FakeUpdate(text="/start", user_id=333, first_name="Игорь")
    await bot.start(update, FakeContext())  # эмулируем первый /start

    context = FakeContext({"name": "Игорь"})
    callback_update = FakeCallbackUpdate("gender_m", user_id=333)

    await bot.handle_callback(callback_update, context)

    assert context.user_data["gender"] == "m"
    assert bot.load_user_profile(333) == {"name": "Игорь", "gender": "m"}
    callback_update.callback_query.message.chat.send_message.assert_awaited()
