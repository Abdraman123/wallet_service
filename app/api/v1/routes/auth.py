from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.auth_service import AuthService, oauth
from app.schemas.auth import TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/google", summary="Initiate Google sign-in")
async def google_login(request: Request):
    """
    Redirect to Google OAuth login page.
    User will sign in with Google.
    """
    redirect_uri = request.url_for('google_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", summary="Google OAuth callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """
    Handle Google OAuth callback.
    Creates user if not exists, returns JWT token.
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
    
    # Return token (in production, redirect to frontend with token)
    return TokenResponse(access_token=access_token)