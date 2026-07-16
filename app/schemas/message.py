from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    item_id: int
    seller_id: int | None = None


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    buyer_id: int
    seller_id: int
    item_id: int | None
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    sender_id: int
    body: str
    is_read: bool
    created_at: datetime


class ConversationDetailRead(ConversationRead):
    messages: list[MessageRead] = Field(default_factory=list)
