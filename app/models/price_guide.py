"""Telefon narx ko'rsatkichi: modellar, xotira bo'yicha narxlar, valyuta sozlamasi.

Manba — Koreya diler (buy-back) narxlari, WON'da (`scripts/price_guide_apple.json`).
WON qiymatlari o'zgarmas manba sifatida saqlanadi; so'mga o'girish har so'rovda
`PriceGuideSettings` (kurs + bozor tuzatmasi) bilan bajariladi — admin kursni
o'zgartirsa, barcha narxlar darhol yangilanadi, ma'lumotni qayta yuklash shart emas.

DIQQAT: `*_krw` ustunlari pul emas, MANBA ma'lumot (won, butun son). Foydalanuvchiga
ko'rsatiladigan har qanday narx tiyinga `convert_foreign_to_tiyin` orqali o'giriladi.
"""

from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DeviceModel(Base):
    __tablename__ = "device_models"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    brand: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    # Ro'yxatda guruhlash uchun: "11", "13", "SE", "X".
    series: Mapped[str] = mapped_column(String(20), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Nosozlik ajratmalari (won, musbat — narxdan AYIRILADI). NULL = jadvalda yo'q
    # (ajratilmaydi). lcd_uninspectable — displeyni tekshirib bo'lmaganda.
    screen_broken_krw: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    lcd_krw: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    lcd_uninspectable_krw: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    face_id_krw: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    camera_krw: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    wifi_krw: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    mic_krw: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    back_glass_krw: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    true_tone_krw: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    genuine_parts_krw: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    nongenuine_parts_krw: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # "Faqat ehtiyot qism sifatida" narx — ajratmalardan keyin pastki chegara.
    scrap_krw: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    prices = relationship(
        "DevicePrice",
        back_populates="model",
        cascade="all, delete-orphan",
        order_by="DevicePrice.sort_order",
    )


class DevicePrice(Base):
    """Bitta model + xotira hajmi uchun daraja bo'yicha narxlar (won).

    NULL daraja narxi = bu darajada sotib olinmaydi (jadvaldagi "X") yoki eski
    model uchun darajalanmagan — bunday holda `base_krw` (holatidan qat'i nazar) ishlatiladi.
    `battery_low_*` — batareya me'yordan past bo'lganda shu daraja narxi.
    """

    __tablename__ = "device_prices"
    __table_args__ = (
        UniqueConstraint("model_id", "storage", name="uq_device_prices_model_storage"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    model_id: Mapped[int] = mapped_column(
        ForeignKey("device_models.id", ondelete="CASCADE"), index=True, nullable=False
    )
    storage: Mapped[str] = mapped_column(String(10), nullable=False)  # "128GB", "1TB"
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    grade_a_krw: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    grade_a_minus_krw: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    grade_b_plus_krw: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    grade_b_minus_krw: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    battery_low_a_krw: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    battery_low_b_plus_krw: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    base_krw: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    model = relationship("DeviceModel", back_populates="prices")


class PriceGuideSettings(Base):
    """Bitta qatorli sozlama (id=1): won -> so'm kursi va bozor tuzatmasi.

    rate_tiyin_per_krw — 1 won necha tiyin (8.55 so'm = 855). Butun son: pul
    hisobida float TAQIQ. market_adjust_bps — Koreya diler narxidan O'zbekiston
    bozoriga tuzatma (+1500 = +15%).
    """

    __tablename__ = "price_guide_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    rate_tiyin_per_krw: Mapped[int] = mapped_column(Integer, nullable=False)
    market_adjust_bps: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
