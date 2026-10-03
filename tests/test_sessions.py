from copy import deepcopy
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.session_store import chat_store, session_store
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_stores() -> Any:
    original_sessions = deepcopy(session_store)
    original_chats = deepcopy(chat_store)
    yield
    session_store[:] = original_sessions
    chat_store.clear()
    chat_store.update(original_chats)


def test_create_session_normalizes_username_and_initializes_chat() -> None:
    response = client.post("/sessions", json={"session_user": "  Alice  "})

    assert response.status_code == 201
    assert response.json()["session_id"] == 2
    assert response.json()["session_user"] == "alice"
    assert response.json()["created_at"].endswith("+00:00")
    assert chat_store[2] == []


@pytest.mark.parametrize("username", ["", "   "])
def test_create_session_rejects_empty_username(username: str) -> None:
    response = client.post("/sessions", json={"session_user": username})

    assert response.status_code == 422


def test_add_message_to_session() -> None:
    response = client.post(
        "/sessions/1/messages",
        json={"role": "user", "content": "What is AI?"},
    )

    assert response.status_code == 201
    assert response.json() == {"role": "user", "content": "What is AI?"}
    assert chat_store[1][-1] == {"role": "user", "content": "What is AI?"}


def test_add_message_rejects_unknown_session() -> None:
    response = client.post(
        "/sessions/999/messages",
        json={"role": "user", "content": "Hello"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Session not found"}


def test_add_message_rejects_invalid_role() -> None:
    response = client.post(
        "/sessions/1/messages",
        json={"role": "system", "content": "Do something"},
    )

    assert response.status_code == 422


def test_get_all_messages_for_session() -> None:
    response = client.get("/sessions/1/messages")

    assert response.status_code == 200
    assert response.json() == [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        ("user", [{"role": "user", "content": "Hello"}]),
        ("assistant", [{"role": "assistant", "content": "Hi there!"}]),
    ],
)
def test_get_messages_filters_by_role(role: str, expected: list[dict[str, str]]) -> None:
    response = client.get("/sessions/1/messages", params={"role": role})

    assert response.status_code == 200
    assert response.json() == expected


def test_get_messages_rejects_unknown_session() -> None:
    response = client.get("/sessions/999/messages")

    assert response.status_code == 404
    assert response.json() == {"detail": "Session not found"}


def test_get_messages_rejects_invalid_role_filter() -> None:
    response = client.get("/sessions/1/messages", params={"role": "system"})

    assert response.status_code == 422
