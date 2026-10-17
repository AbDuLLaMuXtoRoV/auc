from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Region(Base):
    """O'zbekiston hududi (viloyat / respublika / shahar).

    E'lon joylashuvini strukturaviy tanlash uchun — matn kiritish o'rniga
    ro'yxatdan tanlash filtr va statistikani aniq qiladi. name_uz/name_ru —
    ikki tilli interfeys uchun. `code` — barqaror mashina identifikatori
    (masalan ISO-ga o'xshash "TAS"), seed va integratsiyalarda ishlatiladi.
    """

    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name_uz: Mapped[str] = mapped_column(String(120), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)

    districts = relationship("District", back_populates="region", cascade="all, delete-orphan")


class District(Base):
    """Hudud ichidagi tuman/shahar. Viloyatga tegishli (region_id)."""

    __tablename__ = "districts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"), index=True, nullable=False)
    name_uz: Mapped[str] = mapped_column(String(120), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(120), nullable=False)

    region = relationship("Region", back_populates="districts")
