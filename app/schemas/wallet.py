from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from typing import Optional


# ----- Request Schemas -----

class DepositRequest(BaseModel):
    """Request model for wallet deposit."""
    amount: Decimal = Field(..., gt=0, decimal_places=2, description="Amount in Naira")
    
    @property
    def amount_in_kobo(self) -> int:
        """Convert Naira to kobo."""
        return int(self.amount * 100)
    

class TransferRequest(BaseModel):
    """Request model for wallet transfer."""
    wallet_number: str = Field(..., min_length=13, max_length=13)
    amount: Decimal = Field(..., gt=0, decimal_places=2)


# ----- Response Schemas -----

class DepositResponse(BaseModel):
    """Response model for deposit initialization."""
    reference: str
    authorization_url: str

class DepositStatusResponse(BaseModel):
    """Response model for deposit status check."""
    reference: str
    status: str
    amount: float
    paid_at: Optional[datetime]

class BalanceResponse(BaseModel):
    """Response model for wallet balance."""
    balance: Decimal
    wallet_number: str

class TransferResponse(BaseModel):
    """Response model for transfer."""
    status: str
    message: str
    reference: str

class TransactionResponse(BaseModel):
    type: str
    amount: Decimal
    status: str
    reference: str
    created_at: datetime

    class Config:
        from_attributes = True
