"""Бот-консультант для плашек услуг на лендинге (intake_bot.py):
карточка услуги по deep-link, свободные вопросы через Groq, сбор брифа
и уведомления администратору (ADMIN_IDS)."""
import pytest
from unittest.mock import AsyncMock, MagicMock

import intake_bot
from conftest import FakeUpdate, FakeCallbackUpdate


class FakeBot:
    def __init__(self):
        self.send_message = AsyncMock()


class FakeIntakeContext:
    def __init__(self, user_data=None, args=None):
        self.user_data = user_data if user_data is not None else {}
        self.args = args or []
        self.bot = FakeBot()


def make_groq_response(text):
    resp = MagicMock()
    resp.choices = [MagicMock(message=MagicMock(content=text))]
    return resp


# --- /start ---

@pytest.mark.asyncio
async def test_start_with_known_slug_shows_service_card():
    update = FakeUpdate()
    context = FakeIntakeContext(args=["texts"])

    await intake_bot.start(update, context)

    update.effective_chat.send_message.assert_awaited_once()
    args, kwargs = update.effective_chat.send_message.await_args
    assert "Генерация и редактирование текстов" in args[0]
    assert "4 500" in args[0]
    assert context.user_data["slug"] == "texts"


@pytest.mark.asyncio
async def test_start_without_args_shows_services_list():
    update = FakeUpdate()
    context = FakeIntakeContext()

    await intake_bot.start(update, context)

    assert update.effective_chat.send_message.await_count == 2
    _, last_kwargs = update.effective_chat.send_message.await_args
    assert "reply_markup" in last_kwargs
    assert "slug" not in context.user_data


@pytest.mark.asyncio
async def test_start_with_unknown_slug_falls_back_to_services_list():
    update = FakeUpdate()
    context = FakeIntakeContext(args=["nonexistent"])

    await intake_bot.start(update, context)

    assert update.effective_chat.send_message.await_count == 2
    assert "slug" not in context.user_data


# --- Свободные вопросы (режим qa) ---

@pytest.mark.asyncio
async def test_qa_confident_answer_does_not_notify_admins(monkeypatch):
    monkeypatch.setattr(
        intake_bot.groq_client.chat.completions, "create",
        MagicMock(return_value=make_groq_response("Стоимость текстового пакета — от 4 500 ₽."))
    )
    update = FakeUpdate(text="Сколько стоит пакет текстов?")
    context = FakeIntakeContext(user_data={"mode": "qa", "slug": "texts"})

    await intake_bot.handle_message(update, context)

    update.message.chat.send_message.assert_awaited_once()
    args, _ = update.message.chat.send_message.await_args
    assert "4 500" in args[0]
    context.bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_qa_groq_exception_notifies_all_admins(monkeypatch):
    monkeypatch.setattr(
        intake_bot.groq_client.chat.completions, "create",
        MagicMock(side_effect=Exception("groq down"))
    )
    update = FakeUpdate(text="Есть скидка для НКО?")
    context = FakeIntakeContext(user_data={"mode": "qa", "slug": "prompts"})

    await intake_bot.handle_message(update, context)

    assert context.bot.send_message.await_count == len(intake_bot.ADMIN_IDS)
    update.message.chat.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_qa_uncertain_answer_notifies_admins(monkeypatch):
    monkeypatch.setattr(
        intake_bot.groq_client.chat.completions, "create",
        MagicMock(return_value=make_groq_response("Точно не отвечу — уточню у Светланы."))
    )
    update = FakeUpdate(text="А если нужно сразу на трёх языках?")
    context = FakeIntakeContext(user_data={"mode": "qa", "slug": "texts"})

    await intake_bot.handle_message(update, context)

    assert context.bot.send_message.await_count == len(intake_bot.ADMIN_IDS)


# --- Сбор брифа (режим brief) ---

@pytest.mark.asyncio
async def test_full_brief_flow_notifies_admins_and_confirms_client():
    update = FakeUpdate(text="Песня на юбилей маме")
    context = FakeIntakeContext(user_data={
        "mode": "brief", "slug": "song", "question_step": 0, "answers": {},
    })

    await intake_bot.handle_message(update, context)
    assert context.user_data["question_step"] == 1
    assert context.user_data["answers"]["task"] == "Песня на юбилей маме"

    update.message.text = "Через неделю"
    await intake_bot.handle_message(update, context)
    assert context.user_data["question_step"] == 2

    update.message.text = "5000 рублей"
    await intake_bot.handle_message(update, context)

    assert context.bot.send_message.await_count == len(intake_bot.ADMIN_IDS)
    brief_text = context.bot.send_message.await_args_list[0].args[1]
    assert "Персональные песни на заказ" in brief_text
    assert "Песня на юбилей маме" in brief_text
    assert "Через неделю" in brief_text
    assert "5000 рублей" in brief_text

    last_args, last_kwargs = update.message.chat.send_message.await_args
    assert "Светлане" in last_args[0]
    assert "reply_markup" in last_kwargs


# --- Callback-кнопки ---

@pytest.mark.asyncio
async def test_callback_ask_sets_qa_mode_and_prompts():
    update = FakeCallbackUpdate(data="ask_consult")
    context = FakeIntakeContext()

    await intake_bot.handle_callback(update, context)

    assert context.user_data["mode"] == "qa"
    assert context.user_data["slug"] == "consult"
    update.callback_query.message.chat.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_callback_brief_starts_question_flow():
    update = FakeCallbackUpdate(data="brief_visual")
    context = FakeIntakeContext()

    await intake_bot.handle_callback(update, context)

    assert context.user_data["mode"] == "brief"
    assert context.user_data["slug"] == "visual"
    assert context.user_data["question_step"] == 0
    update.callback_query.message.chat.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_callback_unknown_slug_falls_back_to_services_list():
    update = FakeCallbackUpdate(data="svc_doesnotexist")
    context = FakeIntakeContext()

    await intake_bot.handle_callback(update, context)

    update.callback_query.message.chat.send_message.assert_awaited_once()
    assert "slug" not in context.user_data


@pytest.mark.asyncio
async def test_callback_main_menu_clears_state():
    update = FakeCallbackUpdate(data="main_menu")
    context = FakeIntakeContext(user_data={"mode": "brief", "slug": "song"})

    await intake_bot.handle_callback(update, context)

    assert context.user_data.get("mode") is None
    assert "slug" not in context.user_data
    update.callback_query.message.chat.send_message.assert_awaited_once()
