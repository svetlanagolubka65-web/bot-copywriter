import os
import sys
import pathlib

os.environ.setdefault("BOT_TOKEN", "test-token")
os.environ.setdefault("GROQ_API_KEY", "test-key")
os.environ.setdefault("INTAKE_BOT_TOKEN", "test-intake-token")
os.environ.setdefault("ADMIN_IDS", "111,222,12345")
os.environ.setdefault("LEADS_CHAT_ID", "")
os.environ.setdefault("SVETLYACHOK_BOT_TOKEN", "test-svetlyachok-token")
os.environ.setdefault("ACCESS_CODE", "test-code")
os.environ.setdefault("CONSULT_LINK_URL", "")
os.environ.setdefault("LESSONS_URL", "")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import pytest
from unittest.mock import AsyncMock, MagicMock


class FakeChat:
    def __init__(self):
        self.send_message = AsyncMock()


class FakeMessage:
    """Минимальная замена telegram.Message для тестов."""
    def __init__(self):
        self.reply_text = AsyncMock()
        self.chat = FakeChat()


class FakeUser:
    def __init__(self, user_id=12345, first_name="Аня"):
        self.id = user_id
        self.first_name = first_name


class FakeUpdate:
    def __init__(self, text=None, user_id=12345, first_name="Аня"):
        self.message = FakeMessage()
        self.message.text = text
        self.effective_user = FakeUser(user_id, first_name)
        self.effective_chat = FakeChat()


class FakeQuery:
    def __init__(self, data):
        self.data = data
        self.message = FakeMessage()
        self.answer = AsyncMock()


class FakeCallbackUpdate:
    def __init__(self, data, user_id=12345):
        self.callback_query = FakeQuery(data)
        self.effective_user = FakeUser(user_id)


class FakeContext:
    def __init__(self, user_data=None):
        self.user_data = user_data if user_data is not None else {}


@pytest.fixture
def isolate_user_storage(tmp_path, monkeypatch):
    """Подменяет файлы пользователей на временные, чтобы тесты не трогали
    реальные users.json / users_data.json проекта."""
    import bot
    monkeypatch.setattr(bot, "USERS_FILE", str(tmp_path / "users.json"))
    monkeypatch.setattr(bot, "USERS_DATA_FILE", str(tmp_path / "users_data.json"))
    return tmp_path


@pytest.fixture
def isolate_svetlyachok_storage(tmp_path, monkeypatch):
    """Подменяет файл доступа Светлячка на временный, чтобы тесты не трогали
    реальный svetlyachok_access.json проекта."""
    import svetlyachok_bot
    monkeypatch.setattr(svetlyachok_bot, "ACCESS_FILE", str(tmp_path / "svetlyachok_access.json"))
    return tmp_path
