from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import bcrypt
import jwt
from jwt import PyJWTError

from app.core.config import settings

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"
PASSWORD_RESET_TOKEN_TYPE = "password_reset"
EMAIL_VERIFICATION_TOKEN_TYPE = "email_verification"

_REVOKED_TOKEN_IDS: set[str] = set()


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    expires_at = datetime.now(UTC) + expires_delta
    payload = {
        "sub": subject,
        "exp": expires_at,
        "type": token_type,
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(subject: str) -> str:
    return create_token(
        subject=subject,
        token_type=ACCESS_TOKEN_TYPE,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(subject: str) -> str:
    return create_token(
        subject=subject,
        token_type=REFRESH_TOKEN_TYPE,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )


def create_password_reset_token(subject: str) -> str:
    return create_token(
        subject=subject,
        token_type=PASSWORD_RESET_TOKEN_TYPE,
        expires_delta=timedelta(minutes=settings.password_reset_token_expire_minutes),
    )


def create_email_verification_token(subject: str) -> str:
    return create_token(
        subject=subject,
        token_type=EMAIL_VERIFICATION_TOKEN_TYPE,
        expires_delta=timedelta(minutes=settings.email_verification_token_expire_minutes),
    )


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except PyJWTError:
        return None

    token_id = payload.get("jti")
    if token_id in _REVOKED_TOKEN_IDS:
        return None
    if expected_type is not None and payload.get("type") != expected_type:
        return None
    return payload


def decode_access_token(token: str) -> dict[str, Any] | None:
    return decode_token(token, expected_type=ACCESS_TOKEN_TYPE)


def revoke_token(token: str) -> bool:
    payload = decode_token(token)
    if payload is None:
        return False
    token_id = payload.get("jti")
    if token_id is None:
        return False
    _REVOKED_TOKEN_IDS.add(token_id)
    return True
