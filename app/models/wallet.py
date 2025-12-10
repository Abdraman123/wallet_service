from decimal import Decimal
from sqlalchemy import String, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, List

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.transaction import Transaction


class Wallet(Base, TimestampMixin):
    """Wallet model for user balances."""
    
    __tablename__ = "wallets"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    wallet_number: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=False
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        default=Decimal("0.00"),
        nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        unique=True,
        nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="wallet")
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction",
        back_populates="wallet",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Wallet(wallet_number={self.wallet_number}, balance={self.balance})>"