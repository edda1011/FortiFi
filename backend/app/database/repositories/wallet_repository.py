"""
Repository for persisting and reading wallet snapshots.

This layer owns all SQL. It never makes RPC calls and never calls the
AI — it is a pure data-access layer. Services call it with a session
and a computed snapshot, and it returns ORM models.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import WalletSnapshot
from app.schemas.wallet import WalletCheckResponse


class WalletRepository:
    """
    Persists computed wallet snapshots and reads them back.

    One class = one responsibility: this class only knows how to
    store and retrieve `WalletSnapshot` rows. It does not know how
    balances are read from Base.
    """

    def __init__(
        self,
        db: Session,
    ) -> None:
        self.db = db

    def save_snapshot(
        self,
        snapshot: WalletCheckResponse,
    ) -> WalletSnapshot:
        """
        Persist a computed snapshot. Pure data write, no RPC calls
        here. Commits the row and returns the ORM model.
        """

        row = WalletSnapshot(
            wallet_address=snapshot.address,
            network=snapshot.network,
            eth_balance=snapshot.eth_balance,
            eth_price=snapshot.eth_price,
            eth_value=snapshot.eth_value,
            usdc_balance=snapshot.usdc_balance,
            total_value=snapshot.total_value,
            eth_exposure_percent=snapshot.eth_exposure_percent,
        )

        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)

        return row

    def get_latest(
        self,
        address: str,
    ) -> Optional[WalletSnapshot]:
        """
        Return the most recent saved snapshot for an address, or None
        if none exists yet.
        """

        statement = (
            select(WalletSnapshot)
            .where(WalletSnapshot.wallet_address == address)
            .order_by(WalletSnapshot.created_at.desc())
            .limit(1)
        )

        return self.db.scalars(statement).first()

    def list_by_address(
        self,
        address: str,
        limit: int = 20,
    ) -> list[WalletSnapshot]:
        """
        Return past snapshots for an address, most recent first.
        """

        statement = (
            select(WalletSnapshot)
            .where(WalletSnapshot.wallet_address == address)
            .order_by(WalletSnapshot.created_at.desc())
            .limit(limit)
        )

        return list(self.db.scalars(statement).all())
