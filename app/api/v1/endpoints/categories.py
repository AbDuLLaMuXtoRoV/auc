from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.dependencies import CurrentAdmin, DbSession
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryRead

router = APIRouter()


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_item_category(
    payload: CategoryCreate,
    _admin: CurrentAdmin,
    db: DbSession,
) -> Category:
    if payload.parent_id is not None and db.get(Category, payload.parent_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent category not found",
        )

    category = Category(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.get("", response_model=list[CategoryRead])
def read_categories(db: DbSession) -> list[Category]:
    statement = select(Category).order_by(Category.name.asc())
    return list(db.scalars(statement))
