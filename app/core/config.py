from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Kod ichida yozilgan zaif defaultlar. Prod/staging'da bu qiymatlar bilan
# ishga tushish TAQIQ (JWT qalbakilashtirish / soxta webhook imzo xatari).
INSECURE_DEFAULT_SECRET_KEY = "change-me-in-production-secret-key"
INSECURE_DEFAULT_WEBHOOK_SECRET = "change-me-webhook-secret"

Environment = Literal["local", "test", "staging", "production"]

# Mock to'lov provayderi va mock tasdiqlash faqat shu muhitlarda ruxsat etiladi.
# Prod'da mock = tovarni bepul olish imkoni.
_MOCK_SAFE_ENVIRONMENTS: frozenset[str] = frozenset({"local", "test"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Bazart API"
    environment: Environment = "local"
    # 5433 — docker compose'dagi Postgres host porti (5432 mahalliy
    # o'rnatilgan Postgres tomonidan band bo'lishi mumkin).
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5433/bazart"
    secret_key: str = Field(default=INSECURE_DEFAULT_SECRET_KEY, min_length=32)
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    password_reset_token_expire_minutes: int = 30
    email_verification_token_expire_minutes: int = 60
    soft_close_window_seconds: int = 120
    soft_close_extension_seconds: int = 120
    # Anti-sniping cheksiz cho'zilmasin: bir auksion ko'pi bilan shuncha marta
    # uzaytiriladi. Undan keyin oxirgi soniyadagi bid muddatni surmaydi.
    max_soft_close_extensions: int = 10
    local_upload_dir: str = "uploads"
    public_upload_url_prefix: str = "/uploads"
    algorithm: str = "HS256"

    # Auksionni avtomatik yopuvchi fon vazifasi.
    # Default False: testlarda fon vazifasi ishga tushib test bazasini
    # o'zgartirmasligi kerak. Local/prod'da .env orqali yoqiladi.
    auction_closer_enabled: bool = False
    auction_closer_interval_seconds: int = 5

    # Rate limiting (bid/login brute-force himoyasi).
    rate_limit_enabled: bool = True
    rate_limit_login_per_minute: int = 5
    rate_limit_bid_per_minute: int = 10

    # Escrow / to'lov (Faza D).
    buyer_premium_bps: int = 800  # 8% (basis points)
    auto_complete_hours: int = 72  # xaridor sukut saqlasa order shu vaqtda yakunlanadi
    # PSP webhook imzo maxfiy kaliti. Prod'da .env orqali beriladi.
    psp_webhook_secret: str = INSECURE_DEFAULT_WEBHOOK_SECRET
    # Auto-complete fon vazifasi (auction_closer kabi, testda o'chiq).
    auto_complete_enabled: bool = False
    auto_complete_interval_seconds: int = 300

    @property
    def is_production(self) -> bool:
        """Prod yoki staging — ya'ni real pul va real foydalanuvchilar muhiti."""
        return self.environment in {"staging", "production"}

    @property
    def allow_mock_payments(self) -> bool:
        """Mock to'lov oqimiga ruxsat berilganmi.

        Faqat local/test. Prod'da mock provayder doim PAID qaytargani uchun
        bu bayroq yoqilsa istalgan xaridor tovarni to'lovsiz oladi.
        """
        return self.environment in _MOCK_SAFE_ENVIRONMENTS

    @model_validator(mode="after")
    def _forbid_insecure_secret_in_production(self) -> "Settings":
        """Prod/staging'da default SECRET_KEY bilan ishga tushishni bloklaydi.

        Default secret bilan ishlasa istalgan odam istalgan foydalanuvchi
        nomidan JWT qalbakilashtira oladi. Shuning uchun bu xato ogohlantirish
        emas — ilova umuman ko'tarilmaydi.
        """
        if self.is_production and self.secret_key == INSECURE_DEFAULT_SECRET_KEY:
            raise ValueError(
                f"SECRET_KEY '{self.environment}' muhitida default qiymatda qolgan. "
                'Kuchli tasodifiy qiymat bering: python -c "import secrets; '
                'print(secrets.token_urlsafe(48))"'
            )
        if self.is_production and self.psp_webhook_secret == INSECURE_DEFAULT_WEBHOOK_SECRET:
            raise ValueError(
                f"PSP_WEBHOOK_SECRET '{self.environment}' muhitida default qiymatda qolgan. "
                "Soxta webhook imzosi bilan tovar bepul ketishi mumkin — kuchli kalit bering."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
