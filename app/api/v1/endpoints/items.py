from typing import Annotated

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from app.core.dependencies import CurrentActiveUser, DbSession
from app.models.enums import ItemStatus
from app.models.item import Item
from app.repositories.item_repository import ItemRepository
from app.schemas.item import ItemCreate, ItemImageUploadRead, ItemRead, ItemUpdate
from app.services.item_service import ItemService

router = APIRouter()
SkipQuery = Annotated[int, Query(ge=0)]
LimitQuery = Annotated[int, Query(ge=1, le=100)]
CategoryQuery = Annotated[int | None, Query()]
SellerQuery = Annotated[int | None, Query()]
StatusQuery = Annotated[ItemStatus | None, Query(alias="status")]
LocationQuery = Annotated[str | None, Query(max_length=160)]
UploadImage = Annotated[UploadFile, File()]
PrimaryImageForm = Annotated[bool, Form()]


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_listing(payload: ItemCreate, current_user: CurrentActiveUser, db: DbSession) -> Item:
    return ItemService(db).create_item(current_user, payload)


@router.get("", response_model=list[ItemRead])
def read_listings(
    db: DbSession,
    category_id: CategoryQuery = None,
    seller_id: SellerQuery = None,
    status_filter: StatusQuery = None,
    location: LocationQuery = None,
    skip: SkipQuery = 0,
    limit: LimitQuery = 50,
) -> list[Item]:
    return ItemRepository(db).list(
        category_id=category_id,
        seller_id=seller_id,
        status=status_filter,
        location=location,
        skip=skip,
        limit=limit,
    )


@router.get("/{item_id}", response_model=ItemRead)
def read_listing(item_id: int, db: DbSession) -> Item:
    return ItemService(db).get_item_or_404(item_id)


@router.patch("/{item_id}", response_model=ItemRead)
def update_listing(
    item_id: int,
    payload: ItemUpdate,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> Item:
    return ItemService(db).update_item(item_id, payload, current_user)


@router.delete("/{item_id}", response_model=ItemRead)
def delete_listing(
    item_id: int,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> Item:
    return ItemService(db).cancel_item(item_id, current_user)


@router.post(
    "/{item_id}/images", response_model=ItemImageUploadRead, status_code=status.HTTP_201_CREATED
)
def upload_item_image(
    item_id: int,
    file: UploadImage,
    current_user: CurrentActiveUser,
    db: DbSession,
    is_primary: PrimaryImageForm = False,
) -> ItemImageUploadRead:
    image = ItemService(db).upload_image(item_id, file, current_user, is_primary=is_primary)
    return ItemImageUploadRead(image=image)
