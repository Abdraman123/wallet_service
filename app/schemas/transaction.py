from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime
from typing import Optional


class TransactionResponse(BaseModel):
    """Response model for transaction."""
    type: str
    amount: Decimal
    status: str
    reference: str
    recipient_wallet_number: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True