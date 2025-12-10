from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.wallet import Wallet


class WalletRepository:
    """Repository for Wallet database operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, user_id: int, wallet_number: str) -> Wallet:
        """Create a new wallet."""
        wallet = Wallet(
            user_id=user_id,
            wallet_number=wallet_number,
            balance=Decimal("0.00")
        )
        self.db.add(wallet)
        self.db.commit()
        self.db.refresh(wallet)
        return wallet
    
    def get_by_user_id(self, user_id: int) -> Optional[Wallet]:
        """Get wallet by user ID."""
        stmt = select(Wallet).where(Wallet.user_id == user_id)
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    def get_by_wallet_number(self, wallet_number: str) -> Optional[Wallet]:
        """Get wallet by wallet number."""
        stmt = select(Wallet).where(Wallet.wallet_number == wallet_number)
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    def update_balance(self, wallet: Wallet, new_balance: Decimal) -> Wallet:
        """Update wallet balance."""
        wallet.balance = new_balance
        self.db.commit()
        self.db.refresh(wallet)
        return wallet
    
    def add_to_balance(self, wallet: Wallet, amount: Decimal) -> Wallet:
        """Add amount to wallet balance."""
        wallet.balance += amount
        self.db.commit()
        self.db.refresh(wallet)
        return wallet
    
    def deduct_from_balance(self, wallet: Wallet, amount: Decimal) -> Wallet:
        """Deduct amount from wallet balance."""
        wallet.balance -= amount
        self.db.commit()
        self.db.refresh(wallet)
        return wallet