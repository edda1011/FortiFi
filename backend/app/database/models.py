"""
SQLAlchemy ORM models.

Each model maps to a table. This file currently holds the wallet
snapshot model; other features (claims, history) may add theirs here
as they land.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base


def utcnow() -> datetime:
    """Timezone-aware UTC now, matching the spec's created_at default."""

    return datetime.now(timezone.utc)


class WalletSnapshot(Base):
    """
    A persisted portfolio snapshot captured on a successful wallet
    check. Matches spec section 7 field-for-field.
    """

    __tablename__ = "wallet_snapshots"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    wallet_address: Mapped[str] = mapped_column(
        String,
        index=True,
    )

    network: Mapped[str] = mapped_column(
        String,
        default="base",
    )

    eth_balance: Mapped[float] = mapped_column(Float)

    eth_price: Mapped[float] = mapped_column(Float)

    eth_value: Mapped[float] = mapped_column(Float)

    usdc_balance: Mapped[float] = mapped_column(Float)

    total_value: Mapped[float] = mapped_column(Float)

    eth_exposure_percent: Mapped[float] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )
