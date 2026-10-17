from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DbSession
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    TelegramLink,
    UserMeRead,
    UserPreferencesUpdate,
    UserRead,
    UserUpdate,
)

router = APIRouter()


@router.get("/me", response_model=UserMeRead)
def read_profile(current_user: CurrentUser) -> User:
    # Egaga o'zining shaxsiy maydonlari (telegram_chat_id, til) ham qaytadi.
    return current_user


@router.patch("/me", response_model=UserRead)
def update_profile(payload: UserUpdate, current_user: CurrentUser, db: DbSession) -> User:
    return UserRepository(db).update(current_user, payload)


@router.post("/me/telegram", response_model=UserMeRead)
def link_telegram(payload: TelegramLink, current_user: CurrentUser, db: DbSession) -> User:
    """Autentifikatsiyalangan foydalanuvchi o'z Telegram chat'ini ulaydi.

    Faqat o'ziga: `current_user` orqali — begona chat_id boshqa akkauntga
    biriktirilmaydi. Ulangach, bildirishnomalar shu chat'ga ham yetkaziladi.
    """
    current_user.telegram_chat_id = payload.chat_id
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.patch("/me/preferences", response_model=UserMeRead)
def update_preferences(
    payload: UserPreferencesUpdate, current_user: CurrentUser, db: DbSession
) -> User:
    """Foydalanuvchi interfeys tilini (uz/ru) yangilaydi — faqat o'ziniki."""
    current_user.preferred_language = payload.preferred_language
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user
