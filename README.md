# Wallet Service - Paystack Integration with JWT & API Keys

A production-ready wallet service supporting Google OAuth, Paystack deposits, wallet transfers, and flexible API key authentication with permissions.

## Features

 **Google OAuth Authentication**
- Sign in with Google
- Auto-creates wallet on signup
- JWT token generation

 **Wallet Operations**
- Deposit via Paystack
- Check balance
- Transfer between wallets
- Transaction history

 **Paystack Integration**
- Payment initialization
- Webhook processing (auto-credits wallet)
- Signature verification
- Idempotent webhooks

 **API Key System**
- Permission-based access (read, deposit, transfer)
- Max 5 active keys per user
- Flexible expiry (1H, 1D, 1M, 1Y)
- Key rollover for expired keys

 **Dual Authentication**
- JWT for users
- API keys for services
- **Fixed: API key checked FIRST** (solves Swagger UI issue)

## Quick Start

### 1. Installation

```bash
# Clone and setup
git clone <repo>
cd wallet-service

# Install dependencies
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### 2. Environment Setup

Create `.env` file:

```bash
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/wallet_db

# JWT
SECRET_KEY=your-secret-key-here

# Google OAuth (get from Google Cloud Console)
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

# Paystack (get from Paystack dashboard)
PAYSTACK_SECRET_KEY=sk_test_xxx
PAYSTACK_PUBLIC_KEY=pk_test_xxx
PAYSTACK_WEBHOOK_SECRET=your_webhook_secret
```

### 3. Database Migration

```bash
alembic upgrade head
```

### 4. Run Server

```bash
uvicorn app.main:app --reload
```

Visit: http://localhost:8000/docs

---

## API Endpoints

### Authentication

**GET /api/v1/auth/google**
- Initiates Google OAuth flow
- Redirects to Google login

**GET /api/v1/auth/google/callback**
- Handles Google callback
- Returns JWT token

### API Keys

**POST /api/v1/keys/create**
```json
{
  "name": "wallet-service",
  "permissions": ["deposit", "transfer", "read"],
  "expiry": "1M"
}
```
Returns: API key (shown only once!)

**POST /api/v1/keys/rollover**
```json
{
  "expired_key_id": 5,
  "expiry": "1D"
}
```
Creates new key with same permissions

**GET /api/v1/keys**
- Lists all your API keys

**DELETE /api/v1/keys/{key_id}**
- Revokes an API key

### Wallet Operations

**POST /api/v1/wallet/deposit**
```json
{
  "amount": 5000
}
```
Returns: Paystack payment URL

**GET /api/v1/wallet/balance**
Returns: Current balance

**POST /api/v1/wallet/transfer**
```json
{
  "wallet_number": "1234567890123",
  "amount": 3000
}
```
Transfers to another wallet

**GET /api/v1/wallet/transactions**
Returns: Transaction history

**GET /api/v1/wallet/deposit/{reference}/status**
Checks deposit status (doesn't credit wallet)

### Webhook

**POST /api/v1/wallet/paystack/webhook**
- Receives Paystack webhooks
- **Only endpoint that credits wallets**
- Validates signature
- Idempotent

---

## Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create project
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URI: `http://localhost:8000/api/v1/auth/google/callback`
6. Copy Client ID and Secret to `.env`

---

## Paystack Setup

1. Create account at [Paystack](https://paystack.com/)
2. Get API keys from Settings → API Keys
3. Set webhook URL: `https://your-domain.com/api/v1/wallet/paystack/webhook`
4. Copy webhook secret to `.env`

---

## Authentication Methods

### Method 1: JWT (for users)
```bash
# Login with Google first
curl http://localhost:8000/api/v1/auth/google

# Use token
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/wallet/balance
```

### Method 2: API Key (for services)
```bash
# Create key first (needs JWT)
# Then use key
curl -H "X-API-Key: sk_xxx" \
  http://localhost:8000/api/v1/wallet/balance
```


---

## API Key Permissions

- **read** - View balance, transactions
- **deposit** - Initialize deposits
- **transfer** - Transfer funds

Example:
```json
{
  "permissions": ["read", "deposit"]  // Can view and deposit, but not transfer
}
```

---

## Expiry Formats

- `1H` - 1 hour
- `5D` - 5 days
- `2M` - 2 months (60 days)
- `1Y` - 1 year (365 days)

---

---

## Security Features

 Google OAuth (no password storage)
 JWT with expiration
 Paystack webhook signature verification
 API key permissions
 Max 5 active keys per user
 Atomic transfers (no partial deductions)
 Idempotent webhooks (no double-credits)
 Balance checks before transfers

---

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Test specific file
pytest tests/test_wallet.py -v
```

---

## Database Schema

### users
- id, google_id, email, name, picture

### wallets
- id, wallet_number, balance, user_id

### transactions
- id, reference, type, status, amount, wallet_id

### api_keys
- id, key, name, permissions (JSON), expires_at, user_id

---

## Production Deployment

1. Use HTTPS (required for OAuth)
2. Set strong SECRET_KEY
3. Use production Paystack keys
4. Set up proper webhook URL
5. Enable database backups
6. Add rate limiting
7. Monitor webhook failures


Built with FastAPI, PostgreSQL, Paystack, and Google OAuth 