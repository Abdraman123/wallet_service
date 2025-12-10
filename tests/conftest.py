import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from decimal import Decimal

from app.main import app
from app.db.session import get_db
from app.models.base import Base
from app.models.user import User
from app.models.wallet import Wallet
from app.models.api_key import APIKey
from app.utils.security import create_access_token, generate_wallet_number

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    """Create a test client with database dependency override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        google_id="test_google_id_123",
        email="test@example.com",
        name="Test User",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    # Create wallet for user
    wallet = Wallet(
        user_id=user.id,
        wallet_number=generate_wallet_number(),
        balance=Decimal("10000.00")
    )
    db_session.add(wallet)
    db_session.commit()
    
    return user


@pytest.fixture
def test_user_token(test_user):
    """Create JWT token for test user."""
    return create_access_token(data={"sub": str(test_user.id)})


@pytest.fixture
def test_api_key(db_session, test_user):
    """Create a test API key with all permissions."""
    from datetime import datetime, timedelta, timezone
    from app.utils.security import generate_api_key
    
    api_key = APIKey(
        key=generate_api_key(),
        name="Test Key",
        user_id=test_user.id,
        permissions=["read", "deposit", "transfer"],
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        is_active=True
    )
    db_session.add(api_key)
    db_session.commit()
    db_session.refresh(api_key)
    
    return api_key