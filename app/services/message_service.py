from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.message import Conversation, Message
from app.models.user import User
from app.repositories.item_repository import ItemRepository
from app.repositories.message_repository import MessageRepository
from app.schemas.message import ConversationCreate, MessageCreate


class MessageService:
    def __init__(self, db: Session) -> None:
        self.items = ItemRepository(db)
        self.messages = MessageRepository(db)

    def create_conversation(self, buyer: User, payload: ConversationCreate) -> Conversation:
        item = self.items.get(payload.item_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

        seller_id = payload.seller_id if payload.seller_id is not None else item.seller_id
        if seller_id != item.seller_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seller does not own this item",
            )
        if buyer.id == seller_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seller cannot start a buyer conversation for their own item",
            )
        return self.messages.create_conversation(
            item_id=item.id,
            buyer_id=buyer.id,
            seller_id=seller_id,
        )

    def list_conversations(self, user: User) -> list[Conversation]:
        return self.messages.list_conversations(user.id)

    def get_conversation_for_user(self, conversation_id: int, user: User) -> Conversation:
        conversation = self.messages.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
            )
        self._ensure_participant(conversation, user)
        return conversation

    def send_message(
        self,
        conversation_id: int,
        sender: User,
        payload: MessageCreate,
    ) -> Message:
        conversation = self.get_conversation_for_user(conversation_id, sender)
        return self.messages.create_message(conversation, sender_id=sender.id, body=payload.body)

    def mark_message_read(self, message_id: int, user: User) -> Message:
        message = self.messages.get_message(message_id)
        if message is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
        conversation = self.get_conversation_for_user(message.conversation_id, user)
        if message.sender_id == user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sender cannot mark their own message as read",
            )
        self._ensure_participant(conversation, user)
        return self.messages.mark_message_read(message)

    def _ensure_participant(self, conversation: Conversation, user: User) -> None:
        if user.id not in {conversation.buyer_id, conversation.seller_id}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not your conversation",
            )
