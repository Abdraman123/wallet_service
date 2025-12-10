import pytest
from datetime import datetime, timedelta, timezone


class TestAPIKeyCreation:
    """Test API key creation."""
    
    def test_create_api_key_success(self, client, test_user_token):
        """Test successful API key creation."""
        response = client.post(
            "/api/v1/keys/create",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "name": "Test Service",
                "permissions": ["read", "deposit"],
                "expiry": "1D"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "api_key" in data
        assert data["api_key"].startswith("sk_")
        assert data["name"] == "Test Service"
        assert set(data["permissions"]) == {"read", "deposit"}
    
    def test_create_api_key_invalid_permission(self, client, test_user_token):
        """Test API key creation with invalid permission."""
        response = client.post(
            "/api/v1/keys/create",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "name": "Test Service",
                "permissions": ["invalid_permission"],
                "expiry": "1D"
            }
        )
        
        assert response.status_code == 400
        assert "Invalid permissions" in response.json()["detail"]
    
    def test_create_api_key_invalid_expiry(self, client, test_user_token):
        """Test API key creation with invalid expiry format."""
        response = client.post(
            "/api/v1/keys/create",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "name": "Test Service",
                "permissions": ["read"],
                "expiry": "invalid"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_max_active_keys_limit(self, client, test_user_token):
        """Test maximum 5 active keys limit."""
        # Create 5 keys
        for i in range(5):
            response = client.post(
                "/api/v1/keys/create",
                headers={"Authorization": f"Bearer {test_user_token}"},
                json={
                    "name": f"Key {i+1}",
                    "permissions": ["read"],
                    "expiry": "1D"
                }
            )
            assert response.status_code == 201
        
        # Try to create 6th key (should fail)
        response = client.post(
            "/api/v1/keys/create",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "name": "Key 6",
                "permissions": ["read"],
                "expiry": "1D"
            }
        )
        
        assert response.status_code == 400
        assert "Maximum 5 active API keys" in response.json()["detail"]


class TestAPIKeyRollover:
    """Test API key rollover."""
    
    def test_rollover_expired_key(self, client, test_user_token, db_session, test_user):
        """Test rolling over an expired key."""
        from app.models.api_key import APIKey
        from app.utils.security import generate_api_key
        
        # Create an expired key
        expired_key = APIKey(
            key=generate_api_key(),
            name="Expired Key",
            user_id=test_user.id,
            permissions=["read", "transfer"],
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),  # Already expired
            is_active=True
        )
        db_session.add(expired_key)
        db_session.commit()
        
        # Rollover
        response = client.post(
            "/api/v1/keys/rollover",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "expired_key_id": expired_key.id,
                "expiry": "1M"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "api_key" in data
        assert set(data["permissions"]) == {"read", "transfer"}  # Same permissions
    
    def test_rollover_non_expired_key_fails(self, client, test_user_token, test_api_key):
        """Test that rollover fails for non-expired keys."""
        response = client.post(
            "/api/v1/keys/rollover",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "expired_key_id": test_api_key.id,
                "expiry": "1D"
            }
        )
        
        assert response.status_code == 400
        assert "not expired" in response.json()["detail"]


class TestAPIKeyListing:
    """Test API key listing."""
    
    def test_list_api_keys(self, client, test_user_token, test_api_key):
        """Test listing user's API keys."""
        response = client.get(
            "/api/v1/keys",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["name"] == "Test Key"
        assert "api_key" not in data[0]  # Actual key not shown in list


class TestAPIKeyRevocation:
    """Test API key revocation."""
    
    def test_revoke_api_key(self, client, test_user_token, test_api_key):
        """Test revoking an API key."""
        response = client.delete(
            f"/api/v1/keys/{test_api_key.id}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 200
        assert "revoked" in response.json()["message"]
    
    def test_revoke_nonexistent_key(self, client, test_user_token):
        """Test revoking non-existent key."""
        response = client.delete(
            "/api/v1/keys/99999",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 404