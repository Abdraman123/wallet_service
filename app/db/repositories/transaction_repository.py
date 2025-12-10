from decimal import Decimal
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.transaction import Transaction, TransactionType, TransactionStatus


class TransactionRepository:
    """Repository for Transaction database operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(
        self,
        reference: str,
        type: TransactionType,
        amount: Decimal,
        wallet_id: int,
        status: TransactionStatus = TransactionStatus.PENDING,
        recipient_wallet_number: Optional[str] = None,
        paystack_reference: Optional[str] = None
    ) -> Transaction:
        """Create a new transaction."""
        transaction = Transaction(
            reference=reference,
            type=type,
            amount=amount,
            wallet_id=wallet_id,
            status=status,
            recipient_wallet_number=recipient_wallet_number,
            paystack_reference=paystack_reference
        )
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        return transaction
    
    def get_by_reference(self, reference: str) -> Optional[Transaction]:
        """Get transaction by reference."""
        stmt = select(Transaction).where(Transaction.reference == reference)
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    def get_by_paystack_reference(self, paystack_ref: str) -> Optional[Transaction]:
        """Get transaction by Paystack reference."""
        stmt = select(Transaction).where(Transaction.paystack_reference == paystack_ref)
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    def get_by_wallet_id(self, wallet_id: int) -> List[Transaction]:
        """Get all transactions for a wallet."""
        stmt = select(Transaction).where(
            Transaction.wallet_id == wallet_id
        ).order_by(Transaction.created_at.desc())
        result = self.db.execute(stmt)
        return list(result.scalars().all())
    
    def update_status(self, transaction: Transaction, status: TransactionStatus) -> Transaction:
        """Update transaction status."""
        transaction.status = status
        self.db.commit()
        self.db.refresh(transaction)
        return transaction