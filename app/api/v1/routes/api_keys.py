from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.api_key_service import APIKeyService
from app.schemas.api_key import (
    APIKeyCreateRequest,
    APIKeyRolloverRequest,
    APIKeyResponse,
    APIKeyListItem
)
from app.schemas.common import MessageResponse
from app.api.dependencies import get_current_user_from_jwt
from app.models.user import User

router = APIRouter(prefix="/keys", tags=["API Keys"])


@router.post(
    "/create",
    response_model=APIKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key"
)
def create_api_key(
    request: APIKeyCreateRequest,
    current_user: User = Depends(get_current_user_from_jwt),
    db: Session = Depends(get_db)
):
    """
    Create a new API key with specific permissions.
    
    - **name**: Descriptive name
    - **permissions**: List of permissions (read, deposit, transfer)
    - **expiry**: Format: 1H, 1D, 1M, 1Y
    
    Maximum 5 active keys per user.
    Key is shown only once!
    """
    api_key_service = APIKeyService(db)
    api_key = api_key_service.create_api_key(
        name=request.name,
        user_id=current_user.id,
        permissions=request.permissions,
        expiry=request.expiry
    )
    
    # Return key with actual key string (only time it's shown)
    response = APIKeyResponse.model_validate(api_key)
    response.api_key = api_key.key
    return response


@router.post(
    "/rollover",
    response_model=APIKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Rollover an expired API key"
)
def rollover_api_key(
    request: APIKeyRolloverRequest,
    current_user: User = Depends(get_current_user_from_jwt),
    db: Session = Depends(get_db)
):
    """
    Create new API key using permissions from an expired key.
    
    - **expired_key_id**: ID of the expired key
    - **expiry**: New expiry format (1H, 1D, 1M, 1Y)
    
    Old key must be truly expired.
    """
    api_key_service = APIKeyService(db)
    api_key = api_key_service.rollover_api_key(
        expired_key_id=request.expired_key_id,
        user_id=current_user.id,
        expiry=request.expiry
    )
    
    # Return with actual key string
    response = APIKeyResponse.model_validate(api_key)
    response.api_key = api_key.key
    return response


@router.get(
    "",
    response_model=List[APIKeyListItem],
    summary="List all your API keys"
)
def list_api_keys(
    current_user: User = Depends(get_current_user_from_jwt),
    db: Session = Depends(get_db)
):
    """Get list of all API keys (actual key strings not included)."""
    api_key_service = APIKeyService(db)
    api_keys = api_key_service.get_user_api_keys(current_user.id)
    return api_keys


@router.delete(
    "/{key_id}",
    response_model=MessageResponse,
    summary="Revoke an API key"
)
def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user_from_jwt),
    db: Session = Depends(get_db)
):
    """Revoke (deactivate) an API key."""
    api_key_service = APIKeyService(db)
    api_key_service.revoke_api_key(key_id=key_id, user_id=current_user.id)
    return MessageResponse(message="API key revoked successfully")