from decimal import Decimal
from typing import Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.repositories.wallet_repository import WalletRepository
from app.db.repositories.transaction_repository import TransactionRepository
from app.models.transaction import TransactionStatus


class WebhookService:
    """Service for processing Paystack webhooks."""
    
    def __init__(self, db: Session):
        self.wallet_repo = WalletRepository(db)
        self.transaction_repo = TransactionRepository(db)
        self.db = db
    
    def process_payment_webhook(self, webhook_data: Dict[str, Any]) -> None:
        """
        Process Paystack webhook for successful payment.
        This is the ONLY place where wallet balance is credited.
        """
        event = webhook_data.get("event")
        
        if event != "charge.success":
            return  # Ignore non-success events
        
        data = webhook_data.get("data", {})
        reference = data.get("reference")
        amount_kobo = data.get("amount")
        paystack_status = data.get("status")
        
        if not reference or not amount_kobo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook data"
            )
        
        # Convert kobo to Naira
        amount = Decimal(amount_kobo) / 100
        
        # Find transaction
        transaction = self.transaction_repo.get_by_paystack_reference(reference)
        
        if not transaction:
            # Silently ignore if transaction not found (idempotency)
            return
        
        # Check if already processed (idempotency)
        if transaction.status == TransactionStatus.SUCCESS:
            return  # Already credited, ignore duplicate webhook
        
        try:
            # Update transaction status
            if paystack_status == "success":
                self.transaction_repo.update_status(transaction, TransactionStatus.SUCCESS)
                
                # Credit wallet (ONLY HERE!)
                wallet = self.wallet_repo.get_by_user_id(transaction.wallet.user_id)
                if wallet:
                    self.wallet_repo.add_to_balance(wallet, amount)
            else:
                self.transaction_repo.update_status(transaction, TransactionStatus.FAILED)
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Webhook processing failed: {str(e)}"
            )