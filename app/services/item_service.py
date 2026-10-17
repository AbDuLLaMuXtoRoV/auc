from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import is_admin
from app.models.item import Item, ItemImage
from app.models.user import User
from app.repositories.item_repository import ItemRepository
from app.repositories.region_repository import RegionRepository
from app.schemas.item import ItemCreate, ItemUpdate
from app.services.storage_service import StorageService


class ItemService:
    def __init__(self, db: Session) -> None:
        self.repository = ItemRepository(db)
        self.regions = RegionRepository(db)
        self.storage = StorageService()

    def create_item(self, seller: User, payload: ItemCreate) -> Item:
        self._validate_location(payload.region_id, payload.district_id)
        return self.repository.create(seller, payload)

    def get_item_or_404(self, item_id: int) -> Item:
        item = self.repository.get(item_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        return item

    def update_item(self, item_id: int, payload: ItemUpdate, actor: User) -> Item:
        item = self.get_item_or_404(item_id)
        self._ensure_can_manage_item(item, actor)
        # Qisman yangilash: berilmagan maydon mavjud qiymat bilan birga tekshiriladi.
        fields = payload.model_fields_set
        region_id = payload.region_id if "region_id" in fields else item.region_id
        district_id = payload.district_id if "district_id" in fields else item.district_id
        self._validate_location(region_id, district_id)
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
        # Har lotdagi rasm sonini cheklaymiz — storage suiiste'moli va
        # og'ir ro'yxat sahifasining oldini oladi.
        if len(item.item_images) >= settings.max_images_per_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Rasm limiti oshib ketdi (maks {settings.max_images_per_item})",
            )
        image_url = self.storage.save_upload(file, folder="items")
        return self.repository.add_image(item, image_url, is_primary=is_primary)

    def _validate_location(self, region_id: int | None, district_id: int | None) -> None:
        """Tuman tanlangan viloyatga tegishli bo'lishi shart.

        Aks holda lot ziddiyatli manzil bilan saqlanib, hudud filtri bo'yicha
        noto'g'ri natija beradi (yoki boshqa viloyat qidiruvida chiqadi).
        """
        if region_id is not None and self.regions.get_region(region_id) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown region")
        if district_id is None:
            return
        district = self.regions.get_district(district_id)
        if district is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown district")
        if district.region_id != region_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="District does not belong to the selected region",
            )

    def _ensure_can_manage_item(self, item: Item, actor: User) -> None:
        if is_admin(actor.role):
            return
        if item.seller_id != actor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your item")
