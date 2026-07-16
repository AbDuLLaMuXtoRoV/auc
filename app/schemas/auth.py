from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.user import UserCreate, UserRead


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class MessageResponse(BaseModel):
    message: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class PasswordResetTokenResponse(MessageResponse):
    reset_token: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not any(character.isalpha() for character in value):
            raise ValueError("Password must contain at least one letter")
        if not any(character.isdigit() for character in value):
            raise ValueError("Password must contain at least one number")
        return value


class VerificationTokenResponse(MessageResponse):
    verification_token: str


class VerifyEmailRequest(BaseModel):
    token: str


__all__ = [
    "AccessToken",
    "ForgotPasswordRequest",
    "LogoutRequest",
    "MessageResponse",
    "PasswordResetTokenResponse",
    "RefreshTokenRequest",
    "ResetPasswordRequest",
    "Token",
    "UserCreate",
    "UserRead",
    "VerificationTokenResponse",
    "VerifyEmailRequest",
]
