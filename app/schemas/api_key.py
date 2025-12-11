from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional


class APIKeyCreateRequest(BaseModel):
    """Request model for creating an API key."""
    name: str = Field(..., min_length=1, max_length=255)
    permissions: List[str] = Field(..., min_items=1)
    expiry: str = Field(
        ...,
        pattern="^[0-9]+[HDMY]$",
        description="Expiry format: number followed by H (hours), D (days), M (months), or Y (years). Example: '1D'",
        example="1D",
    )


class APIKeyRolloverRequest(BaseModel):
    """Request model for rolling over an expired API key."""
    expired_key_id: int
    expiry: str = Field(
        ...,
        pattern="^[0-9]+[HDMY]$",
        description="Expiry format: number followed by H (hours), D (days), M (months), or Y (years). Example: '1M'",
        example="1M",
    )


class APIKeyResponse(BaseModel):
    """Response model for API key (includes actual key only on creation)."""
    api_key: Optional[str] = None
    id: int
    name: str
    permissions: List[str]
    expires_at: datetime
    is_active: bool
    last_used_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class APIKeyListItem(BaseModel):
    """Response model for API key in list (without actual key)."""
    id: int
    name: str
    permissions: List[str]
    expires_at: datetime
    is_active: bool
    last_used_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True