"""
Authentication routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from app.services.auth_service import auth_service
from config.config import settings

router = APIRouter()

# Cookie settings
COOKIE_NAME = "auth_token"
COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days in seconds
COOKIE_PATH = "/"
COOKIE_DOMAIN = None  # Use None for same domain
COOKIE_SECURE = getattr(settings, 'ENVIRONMENT', 'development') != "development"  # True in production
COOKIE_HTTPONLY = True
COOKIE_SAMESITE = "lax"  # "lax" is more compatible than "strict"

class UserCreate(BaseModel):
    """Request model for user registration."""
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    """Request model for user login."""
    email: EmailStr
    password: str

class ProfileUpdate(BaseModel):
    """Request model for profile update."""
    full_name: str
    email: EmailStr

class PasswordChange(BaseModel):
    """Request model for password change."""
    current_password: str
    new_password: str

class TwoFactorVerify(BaseModel):
    """Request model for 2FA verification."""
    code: str

class AccountDelete(BaseModel):
    """Request model for account deletion."""
    password: str



@router.post("/register")
async def register(user_data: UserCreate, response: Response):
    """
    Register a new user.

    Args:
        user_data: User registration data
        response: FastAPI Response object for setting cookies

    Returns:
        User information and access token
    """
    result = await auth_service.register_user(
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name
    )

    # If registration was successful and we have a token, set it as a cookie
    if "access_token" in result:
        response.set_cookie(
            key=COOKIE_NAME,
            value=result["access_token"],
            max_age=COOKIE_MAX_AGE,
            path=COOKIE_PATH,
            domain=COOKIE_DOMAIN,
            secure=COOKIE_SECURE,
            httponly=COOKIE_HTTPONLY,
            samesite=COOKIE_SAMESITE
        )

    return result

@router.post("/login")
async def login(user_data: UserLogin, response: Response):
    """
    Login a user.

    Args:
        user_data: User login data
        response: FastAPI Response object for setting cookies

    Returns:
        User information and access token
    """
    result = await auth_service.login_user(
        email=user_data.email,
        password=user_data.password
    )

    # Set the token as a cookie
    if "access_token" in result:
        response.set_cookie(
            key=COOKIE_NAME,
            value=result["access_token"],
            max_age=COOKIE_MAX_AGE,
            path=COOKIE_PATH,
            domain=COOKIE_DOMAIN,
            secure=COOKIE_SECURE,
            httponly=COOKIE_HTTPONLY,
            samesite=COOKIE_SAMESITE
        )

    return result

@router.get("/me")
async def get_current_user(current_user = Depends(auth_service.get_current_user)):
    """
    Get current user information.

    Args:
        current_user: Current authenticated user (from dependency)

    Returns:
        User information
    """
    return current_user

@router.get("/status")
async def auth_status():
    """
    Get authentication status information.

    This is a public endpoint that doesn't require authentication.
    It provides information about the authentication service status.

    Returns:
        Authentication service status
    """
    return {
        "status": "ok",
        "auth_service": "supabase",
        "email_verification_required": True,
        "message": "Authentication service is available"
    }

@router.get("/debug-token")
async def debug_token(current_user = Depends(auth_service.get_current_user)):
    """
    Debug endpoint to check token validity.

    This endpoint requires authentication and returns the current user
    along with a success message if the token is valid.

    Args:
        current_user: Current authenticated user (from dependency)

    Returns:
        Debug information about the token
    """
    return {
        "status": "ok",
        "message": "Token is valid",
        "user": current_user
    }

@router.post("/logout")
async def logout(response: Response):
    """
    Logout a user by clearing their authentication cookie.

    Args:
        response: FastAPI Response object for clearing cookies

    Returns:
        Success message
    """
    # Clear the auth cookie
    response.delete_cookie(
        key=COOKIE_NAME,
        path=COOKIE_PATH,
        domain=COOKIE_DOMAIN
    )

    return {
        "status": "ok",
        "message": "Logged out successfully"
    }

@router.put("/update-profile")
async def update_profile(
    profile_data: ProfileUpdate,
    current_user = Depends(auth_service.get_current_user)
):
    """
    Update user profile information.

    Args:
        profile_data: ProfileUpdate with new profile information
        current_user: Current authenticated user

    Returns:
        Updated user information
    """
    return await auth_service.update_profile(
        user_id=current_user["id"],
        full_name=profile_data.full_name,
        email=profile_data.email
    )

@router.put("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user = Depends(auth_service.get_current_user)
):
    """
    Change user password.

    Args:
        password_data: PasswordChange with current and new passwords
        current_user: Current authenticated user

    Returns:
        Success message
    """
    return await auth_service.change_password(
        user_id=current_user["id"],
        current_password=password_data.current_password,
        new_password=password_data.new_password
    )

@router.post("/enable-2fa")
async def enable_2fa(current_user = Depends(auth_service.get_current_user)):
    """
    Enable two-factor authentication.

    Args:
        current_user: Current authenticated user

    Returns:
        2FA setup information (QR code, backup codes)
    """
    return await auth_service.enable_2fa(current_user["id"])

@router.post("/verify-2fa")
async def verify_2fa(
    verify_data: TwoFactorVerify,
    current_user = Depends(auth_service.get_current_user)
):
    """
    Verify and complete two-factor authentication setup.

    Args:
        verify_data: TwoFactorVerify with verification code
        current_user: Current authenticated user

    Returns:
        Success message
    """
    return await auth_service.verify_2fa(
        user_id=current_user["id"],
        code=verify_data.code
    )

@router.delete("/disable-2fa")
async def disable_2fa(
    verify_data: TwoFactorVerify,
    current_user = Depends(auth_service.get_current_user)
):
    """
    Disable two-factor authentication.

    Args:
        verify_data: TwoFactorVerify with verification code
        current_user: Current authenticated user

    Returns:
        Success message
    """
    return await auth_service.disable_2fa(
        user_id=current_user["id"],
        code=verify_data.code
    )

@router.delete("/delete-account")
async def delete_account(
    response: Response,
    account_data: AccountDelete,
    current_user = Depends(auth_service.get_current_user)
):
    """
    Delete user account.

    Args:
        response: FastAPI Response object for clearing cookies
        account_data: AccountDelete with password for verification
        current_user: Current authenticated user

    Returns:
        Success message
    """
    result = await auth_service.delete_account(
        user_id=current_user["id"],
        password=account_data.password
    )

    # Clear the auth cookie
    response.delete_cookie(
        key=COOKIE_NAME,
        path=COOKIE_PATH,
        domain=COOKIE_DOMAIN
    )

    return result


