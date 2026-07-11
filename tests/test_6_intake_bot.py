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
        self.send_photo = AsyncMock()


class FakePhotoSize:
    def __init__(self, file_id):
        self.file_id = file_id


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

    assert update.effective_chat.send_message.await_count == 2
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
async def test_callback_brief_other_service_starts_question_flow():
    update = FakeCallbackUpdate(data="brief_song")
    context = FakeIntakeContext()

    await intake_bot.handle_callback(update, context)

    assert context.user_data["mode"] == "brief"
    assert context.user_data["slug"] == "song"
    assert context.user_data["question_step"] == 0
    update.callback_query.message.chat.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_callback_brief_visual_asks_subtype_first():
    update = FakeCallbackUpdate(data="brief_visual")
    context = FakeIntakeContext()

    await intake_bot.handle_callback(update, context)

    assert context.user_data["mode"] == "visual_type"
    assert context.user_data["slug"] == "visual"
    update.callback_query.message.chat.send_message.assert_awaited_once()
    args, kwargs = update.callback_query.message.chat.send_message.await_args
    assert "заказать" in args[0].lower()
    assert "reply_markup" in kwargs


# --- Подтип "visual": фото / открытка / ролик ---

@pytest.mark.asyncio
async def test_callback_vtype_photo_starts_photo_style_flow():
    update = FakeCallbackUpdate(data="vtype_photo")
    context = FakeIntakeContext(user_data={"mode": "visual_type", "slug": "visual"})

    await intake_bot.handle_callback(update, context)

    assert context.user_data["mode"] == "photo_style"
    update.callback_query.message.chat.send_message.assert_awaited_once()
    args, _ = update.callback_query.message.chat.send_message.await_args
    assert "стиль" in args[0].lower()


@pytest.mark.asyncio
async def test_callback_vtype_card_starts_generic_brief_with_subtype():
    update = FakeCallbackUpdate(data="vtype_card")
    context = FakeIntakeContext(user_data={"mode": "visual_type", "slug": "visual"})

    await intake_bot.handle_callback(update, context)

    assert context.user_data["mode"] == "brief"
    assert context.user_data["slug"] == "visual"
    assert context.user_data["visual_subtype"] == "Открытка"
    assert context.user_data["question_step"] == 0


@pytest.mark.asyncio
async def test_full_brief_flow_with_visual_subtype_notifies_admins():
    update = FakeUpdate(text="Открытка на день рождения маме")
    context = FakeIntakeContext(user_data={
        "mode": "brief", "slug": "visual", "visual_subtype": "Открытка",
        "question_step": 0, "answers": {},
    })

    await intake_bot.handle_message(update, context)
    update.message.text = "Через 2 дня"
    await intake_bot.handle_message(update, context)
    update.message.text = "1500 рублей"
    await intake_bot.handle_message(update, context)

    assert context.bot.send_message.await_count == len(intake_bot.ADMIN_IDS)
    brief_text = context.bot.send_message.await_args_list[0].args[1]
    assert "Тип: Открытка" in brief_text
    assert "Открытка на день рождения маме" in brief_text


# --- Заказ AI-фото (услуга "visual", подтип "фото") ---

@pytest.mark.asyncio
async def test_callback_style_preset_asks_for_photos():
    update = FakeCallbackUpdate(data="style_beach")
    context = FakeIntakeContext(user_data={"mode": "photo_style", "slug": "visual"})

    await intake_bot.handle_callback(update, context)

    assert context.user_data["mode"] == "photo_upload"
    assert context.user_data["photo_style"] == "🏖 Пляж на закате"
    assert context.user_data["photo_count"] == 0
    assert "песчаном пляже" in context.user_data["photo_prompt"]


@pytest.mark.asyncio
async def test_callback_style_custom_waits_for_description():
    update = FakeCallbackUpdate(data="style_custom")
    context = FakeIntakeContext(user_data={"mode": "photo_style", "slug": "visual"})

    await intake_bot.handle_callback(update, context)

    assert context.user_data["mode"] == "photo_custom_wait"


@pytest.mark.asyncio
async def test_custom_description_text_moves_to_photo_upload():
    update = FakeUpdate(text="Зимний лес, тёплый свитер, кружка какао")
    context = FakeIntakeContext(user_data={"mode": "photo_custom_wait"})

    await intake_bot.handle_message(update, context)

    assert context.user_data["mode"] == "photo_upload"
    assert context.user_data["photo_style"] == "Зимний лес, тёплый свитер, кружка какао"
    assert context.user_data["photo_count"] == 0
    assert "Зимний лес, тёплый свитер, кружка какао" in context.user_data["photo_prompt"]
    assert "Сохрани черты лица" in context.user_data["photo_prompt"]


@pytest.mark.asyncio
async def test_photo_upload_forwards_to_admins_and_counts():
    update = FakeUpdate()
    update.message.photo = [FakePhotoSize("file_1")]
    context = FakeIntakeContext(user_data={
        "mode": "photo_upload", "photo_style": "🏖 Пляж на закате", "photo_count": 0,
    })

    await intake_bot.handle_photo(update, context)

    assert context.user_data["photo_count"] == 1
    assert context.bot.send_photo.await_count == len(intake_bot.ADMIN_IDS)
    args, kwargs = context.bot.send_photo.await_args
    assert args[1] == "file_1"
    assert "Пляж на закате" in kwargs["caption"]
    update.message.chat.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_second_photo_forwards_without_caption():
    update = FakeUpdate()
    update.message.photo = [FakePhotoSize("file_2")]
    context = FakeIntakeContext(user_data={
        "mode": "photo_upload", "photo_style": "🏖 Пляж на закате", "photo_count": 1,
    })

    await intake_bot.handle_photo(update, context)

    assert context.user_data["photo_count"] == 2
    _, kwargs = context.bot.send_photo.await_args
    assert kwargs["caption"] is None


@pytest.mark.asyncio
async def test_photo_done_without_photos_asks_to_send_first():
    update = FakeCallbackUpdate(data="photo_done")
    context = FakeIntakeContext(user_data={"mode": "photo_upload", "photo_count": 0})

    await intake_bot.handle_callback(update, context)

    args, _ = update.callback_query.message.chat.send_message.await_args
    assert "хотя бы одно фото" in args[0]
    assert context.user_data["mode"] == "photo_upload"


@pytest.mark.asyncio
async def test_stale_photo_done_outside_photo_upload_mode_is_ignored():
    """Пользователь мог тапнуть старую кнопку «Готово, отправить» с уже
    завершённого или чужого заказа — не должно дублировать уведомление."""
    update = FakeCallbackUpdate(data="photo_done")
    context = FakeIntakeContext(user_data={
        "mode": "qa", "slug": "consult", "photo_count": 2,
        "photo_style": "🏖 Пляж на закате", "photo_prompt": "старый промпт",
    })

    await intake_bot.handle_callback(update, context)

    context.bot.send_message.assert_not_awaited()
    update.callback_query.message.chat.send_message.assert_not_awaited()
    assert context.user_data["mode"] == "qa"


@pytest.mark.asyncio
async def test_finish_photo_order_clears_state_to_prevent_duplicate_on_restale_tap():
    update = FakeCallbackUpdate(data="photo_done")
    context = FakeIntakeContext(user_data={
        "mode": "photo_upload", "photo_count": 2,
        "photo_style": "🏖 Пляж на закате", "photo_prompt": "Сгенерируй...",
    })

    await intake_bot.handle_callback(update, context)
    assert context.user_data["photo_count"] == 0
    assert "photo_style" not in context.user_data
    assert "photo_prompt" not in context.user_data

    # Повторный тап той же кнопки после завершения — должен быть проигнорирован.
    context.bot.send_message.reset_mock()
    update2 = FakeCallbackUpdate(data="photo_done")
    await intake_bot.handle_callback(update2, context)
    context.bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_photo_done_with_photos_confirms_and_resets_mode():
    update = FakeCallbackUpdate(data="photo_done")
    context = FakeIntakeContext(user_data={
        "mode": "photo_upload", "photo_count": 2,
        "photo_style": "🏖 Пляж на закате", "photo_prompt": "Сгенерируй молодую женщину на пляже...",
    })

    await intake_bot.handle_callback(update, context)

    assert context.user_data["mode"] is None
    args, kwargs = update.callback_query.message.chat.send_message.await_args
    assert "Светлана" in args[0]
    assert "reply_markup" in kwargs

    assert context.bot.send_message.await_count == len(intake_bot.ADMIN_IDS)
    prompt_args, prompt_kwargs = context.bot.send_message.await_args
    assert "Готовый промпт" in prompt_args[1]
    assert "Сгенерируй молодую женщину на пляже" in prompt_args[1]
    assert "parse_mode" not in prompt_kwargs


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
