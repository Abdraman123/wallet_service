import hmac
import hashlib
import requests
from decimal import Decimal
from typing import Dict, Any
from fastapi import HTTPException, status

from app.config import settings


class PaystackService:
    """Service for Paystack API interactions."""
    
    BASE_URL = "https://api.paystack.co"
    
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
    
    def initialize_transaction(self, email: str, amount: Decimal, reference: str) -> Dict[str, Any]:
        """
        Initialize a Paystack transaction.
        
        Args:
            email: User's email
            amount: Amount in Naira (will be converted to kobo)
            reference: Unique transaction reference
            
        Returns:
            Dict with authorization_url and access_code
        """
        # Convert Naira to kobo (Paystack uses kobo)
        amount_kobo = int(amount * 100)
        
        payload = {
            "email": email,
            "amount": amount_kobo,
            "reference": reference,
            "callback_url": f"{settings.API_V1_PREFIX}/wallet/deposit/callback"
        }
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/transaction/initialize",
                json=payload,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("status"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to initialize Paystack transaction"
                )
            
            return data["data"]
            
        except requests.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Paystack service unavailable: {str(e)}"
            )
    
    def verify_transaction(self, reference: str) -> Dict[str, Any]:
        """
        Verify a transaction status with Paystack.
        
        Args:
            reference: Transaction reference
            
        Returns:
            Transaction data from Paystack
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/transaction/verify/{reference}",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("status"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to verify transaction"
                )
            
            return data["data"]
            
        except requests.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Paystack service unavailable: {str(e)}"
            )
    
    @staticmethod
    def verify_webhook_signature(payload: bytes, signature: str) -> bool:
        """
        Verify Paystack webhook signature.
        
        Args:
            payload: Raw request body
            signature: X-Paystack-Signature header value
            
        Returns:
            True if signature is valid
        """
        computed_signature = hmac.new(
            settings.PAYSTACK_WEBHOOK_SECRET.encode('utf-8'),
            payload,
            hashlib.sha512
        ).hexdigest()
        
        return hmac.compare_digest(computed_signature, signature)