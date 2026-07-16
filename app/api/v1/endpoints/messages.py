from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, DbSession
from app.models.message import Conversation, Message
from app.schemas.message import (
    ConversationCreate,
    ConversationDetailRead,
    ConversationRead,
    MessageCreate,
    MessageRead,
)
from app.services.message_service import MessageService

router = APIRouter()


@router.post("/conversations", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
def start_conversation(
    payload: ConversationCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> Conversation:
    return MessageService(db).create_conversation(current_user, payload)


@router.get("/conversations", response_model=list[ConversationRead])
def read_conversations(current_user: CurrentUser, db: DbSession) -> list[Conversation]:
    return MessageService(db).list_conversations(current_user)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailRead)
def read_conversation(
    conversation_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> Conversation:
    return MessageService(db).get_conversation_for_user(conversation_id, current_user)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
)
def send_message(
    conversation_id: int,
    payload: MessageCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> Message:
    return MessageService(db).send_message(conversation_id, current_user, payload)


@router.patch("/messages/{message_id}/read", response_model=MessageRead)
def mark_message_read(
    message_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> Message:
    return MessageService(db).mark_message_read(message_id, current_user)
