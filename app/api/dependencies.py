from datetime import datetime, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.api_key_repository import APIKeyRepository
from app.utils.security import decode_access_token
from app.models.user import User
from app.models.api_key import APIKey

# Security scheme for JWT
security = HTTPBearer(auto_error=False)


def get_current_user_from_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id_str: str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


def get_api_key_auth(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db)
) -> APIKey:
    """Authenticate using API key."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    api_key_repo = APIKeyRepository(db)
    api_key = api_key_repo.get_by_key(x_api_key)
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    if not api_key.is_valid:
        if api_key.is_expired:
            detail = "API key has expired"
        else:
            detail = "API key is inactive"
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )
    
    # Update last used timestamp
    api_key_repo.update_last_used(api_key, datetime.now(timezone.utc))
    
    return api_key


def get_current_user_or_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> tuple[Optional[User], Optional[APIKey]]:
    """
    CRITICAL: Check API key FIRST, then JWT.
    This fixes the Swagger UI issue where JWT was checked first.
    """
    # PRIORITY 1: API Key (if X-API-Key header exists)
    if x_api_key:
        try:
            api_key = get_api_key_auth(x_api_key, db)
            return (None, api_key)
        except HTTPException:
            pass
    
    # PRIORITY 2: JWT Token (if Authorization header exists)
    if credentials:
        try:
            user = get_current_user_from_jwt(credentials, db)
            return (user, None)
        except HTTPException:
            pass
    
    # Neither authentication method worked
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Valid authentication required (JWT token or API key)"
    )