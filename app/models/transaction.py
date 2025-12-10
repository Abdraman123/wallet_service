from decimal import Decimal
from sqlalchemy import String, Numeric, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional
import enum

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.wallet import Wallet


class TransactionType(str, enum.Enum):
    """Transaction types."""
    DEPOSIT = "deposit"
    TRANSFER = "transfer"


class TransactionStatus(str, enum.Enum):
    """Transaction statuses."""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class Transaction(Base, TimestampMixin):
    """Transaction model for wallet operations."""
    
    __tablename__ = "transactions"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    reference: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    type: Mapped[TransactionType] = mapped_column(SQLEnum(TransactionType), nullable=False)
    status: Mapped[TransactionStatus] = mapped_column(
        SQLEnum(TransactionStatus),
        default=TransactionStatus.PENDING,
        nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2), nullable=False)
    wallet_id: Mapped[int] = mapped_column(ForeignKey("wallets.id"), nullable=False)
    
    # For transfers: recipient wallet number
    recipient_wallet_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # For deposits: Paystack metadata
    paystack_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Relationship
    wallet: Mapped["Wallet"] = relationship("Wallet", back_populates="transactions")
    
    def __repr__(self) -> str:
        return f"<Transaction(ref={self.reference}, type={self.type}, status={self.status})>"