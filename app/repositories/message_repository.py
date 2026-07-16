from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.message import Conversation, Message


class MessageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_conversation(self, *, item_id: int, buyer_id: int, seller_id: int) -> Conversation:
        conversation = Conversation(item_id=item_id, buyer_id=buyer_id, seller_id=seller_id)
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def list_conversations(self, user_id: int) -> list[Conversation]:
        statement = (
            select(Conversation)
            .where(or_(Conversation.buyer_id == user_id, Conversation.seller_id == user_id))
            .order_by(Conversation.updated_at.desc())
        )
        return list(self.db.scalars(statement))

    def get_conversation(self, conversation_id: int) -> Conversation | None:
        statement = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        return self.db.scalar(statement)

    def create_message(self, conversation: Conversation, *, sender_id: int, body: str) -> Message:
        message = Message(conversation_id=conversation.id, sender_id=sender_id, body=body)
        conversation.updated_at = datetime.now(UTC)
        self.db.add(conversation)
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def get_message(self, message_id: int) -> Message | None:
        return self.db.get(Message, message_id)

    def mark_message_read(self, message: Message) -> Message:
        message.is_read = True
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message
