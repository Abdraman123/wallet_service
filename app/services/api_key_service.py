from datetime import datetime, timezone
from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.repositories.api_key_repository import APIKeyRepository
from app.utils.security import generate_api_key
from app.utils.expiry_parser import parse_expiry
from app.utils.permissions import validate_permissions
from app.models.api_key import APIKey


class APIKeyService:
    """Service for API key operations."""
    
    MAX_ACTIVE_KEYS = 5
    
    def __init__(self, db: Session):
        self.api_key_repo = APIKeyRepository(db)
    
    def create_api_key(
        self,
        name: str,
        user_id: int,
        permissions: List[str],
        expiry: str
    ) -> APIKey:
        """Create a new API key with permissions and expiry."""
        # Validate permissions
        validate_permissions(permissions)
        
        # Parse expiry to datetime
        expires_at = parse_expiry(expiry)
        
        # Check active key limit
        now = datetime.now(timezone.utc)
        active_count = self.api_key_repo.count_active_keys(user_id, now)
        
        if active_count >= self.MAX_ACTIVE_KEYS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum {self.MAX_ACTIVE_KEYS} active API keys allowed per user"
            )
        
        # Generate unique API key
        key = generate_api_key()
        
        # Create API key in database
        api_key = self.api_key_repo.create(
            key=key,
            name=name,
            user_id=user_id,
            permissions=permissions,
            expires_at=expires_at
        )
        
        return api_key
    
    def rollover_api_key(
        self,
        expired_key_id: int,
        user_id: int,
        expiry: str
    ) -> APIKey:
        """Create new API key using permissions from expired key."""
        # Get the expired key
        old_key = self.api_key_repo.get_by_id(expired_key_id)
        
        if not old_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        # Verify ownership
        if old_key.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to rollover this API key"
            )
        
        # Verify key is actually expired
        if not old_key.is_expired:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot rollover a key that has not expired"
            )
        
        # Create new key with same permissions
        return self.create_api_key(
            name=f"{old_key.name} (rolled over)",
            user_id=user_id,
            permissions=old_key.permissions,
            expiry=expiry
        )
    
    def get_user_api_keys(self, user_id: int) -> List[APIKey]:
        """Get all API keys for a user."""
        return self.api_key_repo.get_all_by_user(user_id)
    
    def revoke_api_key(self, key_id: int, user_id: int) -> APIKey:
        """Revoke an API key."""
        api_key = self.api_key_repo.get_by_id(key_id)
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        if api_key.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to revoke this API key"
            )
        
        return self.api_key_repo.revoke(api_key)