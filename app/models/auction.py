from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import AuctionStatus


class Auction(Base):
    __tablename__ = "auctions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), unique=True, nullable=False)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    status: Mapped[AuctionStatus] = mapped_column(
        SqlEnum(AuctionStatus, name="auction_status"),
        default=AuctionStatus.SCHEDULED,
        index=True,
        nullable=False,
    )
    starting_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    current_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    minimum_bid_increment: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=1, nullable=False
    )
    reserve_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    highest_bidder_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=True
    )
    winner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    winning_bid_id: Mapped[int | None] = mapped_column(
        ForeignKey("bids.id", name="fk_auctions_winning_bid_id_bids", use_alter=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    item = relationship("Item", back_populates="auction")
    seller = relationship("User", foreign_keys=[seller_id], back_populates="auctions")
    highest_bidder = relationship("User", foreign_keys=[highest_bidder_id])
    winner = relationship("User", foreign_keys=[winner_id], back_populates="won_auctions")
    bids = relationship(
        "Bid",
        back_populates="auction",
        cascade="all, delete-orphan",
        foreign_keys="Bid.auction_id",
    )
    winning_bid = relationship("Bid", foreign_keys=[winning_bid_id], post_update=True)
    order = relationship("Order", back_populates="auction", uselist=False)
