from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status


def parse_expiry(expiry_str: str) -> datetime:
    """
    Parse expiry string (1H, 1D, 1M, 1Y) into datetime.
    
    Args:
        expiry_str: Expiry format (1H, 1D, 1M, 1Y)
        
    Returns:
        Datetime when key expires
        
    Raises:
        HTTPException: If format is invalid
    """
    if not expiry_str or len(expiry_str) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid expiry format. Use: 1H, 1D, 1M, or 1Y"
        )
    
    # Extract number and unit
    try:
        number = int(expiry_str[:-1])
        unit = expiry_str[-1].upper()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid expiry format. Use: 1H, 1D, 1M, or 1Y"
        )
    
    # Calculate expiry based on unit
    now = datetime.now(timezone.utc)
    
    if unit == 'H':
        return now + timedelta(hours=number)
    elif unit == 'D':
        return now + timedelta(days=number)
    elif unit == 'M':
        return now + timedelta(days=number * 30)  # Approximate month
    elif unit == 'Y':
        return now + timedelta(days=number * 365)  # Approximate year
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid expiry unit. Use: H (hour), D (day), M (month), or Y (year)"
        )