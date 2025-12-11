from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.db.session import get_db
from app.services.auth_service import AuthService, oauth
from app.config import settings
from app.schemas.auth import TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/google", summary="Initiate Google sign-in")
async def google_login(request: Request):
    """
    Initiate Google OAuth login flow.
    Returns the Google authorization URL that frontend should redirect to.
    
    Response includes:
    - authorization_url: URL to redirect user to Google login
    """
    # Use the configured redirect URI (ensures HTTPS and exact match with Google Console)
    redirect_uri = settings.GOOGLE_REDIRECT_URI

    # Use authorize_redirect to set up session state and get RedirectResponse
    redirect_response = await oauth.google.authorize_redirect(request, redirect_uri)

    # Extract the actual authorization URL from the RedirectResponse Location header
    authorization_url = (
        redirect_response.headers.get("location")
        or redirect_response.headers.get("Location")
    )

    # Return authorization URL for frontend to handle redirect
    return JSONResponse(
        status_code=200,
        content={
            "authorization_url": authorization_url,
            "message": "Redirect user to the authorization_url to sign in with Google"
        }
    )


@router.get("/google/callback", summary="Google OAuth callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """
    Handle Google OAuth callback.
    Creates user if not exists and returns JWT token with user details.
    """
    # Get token from Google
    token = await oauth.google.authorize_access_token(request)
    
    # Get user info from Google
    user_info = token.get('userinfo')
    
    if not user_info:
        user_info = await oauth.google.parse_id_token(request, token)
    
    # Extract user details
    google_id = user_info['sub']
    email = user_info['email']
    name = user_info.get('name')
    picture = user_info.get('picture')
    
    # Get or create user
    auth_service = AuthService(db)
    user = auth_service.get_or_create_user(
        google_id=google_id,
        email=email,
        name=name,
        picture=picture
    )
    
    # Create JWT token
    access_token = auth_service.create_jwt_for_user(user.id)
    
    # Return response with token and user information
    return JSONResponse(
        status_code=200,
        content={
            "access_token": access_token,
            "token_type": "bearer",
           
        }
    )