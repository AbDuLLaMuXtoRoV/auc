from fastapi import APIRouter, status

from app.core.dependencies import BearerToken, CurrentActiveUser, CurrentUser, DbSession, LoginForm
from app.models.user import User
from app.schemas.auth import (
    AccessToken,
    ForgotPasswordRequest,
    LogoutRequest,
    MessageResponse,
    PasswordResetTokenResponse,
    RefreshTokenRequest,
    ResetPasswordRequest,
    Token,
    UserCreate,
    UserRead,
    VerificationTokenResponse,
    VerifyEmailRequest,
)
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: DbSession) -> User:
    return AuthService(db).register_user(payload)


@router.post("/login", response_model=Token)
def login(form_data: LoginForm, db: DbSession) -> Token:
    return AuthService(db).login_user(form_data.username, form_data.password)


@router.get("/me", response_model=UserRead)
def read_me(current_user: CurrentUser) -> User:
    return current_user


@router.post("/refresh", response_model=AccessToken)
def refresh_token(payload: RefreshTokenRequest, db: DbSession) -> AccessToken:
    return AuthService(db).refresh_access_token(payload.refresh_token)


@router.post("/logout", response_model=MessageResponse)
def logout(payload: LogoutRequest, token: BearerToken, db: DbSession) -> MessageResponse:
    AuthService(db).logout_user(access_token=token, refresh_token=payload.refresh_token)
    return MessageResponse(message="Logged out")


@router.post("/forgot-password", response_model=PasswordResetTokenResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: DbSession,
) -> PasswordResetTokenResponse:
    reset_token = AuthService(db).create_password_reset_token_for_email(payload.email)
    return PasswordResetTokenResponse(
        message="If the email exists, password reset instructions have been generated",
        reset_token=reset_token,
    )


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest, db: DbSession) -> MessageResponse:
    AuthService(db).reset_password(payload.token, payload.new_password)
    return MessageResponse(message="Password has been reset")


@router.post("/verification-token", response_model=VerificationTokenResponse)
def generate_verification_token(
    current_user: CurrentActiveUser,
    db: DbSession,
) -> VerificationTokenResponse:
    token = AuthService(db).create_email_verification_token_for_user(current_user)
    return VerificationTokenResponse(
        message="Email verification token generated",
        verification_token=token,
    )


@router.post("/verify-email", response_model=UserRead)
def verify_email(payload: VerifyEmailRequest, db: DbSession) -> User:
    return AuthService(db).verify_email(payload.token)
