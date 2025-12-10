import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock


class TestWalletBalance:
    """Test wallet balance retrieval."""
    
    def test_get_balance_with_jwt(self, client, test_user_token, test_user):
        """Test getting balance with JWT token."""
        response = client.get(
            "/api/v1/wallet/balance",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "balance" in data
        assert "wallet_number" in data
        assert Decimal(data["balance"]) == Decimal("10000.00")
    
    def test_get_balance_with_api_key(self, client, test_api_key):
        """Test getting balance with API key."""
        response = client.get(
            "/api/v1/wallet/balance",
            headers={"X-API-Key": test_api_key.key}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "balance" in data
    
    def test_get_balance_without_auth(self, client):
        """Test getting balance without authentication."""
        response = client.get("/api/v1/wallet/balance")
        
        assert response.status_code == 401


class TestWalletDeposit:
    """Test wallet deposit initialization."""
    
    @patch('app.services.paystack_service.requests.post')
    def test_initialize_deposit_with_jwt(self, mock_post, client, test_user_token):
        """Test deposit initialization with JWT."""
        # Mock Paystack response
        mock_post.return_value.json.return_value = {
            "status": True,
            "data": {
                "authorization_url": "https://checkout.paystack.com/test",
                "access_code": "test_access_code",
                "reference": "test_ref"
            }
        }
        mock_post.return_value.raise_for_status = MagicMock()
        
        response = client.post(
            "/api/v1/wallet/deposit",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={"amount": 5000}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "reference" in data
        assert "authorization_url" in data
    
    @patch('app.services.paystack_service.requests.post')
    def test_initialize_deposit_with_api_key(self, mock_post, client, test_api_key):
        """Test deposit initialization with API key."""
        mock_post.return_value.json.return_value = {
            "status": True,
            "data": {
                "authorization_url": "https://checkout.paystack.com/test",
                "access_code": "test_access_code",
                "reference": "test_ref"
            }
        }
        mock_post.return_value.raise_for_status = MagicMock()
        
        response = client.post(
            "/api/v1/wallet/deposit",
            headers={"X-API-Key": test_api_key.key},
            json={"amount": 5000}
        )
        
        assert response.status_code == 200
    
    def test_deposit_with_api_key_without_permission(self, client, db_session, test_user):
        """Test deposit with API key lacking deposit permission."""
        from app.models.api_key import APIKey
        from app.utils.security import generate_api_key
        from datetime import datetime, timedelta, timezone
        
        # Create key with only read permission
        read_only_key = APIKey(
            key=generate_api_key(),
            name="Read Only",
            user_id=test_user.id,
            permissions=["read"],  # No deposit permission
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            is_active=True
        )
        db_session.add(read_only_key)
        db_session.commit()
        
        response = client.post(
            "/api/v1/wallet/deposit",
            headers={"X-API-Key": read_only_key.key},
            json={"amount": 5000}
        )
        
        assert response.status_code == 403
        assert "lacks required permission" in response.json()["detail"]


class TestWalletTransfer:
    """Test wallet transfers."""
    
    def test_transfer_success(self, client, test_user_token, db_session, test_user):
        """Test successful transfer between wallets."""
        from app.models.user import User
        from app.models.wallet import Wallet
        from app.utils.security import generate_wallet_number
        
        # Create recipient user and wallet
        recipient = User(
            google_id="recipient_google_id",
            email="recipient@example.com",
            name="Recipient",
            is_active=True
        )
        db_session.add(recipient)
        db_session.commit()
        
        recipient_wallet = Wallet(
            user_id=recipient.id,
            wallet_number=generate_wallet_number(),
            balance=Decimal("0.00")
        )
        db_session.add(recipient_wallet)
        db_session.commit()
        
        # Transfer
        response = client.post(
            "/api/v1/wallet/transfer",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "wallet_number": recipient_wallet.wallet_number,
                "amount": 1000
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "reference" in data
    
    def test_transfer_insufficient_balance(self, client, test_user_token, db_session, test_user):
        """Test transfer with insufficient balance."""
        from app.models.user import User
        from app.models.wallet import Wallet
        from app.utils.security import generate_wallet_number
        
        # Create recipient
        recipient = User(
            google_id="recipient2_google_id",
            email="recipient2@example.com",
            is_active=True
        )
        db_session.add(recipient)
        db_session.commit()
        
        recipient_wallet = Wallet(
            user_id=recipient.id,
            wallet_number=generate_wallet_number(),
            balance=Decimal("0.00")
        )
        db_session.add(recipient_wallet)
        db_session.commit()
        
        # Try to transfer more than balance
        response = client.post(
            "/api/v1/wallet/transfer",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "wallet_number": recipient_wallet.wallet_number,
                "amount": 50000  # More than 10000 balance
            }
        )
        
        assert response.status_code == 400
        assert "Insufficient balance" in response.json()["detail"]
    
    def test_transfer_to_nonexistent_wallet(self, client, test_user_token):
        """Test transfer to non-existent wallet."""
        response = client.post(
            "/api/v1/wallet/transfer",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "wallet_number": "9999999999999",
                "amount": 1000
            }
        )
        
        assert response.status_code == 404
        assert "Recipient wallet not found" in response.json()["detail"]
    
    def test_transfer_without_permission(self, client, db_session, test_user):
        """Test transfer with API key lacking transfer permission."""
        from app.models.api_key import APIKey
        from app.utils.security import generate_api_key
        from datetime import datetime, timedelta, timezone
        
        # Create key without transfer permission
        no_transfer_key = APIKey(
            key=generate_api_key(),
            name="No Transfer",
            user_id=test_user.id,
            permissions=["read", "deposit"],  # No transfer
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            is_active=True
        )
        db_session.add(no_transfer_key)
        db_session.commit()
        
        response = client.post(
            "/api/v1/wallet/transfer",
            headers={"X-API-Key": no_transfer_key.key},
            json={
                "wallet_number": "1234567890123",
                "amount": 1000
            }
        )
        
        assert response.status_code == 403


class TestTransactionHistory:
    """Test transaction history."""
    
    def test_get_transactions(self, client, test_user_token):
        """Test getting transaction history."""
        response = client.get(
            "/api/v1/wallet/transactions",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_transactions_with_api_key(self, client, test_api_key):
        """Test getting transactions with API key."""
        response = client.get(
            "/api/v1/wallet/transactions",
            headers={"X-API-Key": test_api_key.key}
        )
        
        assert response.status_code == 200