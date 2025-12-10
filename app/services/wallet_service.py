import secrets
from decimal import Decimal
from typing import List, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.repositories.wallet_repository import WalletRepository
from app.db.repositories.transaction_repository import TransactionRepository
from app.services.paystack_service import PaystackService
from app.models.wallet import Wallet
from app.models.transaction import Transaction, TransactionType, TransactionStatus


class WalletService:
    """Service for wallet operations."""
    
    def __init__(self, db: Session):
        self.wallet_repo = WalletRepository(db)
        self.transaction_repo = TransactionRepository(db)
        self.paystack_service = PaystackService()
        self.db = db
    
    def get_wallet_by_user_id(self, user_id: int) -> Wallet:
        """Get user's wallet."""
        wallet = self.wallet_repo.get_by_user_id(user_id)
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found"
            )
        return wallet
    
    def initialize_deposit(
        self,
        user_id: int,
        user_email: str,
        amount: Decimal
    ) -> Dict[str, Any]:
        """Initialize a Paystack deposit transaction."""
        wallet = self.get_wallet_by_user_id(user_id)
        
        # Generate unique reference
        reference = f"DEP_{secrets.token_hex(8).upper()}"
        
        # Create pending transaction
        transaction = self.transaction_repo.create(
            reference=reference,
            type=TransactionType.DEPOSIT,
            amount=amount,
            wallet_id=wallet.id,
            status=TransactionStatus.PENDING,
            paystack_reference=reference
        )
        
        # Initialize Paystack transaction
        paystack_data = self.paystack_service.initialize_transaction(
            email=user_email,
            amount=amount,
            reference=reference
        )
        
        return {
            "reference": reference,
            "authorization_url": paystack_data["authorization_url"],
            "access_code": paystack_data["access_code"]
        }
    
    def get_deposit_status(self, reference: str) -> Dict[str, Any]:
        """Get deposit transaction status (manual check - does not credit wallet)."""
        transaction = self.transaction_repo.get_by_reference(reference)
        
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found"
            )
        
        if transaction.type != TransactionType.DEPOSIT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not a deposit transaction"
            )
        
        return {
            "reference": transaction.reference,
            "status": transaction.status.value,
            "amount": float(transaction.amount),
            "currency": "NGN",  # Add this
            "paid_at": transaction.updated_at.isoformat() if transaction.status == TransactionStatus.SUCCESS else None
        }
    
    def transfer_funds(
        self,
        sender_wallet: Wallet,
        recipient_wallet_number: str,
        amount: Decimal
    ) -> Transaction:
        """Transfer funds between wallets."""
        # Validate amount
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Amount must be greater than zero"
            )
        
        # Check sender balance
        if sender_wallet.balance < amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient balance"
            )
        
        # Get recipient wallet
        recipient_wallet = self.wallet_repo.get_by_wallet_number(recipient_wallet_number)
        if not recipient_wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recipient wallet not found"
            )
        
        # Cannot transfer to self
        if sender_wallet.id == recipient_wallet.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot transfer to your own wallet"
            )
        
        # Generate reference
        reference = f"TRF_{secrets.token_hex(8).upper()}"
        
        try:
            # Deduct from sender
            self.wallet_repo.deduct_from_balance(sender_wallet, amount)
            
            # Add to recipient
            self.wallet_repo.add_to_balance(recipient_wallet, amount)
            
            # Record transaction for sender
            transaction = self.transaction_repo.create(
                reference=reference,
                type=TransactionType.TRANSFER,
                amount=amount,
                wallet_id=sender_wallet.id,
                status=TransactionStatus.SUCCESS,
                recipient_wallet_number=recipient_wallet_number
            )
            
            # Record transaction for recipient (incoming transfer)
            self.transaction_repo.create(
                reference=f"{reference}_IN",
                type=TransactionType.TRANSFER,
                amount=amount,
                wallet_id=recipient_wallet.id,
                status=TransactionStatus.SUCCESS,
                recipient_wallet_number=sender_wallet.wallet_number
            )
            
            return transaction
            
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Transfer failed: {str(e)}"
            )
    
    def get_transaction_history(self, wallet_id: int) -> List[Transaction]:
        """Get wallet transaction history."""
        return self.transaction_repo.get_by_wallet_id(wallet_id)