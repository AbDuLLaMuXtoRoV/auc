from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DbSession
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserRead, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserRead)
def read_profile(current_user: CurrentUser) -> User:
    return current_user


@router.patch("/me", response_model=UserRead)
def update_profile(payload: UserUpdate, current_user: CurrentUser, db: DbSession) -> User:
    return UserRepository(db).update(current_user, payload)
