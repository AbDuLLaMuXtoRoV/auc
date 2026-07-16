from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.models.item import Item, ItemImage
from app.models.user import User
from app.repositories.item_repository import ItemRepository
from app.schemas.item import ItemCreate, ItemUpdate
from app.services.storage_service import StorageService


class ItemService:
    def __init__(self, db: Session) -> None:
        self.repository = ItemRepository(db)
        self.storage = StorageService()

    def create_item(self, seller: User, payload: ItemCreate) -> Item:
        return self.repository.create(seller, payload)

    def get_item_or_404(self, item_id: int) -> Item:
        item = self.repository.get(item_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        return item

    def update_item(self, item_id: int, payload: ItemUpdate, actor: User) -> Item:
        item = self.get_item_or_404(item_id)
        self._ensure_can_manage_item(item, actor)
        return self.repository.update(item, payload)

    def cancel_item(self, item_id: int, actor: User) -> Item:
        item = self.get_item_or_404(item_id)
        self._ensure_can_manage_item(item, actor)
        return self.repository.mark_cancelled(item)

    def upload_image(
        self,
        item_id: int,
        file: UploadFile,
        actor: User,
        *,
        is_primary: bool = False,
    ) -> ItemImage:
        item = self.get_item_or_404(item_id)
        self._ensure_can_manage_item(item, actor)
        image_url = self.storage.save_upload(file, folder="items")
        return self.repository.add_image(item, image_url, is_primary=is_primary)

    def _ensure_can_manage_item(self, item: Item, actor: User) -> None:
        if actor.role == UserRole.ADMIN:
            return
        if item.seller_id != actor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your item")
