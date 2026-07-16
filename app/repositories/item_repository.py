from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.enums import ItemStatus
from app.models.item import Item, ItemImage
from app.models.user import User
from app.schemas.item import ItemCreate, ItemUpdate


class ItemRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, seller: User, payload: ItemCreate) -> Item:
        item = Item(seller_id=seller.id, **payload.model_dump())
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list(
        self,
        *,
        category_id: int | None = None,
        seller_id: int | None = None,
        status: ItemStatus | None = None,
        location: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Item]:
        statement = select(Item).order_by(Item.created_at.desc()).offset(skip).limit(limit)
        if category_id is not None:
            statement = statement.where(Item.category_id == category_id)
        if seller_id is not None:
            statement = statement.where(Item.seller_id == seller_id)
        if status is not None:
            statement = statement.where(Item.status == status)
        if location:
            # TODO: Replace this basic text match with geo-distance search.
            location_pattern = f"%{location}%"
            statement = statement.where(
                or_(
                    Item.location.ilike(location_pattern),
                    Item.item_location.ilike(location_pattern),
                )
            )
        return list(self.db.scalars(statement))

    def get(self, item_id: int) -> Item | None:
        return self.db.get(Item, item_id)

    def update(self, item: Item, payload: ItemUpdate) -> Item:
        data = payload.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(item, field, value)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def mark_cancelled(self, item: Item) -> Item:
        item.status = ItemStatus.CANCELLED
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def add_image(self, item: Item, image_url: str, *, is_primary: bool = False) -> ItemImage:
        if is_primary:
            for image in item.item_images:
                image.is_primary = False
                self.db.add(image)

        item_image = ItemImage(item_id=item.id, image_url=image_url, is_primary=is_primary)
        item.images = [*item.images, image_url]
        self.db.add(item)
        self.db.add(item_image)
        self.db.commit()
        self.db.refresh(item_image)
        return item_image
