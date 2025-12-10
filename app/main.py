from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.openapi.utils import get_openapi
from app.config import settings
from app.db.session import engine
from app.api.v1.routes import auth, api_keys, wallet, webhook

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Wallet Service with Paystack, JWT & API Keys",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add session middleware for OAuth (required by authlib)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(api_keys.router, prefix=settings.API_V1_PREFIX)
app.include_router(wallet.router, prefix=settings.API_V1_PREFIX)
app.include_router(webhook.router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Root"])
def root():
    """Root endpoint."""
    return {
        "message": "Wallet Service API is running",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    print(f" {settings.PROJECT_NAME} starting up...")
    print(f" API Documentation: http://localhost:8000/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    print(f" {settings.PROJECT_NAME} shutting down...")
    engine.dispose()


# Add custom OpenAPI schema with both auth methods
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Define security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT token"
        },
        "APIKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "Enter your API key"
        }
    }

    # Helper to assign security per operation
    def set_security(operation, security):
        if isinstance(operation, dict):
            operation["security"] = security

    # Map endpoints and methods to their required security
    # Use exact paths with {param} as in OpenAPI paths
    for path, path_item in openapi_schema["paths"].items():
        for method, operation in path_item.items():
            # Normalize to lower case
            method = method.lower()

            # Auth-exempt endpoints
            if path.startswith("/auth/google"):
                # No security required for google login or callback
                continue
            if path == "/wallet/paystack/webhook" and method == "post":
                # Webhook has no auth (signature header only)
                continue

            # API Key Management endpoints: JWT only
            if path.startswith("/keys"):
                # All keys routes require JWT only
                set_security(operation, [{"BearerAuth": []}])
                continue

            # Wallet endpoints with mixed JWT/API Key permissions
            if path.startswith("/wallet"):
                if path == "/wallet/deposit" and method == "post":
                    # Deposit: JWT or API key with 'deposit' permission
                    set_security(operation, [
                        {"BearerAuth": []},
                        {"APIKeyAuth": ["deposit"]}
                    ])
                elif path.startswith("/wallet/deposit/") and method == "get":
                    # Deposit status: JWT or API key with 'read' permission
                    set_security(operation, [
                        {"BearerAuth": []},
                        {"APIKeyAuth": ["read"]}
                    ])
                elif path == "/wallet/balance" and method == "get":
                    # Wallet balance: JWT or API key with 'read' permission
                    set_security(operation, [
                        {"BearerAuth": []},
                        {"APIKeyAuth": ["read"]}
                    ])
                elif path == "/wallet/transfer" and method == "post":
                    # Transfer: JWT or API key with 'transfer' permission
                    set_security(operation, [
                        {"BearerAuth": []},
                        {"APIKeyAuth": ["transfer"]}
                    ])
                elif path == "/wallet/transactions" and method == "get":
                    # Transactions: JWT or API key with 'read' permission
                    set_security(operation, [
                        {"BearerAuth": []},
                        {"APIKeyAuth": ["read"]}
                    ])
                else:
                    # For any other wallet endpoints, default to JWT only for safety
                    set_security(operation, [{"BearerAuth": []}])
                continue

            # For all other endpoints, apply no security by default (or apply JWT)
            # If you want to secure everything else by JWT:
            # set_security(operation, [{"BearerAuth": []}])

    app.openapi_schema = openapi_schema
    return app.openapi_schema

