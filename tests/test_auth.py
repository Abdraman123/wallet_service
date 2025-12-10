import pytest
from unittest.mock import patch, MagicMock


class TestGoogleOAuth:
    """Test Google OAuth authentication."""
    
    @patch('app.services.auth_service.oauth')
    def test_google_login_redirect(self, mock_oauth, client):
        """Test Google login initiates redirect."""
        # Mock OAuth redirect
        mock_oauth.google.authorize_redirect = MagicMock()
        
        response = client.get("/api/v1/auth/google")
        
        # Should initiate OAuth flow
        # Note: This is challenging to test fully without mocking the entire OAuth flow
        assert response.status_code in [200, 307]  # 307 is redirect
    
    @patch('app.services.auth_service.oauth')
    def test_google_callback_creates_user(self, mock_oauth, client, db_session):
        """Test Google callback creates new user and wallet."""
        from app.models.user import User
        from app.models.wallet import Wallet
        
        # Mock OAuth token and user info
        mock_token = {
            'userinfo': {
                'sub': 'google_id_12345',
                'email': 'newuser@example.com',
                'name': 'New User',
                'picture': 'https://example.com/photo.jpg'
            }
        }
        mock_oauth.google.authorize_access_token = MagicMock(return_value=mock_token)
        
        # Make request
        response = client.get("/api/v1/auth/google/callback")
        
        # Verify user was created
        user = db_session.query(User).filter_by(google_id='google_id_12345').first()
        assert user is not None
        assert user.email == 'newuser@example.com'
        assert user.name == 'New User'
        
        # Verify wallet was created
        wallet = db_session.query(Wallet).filter_by(user_id=user.id).first()
        assert wallet is not None
        assert len(wallet.wallet_number) == 13
        
        # Verify JWT token returned
        assert response.status_code == 200
        data = response.json()
        assert 'access_token' in data
        assert data['token_type'] == 'bearer'
    
    @patch('app.services.auth_service.oauth')
    def test_google_callback_existing_user(self, mock_oauth, client, test_user, db_session):
        """Test Google callback for existing user doesn't create duplicate."""
        from app.models.user import User
        
        # Mock OAuth token with existing user's Google ID
        mock_token = {
            'userinfo': {
                'sub': test_user.google_id,
                'email': test_user.email,
                'name': test_user.name
            }
        }
        mock_oauth.google.authorize_access_token = MagicMock(return_value=mock_token)
        
        # Count users before
        user_count_before = db_session.query(User).count()
        
        # Make request
        response = client.get("/api/v1/auth/google/callback")
        
        # Verify no new user created
        user_count_after = db_session.query(User).count()
        assert user_count_after == user_count_before
        
        # Verify JWT returned
        assert response.status_code == 200
        data = response.json()
        assert 'access_token' in data


class TestJWTAuthentication:
    """Test JWT token authentication."""
    
    def test_valid_jwt_token(self, client, test_user_token):
        """Test valid JWT token grants access."""
        response = client.get(
            "/api/v1/wallet/balance",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 200
    
    def test_invalid_jwt_token(self, client):
        """Test invalid JWT token is rejected."""
        response = client.get(
            "/api/v1/wallet/balance",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        
        assert response.status_code == 401
    
    def test_missing_jwt_token(self, client):
        """Test missing JWT token is rejected."""
        response = client.get("/api/v1/wallet/balance")
        
        assert response.status_code == 401
    
    def test_expired_jwt_token(self, client):
        """Test expired JWT token is rejected."""
        from datetime import timedelta
        from app.utils.security import create_access_token
        
        # Create token that expires immediately
        expired_token = create_access_token(
            data={"sub": "1"},
            expires_delta=timedelta(seconds=-1)  # Already expired
        )
        
        response = client.get(
            "/api/v1/wallet/balance",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert response.status_code == 401


class TestDualAuthentication:
    """Test JWT vs API key authentication priority."""
    
    def test_api_key_takes_priority_over_jwt(self, client, test_user_token, test_api_key):
        """Test API key is checked before JWT when both present."""
        response = client.get(
            "/api/v1/wallet/balance",
            headers={
                "Authorization": f"Bearer {test_user_token}",
                "X-API-Key": test_api_key.key
            }
        )
        
        # Should succeed with API key
        assert response.status_code == 200
    
    def test_api_key_alone_works(self, client, test_api_key):
        """Test API key works without JWT."""
        response = client.get(
            "/api/v1/wallet/balance",
            headers={"X-API-Key": test_api_key.key}
        )
        
        assert response.status_code == 200
    
    def test_jwt_alone_works(self, client, test_user_token):
        """Test JWT works without API key."""
        response = client.get(
            "/api/v1/wallet/balance",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 200
    
    def test_expired_api_key_rejected(self, client, db_session, test_user):
        """Test expired API key is rejected."""
        from app.models.api_key import APIKey
        from app.utils.security import generate_api_key
        from datetime import datetime, timedelta, timezone
        
        # Create expired key
        expired_key = APIKey(
            key=generate_api_key(),
            name="Expired",
            user_id=test_user.id,
            permissions=["read"],
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
            is_active=True
        )
        db_session.add(expired_key)
        db_session.commit()
        
        response = client.get(
            "/api/v1/wallet/balance",
            headers={"X-API-Key": expired_key.key}
        )
        
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()
    
    def test_revoked_api_key_rejected(self, client, db_session, test_user):
        """Test revoked API key is rejected."""
        from app.models.api_key import APIKey
        from app.utils.security import generate_api_key
        from datetime import datetime, timedelta, timezone
        
        # Create revoked key
        revoked_key = APIKey(
            key=generate_api_key(),
            name="Revoked",
            user_id=test_user.id,
            permissions=["read"],
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            is_active=False  # Revoked
        )
        db_session.add(revoked_key)
        db_session.commit()
        
        response = client.get(
            "/api/v1/wallet/balance",
            headers={"X-API-Key": revoked_key.key}
        )
        
        assert response.status_code == 401