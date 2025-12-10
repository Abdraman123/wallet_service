from typing import List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.wallet_service import WalletService
from app.schemas.wallet import (
    DepositRequest,
    DepositResponse,
    DepositStatusResponse,
    BalanceResponse,
    TransferRequest,
    TransferResponse
)
from app.schemas.transaction import TransactionResponse
from app.api.dependencies import get_current_user_or_api_key
from app.models.user import User
from app.models.api_key import APIKey
from app.utils.permissions import check_permission, Permission

router = APIRouter(prefix="/wallet", tags=["Wallet"])


@router.post(
    "/deposit",
    response_model=DepositResponse,
    summary="Initialize wallet deposit via Paystack"
)
def deposit(
    request: DepositRequest,
    auth: tuple[Optional[User], Optional[APIKey]] = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Initialize a deposit transaction.
    
    Returns Paystack payment URL.
    User completes payment on Paystack.
    Webhook credits wallet automatically.
    
    Requires: JWT or API key with 'deposit' permission.
    """
    user, api_key = auth
    
    # Check API key permission if using API key
    if api_key:
        check_permission(api_key.permissions, Permission.DEPOSIT.value)
        user = api_key.user
    
    wallet_service = WalletService(db)
    result = wallet_service.initialize_deposit(
        user_id=user.id,
        user_email=user.email,
        amount=request.amount
    )
    
    return DepositResponse(
        reference=result["reference"],
        authorization_url=result["authorization_url"]
    )


@router.get(
    "/deposit/{reference}/status",
    response_model=DepositStatusResponse,
    summary="Check deposit status (manual - does not credit wallet)"
)
def get_deposit_status(
    reference: str,
    auth: tuple[Optional[User], Optional[APIKey]] = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Check status of a deposit transaction.
    
    This endpoint DOES NOT credit wallets.
    Only webhooks can credit wallets.
    
    Requires: JWT or API key with 'read' permission.
    """
    user, api_key = auth
    
    if api_key:
        check_permission(api_key.permissions, Permission.READ.value)
    
    wallet_service = WalletService(db)
    return wallet_service.get_deposit_status(reference)


@router.get(
    "/balance",
    response_model=BalanceResponse,
    summary="Get wallet balance"
)
def get_balance(
    auth: tuple[Optional[User], Optional[APIKey]] = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Get current wallet balance.
    
    Requires: JWT or API key with 'read' permission.
    """
    user, api_key = auth
    
    if api_key:
        check_permission(api_key.permissions, Permission.READ.value)
        user = api_key.user
    
    wallet_service = WalletService(db)
    wallet = wallet_service.get_wallet_by_user_id(user.id)
    
    return BalanceResponse(
        balance=wallet.balance,
        wallet_number=wallet.wallet_number
    )


@router.post(
    "/transfer",
    response_model=TransferResponse,
    summary="Transfer funds to another wallet"
)
def transfer(
    request: TransferRequest,
    auth: tuple[Optional[User], Optional[APIKey]] = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Transfer funds from your wallet to another user's wallet.
    
    Requires: JWT or API key with 'transfer' permission.
    """
    user, api_key = auth
    
    if api_key:
        check_permission(api_key.permissions, Permission.TRANSFER.value)
        user = api_key.user
    
    wallet_service = WalletService(db)
    sender_wallet = wallet_service.get_wallet_by_user_id(user.id)
    
    transaction = wallet_service.transfer_funds(
        sender_wallet=sender_wallet,
        recipient_wallet_number=request.wallet_number,
        amount=request.amount
    )
    
    return TransferResponse(
        status="success",
        message="Transfer completed",
        reference=transaction.reference
    )


@router.get(
    "/transactions",
    response_model=List[TransactionResponse],
    summary="Get transaction history"
)
def get_transactions(
    auth: tuple[Optional[User], Optional[APIKey]] = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Get wallet transaction history.
    
    Requires: JWT or API key with 'read' permission.
    """
    user, api_key = auth
    
    if api_key:
        check_permission(api_key.permissions, Permission.READ.value)
        user = api_key.user
    
    wallet_service = WalletService(db)
    wallet = wallet_service.get_wallet_by_user_id(user.id)
    transactions = wallet_service.get_transaction_history(wallet.id)
    
    return transactions