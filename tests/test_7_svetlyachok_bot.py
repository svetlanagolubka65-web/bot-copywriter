"""Бот-консультант «Светлячок» (svetlyachok_bot.py): доступ по общему коду курса,
меню из 8 разделов, случайный промпт и передача заявки на консультацию Светлане."""
import pytest
from unittest.mock import AsyncMock

import svetlyachok_bot
from conftest import FakeUpdate, FakeCallbackUpdate


class FakeBot:
    def __init__(self):
        self.send_message = AsyncMock()


class FakeSvetlyachokContext:
    def __init__(self, user_data=None):
        self.user_data = user_data if user_data is not None else {}
        self.bot = FakeBot()


# --- Доступ по коду ---

@pytest.mark.asyncio
async def test_start_without_access_asks_for_code(isolate_svetlyachok_storage):
    update = FakeUpdate(user_id=999)
    context = FakeSvetlyachokContext()

    await svetlyachok_bot.start(update, context)

    update.effective_chat.send_message.assert_awaited_once()
    args, _ = update.effective_chat.send_message.await_args
    assert "код доступа" in args[0].lower()
    assert context.user_data["mode"] == "awaiting_code"


@pytest.mark.asyncio
async def test_correct_code_grants_access_and_shows_menu(isolate_svetlyachok_storage):
    update = FakeUpdate(text="  Test-Code  ", user_id=999)
    context = FakeSvetlyachokContext(user_data={"mode": "awaiting_code"})

    await svetlyachok_bot.handle_message(update, context)

    assert update.message.chat.send_message.await_count == 2
    last_args, last_kwargs = update.message.chat.send_message.await_args
    assert "reply_markup" in last_kwargs
    assert svetlyachok_bot.has_access(999)


@pytest.mark.asyncio
async def test_wrong_code_does_not_grant_access(isolate_svetlyachok_storage):
    update = FakeUpdate(text="неверный", user_id=999)
    context = FakeSvetlyachokContext(user_data={"mode": "awaiting_code"})

    await svetlyachok_bot.handle_message(update, context)

    args, _ = update.message.chat.send_message.await_args
    assert "не найден" in args[0].lower()
    assert not svetlyachok_bot.has_access(999)


@pytest.mark.asyncio
async def test_start_with_existing_access_shows_menu_directly(isolate_svetlyachok_storage):
    svetlyachok_bot.grant_access(999)
    update = FakeUpdate(user_id=999)
    context = FakeSvetlyachokContext()

    await svetlyachok_bot.start(update, context)

    update.effective_chat.send_message.assert_awaited_once()
    args, kwargs = update.effective_chat.send_message.await_args
    assert "Светлячок" in args[0]
    assert "reply_markup" in kwargs


@pytest.mark.asyncio
async def test_message_without_access_and_without_pending_code_reasks(isolate_svetlyachok_storage):
    update = FakeUpdate(text="🖼 Создать картинку", user_id=999)
    context = FakeSvetlyachokContext()

    await svetlyachok_bot.handle_message(update, context)

    args, _ = update.message.chat.send_message.await_args
    assert "код доступа" in args[0].lower()


# --- Разделы главного меню ---

@pytest.mark.asyncio
async def test_image_section_shows_items_keyboard(isolate_svetlyachok_storage):
    svetlyachok_bot.grant_access(999)
    update = FakeUpdate(text="🖼 Создать картинку", user_id=999)
    context = FakeSvetlyachokContext()

    await svetlyachok_bot.handle_message(update, context)

    args, kwargs = update.message.chat.send_message.await_args
    assert "Kandinsky" in args[0] or "промпт" in args[0].lower()
    assert "reply_markup" in kwargs


@pytest.mark.asyncio
async def test_lesson_section_without_url_shows_placeholder(isolate_svetlyachok_storage, monkeypatch):
    monkeypatch.setattr(svetlyachok_bot, "LESSONS_URL", "")
    svetlyachok_bot.grant_access(999)
    update = FakeUpdate(text="📚 Найти урок", user_id=999)
    context = FakeSvetlyachokContext()

    await svetlyachok_bot.handle_message(update, context)

    args, _ = update.message.chat.send_message.await_args
    assert "скоро появится" in args[0].lower()


@pytest.mark.asyncio
async def test_lesson_section_with_url_sends_link(isolate_svetlyachok_storage, monkeypatch):
    monkeypatch.setattr(svetlyachok_bot, "LESSONS_URL", "https://example.com/lessons")
    svetlyachok_bot.grant_access(999)
    update = FakeUpdate(text="📚 Найти урок", user_id=999)
    context = FakeSvetlyachokContext()

    await svetlyachok_bot.handle_message(update, context)

    args, _ = update.message.chat.send_message.await_args
    assert "https://example.com/lessons" in args[0]


@pytest.mark.asyncio
async def test_random_prompt_returns_one_of_known_items(isolate_svetlyachok_storage):
    svetlyachok_bot.grant_access(999)
    update = FakeUpdate(text="💡 Получить промпт", user_id=999)
    context = FakeSvetlyachokContext()

    await svetlyachok_bot.handle_message(update, context)

    args, kwargs = update.message.chat.send_message.await_args
    all_titles = [
        title for section in svetlyachok_bot.SECTIONS.values() for title, _ in section["items"]
    ]
    assert any(title in args[0] for title in all_titles)
    assert "reply_markup" in kwargs


@pytest.mark.asyncio
async def test_call_svetlana_sends_link_and_notifies_admins(isolate_svetlyachok_storage, monkeypatch):
    monkeypatch.setattr(svetlyachok_bot, "CONSULT_LINK_URL", "https://calendly.com/svetlana")
    monkeypatch.setattr(svetlyachok_bot, "ADMIN_IDS", [111])
    svetlyachok_bot.grant_access(999)
    update = FakeUpdate(text="👩 Позвать Светлану", user_id=999)
    context = FakeSvetlyachokContext()

    await svetlyachok_bot.handle_message(update, context)

    args, _ = update.message.chat.send_message.await_args
    assert "https://calendly.com/svetlana" in args[0]
    context.bot.send_message.assert_awaited_once()
    notify_args, _ = context.bot.send_message.await_args
    assert notify_args[0] == 111


@pytest.mark.asyncio
async def test_call_svetlana_without_link_falls_back_to_personal_message(isolate_svetlyachok_storage, monkeypatch):
    monkeypatch.setattr(svetlyachok_bot, "CONSULT_LINK_URL", "")
    svetlyachok_bot.grant_access(999)
    update = FakeUpdate(text="👩 Позвать Светлану", user_id=999)
    context = FakeSvetlyachokContext()

    await svetlyachok_bot.handle_message(update, context)

    args, _ = update.message.chat.send_message.await_args
    assert "напишите светлане" in args[0].lower()


# --- Callback-кнопки ---

@pytest.mark.asyncio
async def test_callback_back_menu_shows_main_menu(isolate_svetlyachok_storage):
    update = FakeCallbackUpdate(data="back_menu", user_id=999)
    context = FakeSvetlyachokContext()

    await svetlyachok_bot.handle_callback(update, context)

    update.callback_query.answer.assert_awaited_once()
    args, kwargs = update.callback_query.message.chat.send_message.await_args
    assert "Светлячок" in args[0]
    assert "reply_markup" in kwargs


@pytest.mark.asyncio
async def test_callback_item_shows_full_prompt(isolate_svetlyachok_storage):
    update = FakeCallbackUpdate(data="item_image_0", user_id=999)
    context = FakeSvetlyachokContext()

    await svetlyachok_bot.handle_callback(update, context)

    args, kwargs = update.callback_query.message.chat.send_message.await_args
    expected_title, expected_prompt = svetlyachok_bot.SECTIONS["image"]["items"][0]
    assert expected_title in args[0]
    assert expected_prompt in args[0]
    assert kwargs.get("parse_mode") == "Markdown"
