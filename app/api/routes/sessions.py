from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, field_validator

from app.core.session_store import chat_store, session_store

router = APIRouter(tags=["sessions"])


class CreateSessionRequest(BaseModel):
    session_user: str

    @field_validator("session_user", mode="before")
    @classmethod
    def normalize_session_user(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("session_user must be a string")

        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("session_user must not be empty")

        return normalized


class CreateSessionResponse(BaseModel):
    session_id: int
    session_user: str
    created_at: str


class MessageRequest(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class MessageResponse(BaseModel):
    role: Literal["user", "assistant"]
    content: str


@router.post(
    "/sessions",
    response_model=CreateSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_session(request: CreateSessionRequest) -> CreateSessionResponse:
    session_id = len(session_store) + 1
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    session = {
        "session_id": session_id,
        "session_user": request.session_user,
        "created_at": created_at,
    }

    session_store.append(session)
    chat_store[session_id] = []

    return CreateSessionResponse(**session)


@router.post(
    "/sessions/{session_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_message(session_id: int, request: MessageRequest) -> MessageResponse:
    if not any(session["session_id"] == session_id for session in session_store):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    response = MessageResponse(role=request.role, content=request.content)
    chat_store[session_id].append({"role": response.role, "content": response.content})
    return response


@router.get(
    "/sessions/{session_id}/messages",
    response_model=list[MessageResponse],
)
def get_messages(
    session_id: int,
    role: Literal["user", "assistant"] | None = Query(default=None),
) -> list[MessageResponse]:
    if not any(session["session_id"] == session_id for session in session_store):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    messages = chat_store[session_id]
    if role is not None:
        messages = [message for message in messages if message["role"] == role]

    return [MessageResponse(**message) for message in messages]
