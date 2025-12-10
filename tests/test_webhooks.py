import pytest
import json
import hmac
import hashlib
from decimal import Decimal
from unittest.mock import patch


class TestPaystackWebhook:
    """Test Paystack webhook processing."""
    
    def create_webhook_signature(self, payload: str, secret: str) -> str:
        """Helper to create valid webhook signature."""
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
    
    @patch('app.config.settings.PAYSTACK_WEBHOOK_SECRET', 'test_secret')
    def test_webhook_success(self, client, db_session, test_user):
        """Test successful webhook processing."""
        from app.models.transaction import Transaction, TransactionType, TransactionStatus
        
        # Create pending transaction
        transaction = Transaction(
            reference="test_ref_123",
            type=TransactionType.DEPOSIT,
            amount=Decimal("5000.00"),
            wallet_id=test_user.wallet.id,
            status=TransactionStatus.PENDING,
            paystack_reference="test_ref_123"
        )
        db_session.add(transaction)
        db_session.commit()
        
        # Webhook payload
        webhook_data = {
            "event": "charge.success",
            "data": {
                "reference": "test_ref_123",
                "amount": 500000,  # 5000 Naira in kobo
                "status": "success"
            }
        }
        
        payload = json.dumps(webhook_data)
        signature = self.create_webhook_signature(payload, 'test_secret')
        
        # Send webhook
        response = client.post(
            "/api/v1/wallet/paystack/webhook",
            data=payload,
            headers={
                "x-paystack-signature": signature,
                "Content-Type": "application/json"
            }
        )
        
        assert response.status_code == 200
        assert response.json()["status"] is True
        
        # Verify wallet was credited
        db_session.refresh(test_user.wallet)
        assert test_user.wallet.balance == Decimal("15000.00")  # 10000 + 5000
        
        # Verify transaction status updated
        db_session.refresh(transaction)
        assert transaction.status == TransactionStatus.SUCCESS
    
    @patch('app.config.settings.PAYSTACK_WEBHOOK_SECRET', 'test_secret')
    def test_webhook_idempotency(self, client, db_session, test_user):
        """Test webhook is idempotent (no double-credit)."""
        from app.models.transaction import Transaction, TransactionType, TransactionStatus
        
        # Create already successful transaction
        transaction = Transaction(
            reference="test_ref_456",
            type=TransactionType.DEPOSIT,
            amount=Decimal("3000.00"),
            wallet_id=test_user.wallet.id,
            status=TransactionStatus.SUCCESS,  # Already success
            paystack_reference="test_ref_456"
        )
        db_session.add(transaction)
        db_session.commit()
        
        initial_balance = test_user.wallet.balance
        
        # Webhook payload (duplicate)
        webhook_data = {
            "event": "charge.success",
            "data": {
                "reference": "test_ref_456",
                "amount": 300000,
                "status": "success"
            }
        }
        
        payload = json.dumps(webhook_data)
        signature = self.create_webhook_signature(payload, 'test_secret')
        
        # Send webhook
        response = client.post(
            "/api/v1/wallet/paystack/webhook",
            data=payload,
            headers={
                "x-paystack-signature": signature,
                "Content-Type": "application/json"
            }
        )
        
        assert response.status_code == 200
        
        # Verify balance NOT changed (idempotent)
        db_session.refresh(test_user.wallet)
        assert test_user.wallet.balance == initial_balance
    
    @patch('app.config.settings.PAYSTACK_WEBHOOK_SECRET', 'test_secret')
    def test_webhook_invalid_signature(self, client):
        """Test webhook with invalid signature is rejected."""
        webhook_data = {
            "event": "charge.success",
            "data": {
                "reference": "test_ref_789",
                "amount": 500000,
                "status": "success"
            }
        }
        
        payload = json.dumps(webhook_data)
        invalid_signature = "invalid_signature_here"
        
        response = client.post(
            "/api/v1/wallet/paystack/webhook",
            data=payload,
            headers={
                "x-paystack-signature": invalid_signature,
                "Content-Type": "application/json"
            }
        )
        
        assert response.status_code == 401
        assert "Invalid webhook signature" in response.json()["detail"]
    
    @patch('app.config.settings.PAYSTACK_WEBHOOK_SECRET', 'test_secret')
    def test_webhook_nonexistent_transaction(self, client):
        """Test webhook for non-existent transaction is ignored."""
        webhook_data = {
            "event": "charge.success",
            "data": {
                "reference": "nonexistent_ref",
                "amount": 500000,
                "status": "success"
            }
        }
        
        payload = json.dumps(webhook_data)
        signature = self.create_webhook_signature(payload, 'test_secret')
        
        response = client.post(
            "/api/v1/wallet/paystack/webhook",
            data=payload,
            headers={
                "x-paystack-signature": signature,
                "Content-Type": "application/json"
            }
        )
        
        # Should succeed but do nothing
        assert response.status_code == 200
    
    @patch('app.config.settings.PAYSTACK_WEBHOOK_SECRET', 'test_secret')
    def test_webhook_failed_payment(self, client, db_session, test_user):
        """Test webhook for failed payment."""
        from app.models.transaction import Transaction, TransactionType, TransactionStatus
        
        # Create pending transaction
        transaction = Transaction(
            reference="test_ref_fail",
            type=TransactionType.DEPOSIT,
            amount=Decimal("2000.00"),
            wallet_id=test_user.wallet.id,
            status=TransactionStatus.PENDING,
            paystack_reference="test_ref_fail"
        )
        db_session.add(transaction)
        db_session.commit()
        
        initial_balance = test_user.wallet.balance
        
        # Webhook payload for failed payment
        webhook_data = {
            "event": "charge.success",
            "data": {
                "reference": "test_ref_fail",
                "amount": 200000,
                "status": "failed"
            }
        }
        
        payload = json.dumps(webhook_data)
        signature = self.create_webhook_signature(payload, 'test_secret')
        
        response = client.post(
            "/api/v1/wallet/paystack/webhook",
            data=payload,
            headers={
                "x-paystack-signature": signature,
                "Content-Type": "application/json"
            }
        )
        
        assert response.status_code == 200
        
        # Verify wallet NOT credited
        db_session.refresh(test_user.wallet)
        assert test_user.wallet.balance == initial_balance
        
        # Verify transaction marked as failed
        db_session.refresh(transaction)
        assert transaction.status == TransactionStatus.FAILED