import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return self.db.scalar(statement)

    def get_by_google_sub(self, google_sub: str) -> User | None:
        return self.db.scalar(select(User).where(User.google_sub == google_sub))

    def create_from_google(
        self,
        *,
        email: str,
        google_sub: str,
        full_name: str | None,
        avatar_url: str | None,
    ) -> User:
        # Parol ustuni NOT NULL — hech kim bilmaydigan tasodifiy qiymat hash'i
        # yoziladi. Parol bilan kirish kerak bo'lsa "parolni tiklash" orqali.
        user = User(
            email=email,
            google_sub=google_sub,
            full_name=full_name,
            avatar_url=avatar_url,
            hashed_password=hash_password(secrets.token_urlsafe(32)),
            is_verified=True,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def link_google(self, user: User, *, google_sub: str, reset_password: bool) -> User:
        user.google_sub = google_sub
        user.is_verified = True
        if reset_password:
            user.hashed_password = hash_password(secrets.token_urlsafe(32))
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def list(self, *, skip: int = 0, limit: int = 100) -> list[User]:
        statement = select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(statement))

    def create(self, payload: UserCreate) -> User:
        user = User(
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: User, payload: UserUpdate) -> User:
        data = payload.model_dump(exclude_unset=True)
        # Yangi raqam hali tasdiqlanmagan — eski tasdiq unga o'tib ketmasin.
        if "phone" in data and data["phone"] != user.phone:
            user.phone_verified_at = None
        for field, value in data.items():
            setattr(user, field, value)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_password(self, user: User, password: str) -> User:
        user.hashed_password = hash_password(password)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def mark_verified(self, user: User) -> User:
        user.is_verified = True
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def set_role(self, user: User, role: UserRole) -> User:
        user.role = role
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
