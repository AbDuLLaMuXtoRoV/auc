from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    EMAIL_VERIFICATION_TOKEN_TYPE,
    PASSWORD_RESET_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_email_verification_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    revoke_token,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AccessToken, Token, UserCreate


class AuthService:
    def __init__(self, db: Session) -> None:
        self.users = UserRepository(db)

    def register_user(self, payload: UserCreate) -> User:
        # TODO: Add email verification, rate limiting, and audit logging before production.
        existing_user = self.users.get_by_email(payload.email)
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered",
            )
        return self.users.create(payload)

    def login_user(self, email: str, password: str) -> Token:
        # TODO: Add refresh tokens, account lockout, and suspicious-login detection.
        user = self.users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return self._create_token_pair(user)

    def refresh_access_token(self, refresh_token: str) -> AccessToken:
        payload = decode_token(refresh_token, expected_type=REFRESH_TOKEN_TYPE)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        user = self.users.get_by_id(int(payload["sub"]))
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        return AccessToken(access_token=create_access_token(subject=str(user.id)))

    def logout_user(self, access_token: str, refresh_token: str | None = None) -> None:
        revoke_token(access_token)
        if refresh_token is not None:
            revoke_token(refresh_token)

    def create_password_reset_token_for_email(self, email: str) -> str | None:
        # TODO: Persist reset token metadata and send this token by email instead of returning it.
        user = self.users.get_by_email(email)
        if user is None:
            return None
        return create_password_reset_token(subject=str(user.id))

    def reset_password(self, token: str, new_password: str) -> None:
        payload = decode_token(token, expected_type=PASSWORD_RESET_TOKEN_TYPE)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid password reset token",
            )

        user = self.users.get_by_id(int(payload["sub"]))
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid password reset token",
            )
        self.users.update_password(user, new_password)
        revoke_token(token)

    def create_email_verification_token_for_user(self, user: User) -> str:
        # TODO: Send this token by email and store verification attempt metadata.
        return create_email_verification_token(subject=str(user.id))

    def verify_email(self, token: str) -> User:
        payload = decode_token(token, expected_type=EMAIL_VERIFICATION_TOKEN_TYPE)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email verification token",
            )

        user = self.users.get_by_id(int(payload["sub"]))
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email verification token",
            )
        verified_user = self.users.mark_verified(user)
        revoke_token(token)
        return verified_user

    def _create_token_pair(self, user: User) -> Token:
        return Token(
            access_token=create_access_token(subject=str(user.id)),
            refresh_token=create_refresh_token(subject=str(user.id)),
        )
