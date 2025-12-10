from fastapi import APIRouter, Depends, Request, HTTPException, status, Header
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.webhook_service import WebhookService
from app.services.paystack_service import PaystackService

router = APIRouter(prefix="/wallet/paystack", tags=["Webhooks"])


@router.post(
    "/webhook",
    summary="Paystack webhook endpoint",
    status_code=status.HTTP_200_OK
)
async def paystack_webhook(
    request: Request,
    x_paystack_signature: str = Header(..., alias="x-paystack-signature"),
    db: Session = Depends(get_db)
):
    """
    Receive and process Paystack webhooks.
    
    This is the ONLY endpoint that credits wallets after payment.
    Validates Paystack signature for security.
    Idempotent - won't double-credit if webhook is resent.
    """
    # Get raw body for signature verification
    body = await request.body()
    
    # Verify webhook signature
    if not PaystackService.verify_webhook_signature(body, x_paystack_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )
    
    # Parse webhook data
    webhook_data = await request.json()
    
    # Process webhook
    webhook_service = WebhookService(db)
    webhook_service.process_payment_webhook(webhook_data)
    
    return {"status": True}