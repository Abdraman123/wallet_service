from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.models.api_key import APIKey


class APIKeyRepository:
    """Repository for APIKey database operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(
        self,
        key: str,
        name: str,
        user_id: int,
        permissions: List[str],
        expires_at: datetime
    ) -> APIKey:
        """Create a new API key."""
        api_key = APIKey(
            key=key,
            name=name,
            user_id=user_id,
            permissions=permissions,
            expires_at=expires_at
        )
        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)
        return api_key
    
    def get_by_id(self, key_id: int) -> Optional[APIKey]:
        """Get API key by ID."""
        return self.db.get(APIKey, key_id)
    
    def get_by_key(self, key: str) -> Optional[APIKey]:
        """Get API key by key string."""
        stmt = select(APIKey).where(APIKey.key == key)
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    def get_all_by_user(self, user_id: int) -> List[APIKey]:
        """Get all API keys for a user."""
        stmt = select(APIKey).where(
            APIKey.user_id == user_id
        ).order_by(APIKey.created_at.desc())
        result = self.db.execute(stmt)
        return list(result.scalars().all())
    
    def count_active_keys(self, user_id: int, now: datetime) -> int:
        """Count active (non-expired, non-revoked) keys for a user."""
        stmt = select(APIKey).where(
            and_(
                APIKey.user_id == user_id,
                APIKey.is_active == True,
                APIKey.expires_at > now
            )
        )
        result = self.db.execute(stmt)
        return len(list(result.scalars().all()))
    
    def update_last_used(self, api_key: APIKey, timestamp: datetime) -> APIKey:
        """Update the last_used_at timestamp."""
        api_key.last_used_at = timestamp
        self.db.commit()
        self.db.refresh(api_key)
        return api_key
    
    def revoke(self, api_key: APIKey) -> APIKey:
        """Revoke (deactivate) an API key."""
        api_key.is_active = False
        self.db.commit()
        self.db.refresh(api_key)
        return api_key