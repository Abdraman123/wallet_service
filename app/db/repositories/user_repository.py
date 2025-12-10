from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.user import User


class UserRepository:
    """Repository for User database operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, google_id: str, email: str, name: Optional[str] = None, 
               picture: Optional[str] = None) -> User:
        """Create a new user."""
        user = User(
            google_id=google_id,
            email=email,
            name=name,
            picture=picture
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.db.get(User, user_id)
    
    def get_by_google_id(self, google_id: str) -> Optional[User]:
        """Get user by Google ID."""
        stmt = select(User).where(User.google_id == google_id)
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        stmt = select(User).where(User.email == email)
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()