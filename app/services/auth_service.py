from typing import Optional
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth

from app.db.repositories.user_repository import UserRepository
from app.db.repositories.wallet_repository import WalletRepository
from app.utils.security import create_access_token, generate_wallet_number
from app.models.user import User
from app.config import settings


# Initialize OAuth
oauth = OAuth()
oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)


class AuthService:
    """Service for Google OAuth authentication."""
    
    def __init__(self, db: Session):
        self.user_repo = UserRepository(db)
        self.wallet_repo = WalletRepository(db)
        self.db = db
    
    def get_or_create_user(
        self,
        google_id: str,
        email: str,
        name: Optional[str] = None,
        picture: Optional[str] = None
    ) -> User:
        """
        Get existing user or create new one from Google data.
        Also creates wallet if user is new.
        """
        # Check if user exists
        user = self.user_repo.get_by_google_id(google_id)
        
        if user:
            return user
        
        # Create new user
        user = self.user_repo.create(
            google_id=google_id,
            email=email,
            name=name,
            picture=picture
        )
        
        # Create wallet for new user
        wallet_number = generate_wallet_number()
        self.wallet_repo.create(user_id=user.id, wallet_number=wallet_number)
        
        return user
    
    def create_jwt_for_user(self, user_id: int) -> str:
        """Create JWT token for user."""
        return create_access_token(data={"sub": str(user_id)})