from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Bazart API"
    environment: str = "local"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/bazart"
    secret_key: str = Field(default="change-me-in-production-secret-key", min_length=32)
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    password_reset_token_expire_minutes: int = 30
    email_verification_token_expire_minutes: int = 60
    soft_close_window_seconds: int = 120
    soft_close_extension_seconds: int = 120
    local_upload_dir: str = "uploads"
    public_upload_url_prefix: str = "/uploads"
    algorithm: str = "HS256"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
