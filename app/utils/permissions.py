from enum import Enum
from typing import List
from fastapi import HTTPException, status


class Permission(str, Enum):
    """Available API key permissions."""
    READ = "read"
    DEPOSIT = "deposit"
    TRANSFER = "transfer"


VALID_PERMISSIONS = {p.value for p in Permission}


def validate_permissions(permissions: List[str]) -> None:
    """
    Validate that all permissions are valid.
    
    Args:
        permissions: List of permission strings
        
    Raises:
        HTTPException: If any permission is invalid
    """
    if not permissions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one permission must be specified"
        )
    
    invalid = set(permissions) - VALID_PERMISSIONS
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid permissions: {', '.join(invalid)}. "
                   f"Valid options: {', '.join(VALID_PERMISSIONS)}"
        )


def check_permission(api_key_permissions: List[str], required_permission: str) -> None:
    """
    Check if API key has required permission.
    
    Args:
        api_key_permissions: Permissions the API key has
        required_permission: Permission needed for action
        
    Raises:
        HTTPException: If permission is missing
    """
    if required_permission not in api_key_permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"API key lacks required permission: {required_permission}"
        )