session_store: list[dict[str, int | str]] = [
    {
        "session_id": 1,
        "session_user": "abc",
        "created_at": "2025-06-30T16:00:00",
    }
]

chat_store: dict[int, list[dict[str, str]]] = {
    1: [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
}
