"""
Authentication routes.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie, Request
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any

from app.services.auth_service import auth_service
from app.services.token_service import token_service
from config.config import settings

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Cookie settings
ACCESS_TOKEN_COOKIE_NAME = "auth_token"
REFRESH_TOKEN_COOKIE_NAME = "refresh_token"
ACCESS_TOKEN_MAX_AGE = 60 * settings.ACCESS_TOKEN_EXPIRE_MINUTES  # Convert minutes to seconds
REFRESH_TOKEN_MAX_AGE = 60 * 60 * 24 * settings.REFRESH_TOKEN_EXPIRE_DAYS  # Convert days to seconds
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

    # If registration was successful and we have a token, set cookies
    if "access_token" in result:
        # Set access token cookie
        response.set_cookie(
            key=ACCESS_TOKEN_COOKIE_NAME,
            value=result["access_token"],
            max_age=ACCESS_TOKEN_MAX_AGE,
            path=COOKIE_PATH,
            domain=COOKIE_DOMAIN,
            secure=COOKIE_SECURE,
            httponly=COOKIE_HTTPONLY,
            samesite=COOKIE_SAMESITE
        )

        # Create and set refresh token
        user_id = result["user"]["id"]
        refresh_token = await token_service.create_refresh_token(user_id)

        # Add refresh token to the result
        result["refresh_token"] = refresh_token
        result["expires_in"] = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # in seconds
        result["refresh_expires_in"] = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400  # in seconds

        # Set refresh token cookie
        response.set_cookie(
            key=REFRESH_TOKEN_COOKIE_NAME,
            value=refresh_token,
            max_age=REFRESH_TOKEN_MAX_AGE,
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

    # Set the tokens as cookies
    if "access_token" in result:
        # Set access token cookie
        response.set_cookie(
            key=ACCESS_TOKEN_COOKIE_NAME,
            value=result["access_token"],
            max_age=ACCESS_TOKEN_MAX_AGE,
            path=COOKIE_PATH,
            domain=COOKIE_DOMAIN,
            secure=COOKIE_SECURE,
            httponly=COOKIE_HTTPONLY,
            samesite=COOKIE_SAMESITE
        )

        # Create and set refresh token
        user_id = result["user"]["id"]
        refresh_token = await token_service.create_refresh_token(user_id)

        # Add refresh token to the result
        result["refresh_token"] = refresh_token
        result["expires_in"] = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # in seconds
        result["refresh_expires_in"] = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400  # in seconds

        # Set refresh token cookie
        response.set_cookie(
            key=REFRESH_TOKEN_COOKIE_NAME,
            value=refresh_token,
            max_age=REFRESH_TOKEN_MAX_AGE,
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
    try:
        # Get more detailed user information
        user_id = current_user["id"]
        user_details = await auth_service.get_user_by_id(user_id)

        # Return a complete user object
        return {
            "id": user_details.get("id", user_id),
            "email": user_details.get("email", ""),
            "full_name": user_details.get("full_name", ""),
            "subscription_tier": user_details.get("subscription_tier", "free"),
            "created_at": user_details.get("created_at", ""),
            "updated_at": user_details.get("updated_at", ""),
            "last_login": user_details.get("last_login", "")
        }
    except Exception as e:
        logger.warning(f"Error getting detailed user info: {str(e)}")
        # Fall back to the basic user info
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



class RefreshTokenRequest(BaseModel):
    """Request model for refresh token."""
    refresh_token: Optional[str] = None

@router.post("/test-refresh-token")
async def test_refresh_token(
    response: Response,
    request_data: Optional[RefreshTokenRequest] = None,
    refresh_token: Optional[str] = Cookie(None, alias=REFRESH_TOKEN_COOKIE_NAME)
):
    """
    Refresh an access token using a refresh token from cookies or request body.
    This implements the proper OAuth refresh token flow:
    1. Extract refresh token from cookies or request body
    2. Validate the refresh token
    3. Generate a new access token using Supabase's refresh_session method
    4. Optionally rotate the refresh token
    5. Set both tokens as cookies
    6. Return the tokens and user information

    Args:
        response: FastAPI Response object for setting cookies
        request_data: Optional request body containing refresh_token
        refresh_token: Refresh token from cookies (takes precedence over request body)

    Returns:
        New access token and refresh token with user information
    """
    try:
        # Check if refresh token is provided in cookies
        if not refresh_token and request_data:
            # Try to get from request body as fallback
            refresh_token = request_data.refresh_token
            logger.info("Using refresh token from request body")

        # If still no refresh token, raise an error
        if not refresh_token:
            logger.warning("No refresh token found in cookies or request body")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token is required in either cookies or request body"
            )

        # Validate the refresh token
        logger.info(f"Validating refresh token: {refresh_token[:10]}...")
        try:
            token_data = await token_service.validate_refresh_token(refresh_token)

            if not token_data or "user_id" not in token_data:
                logger.error(f"Invalid token data returned: {token_data}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token - missing user_id"
                )
        except Exception as token_error:
            logger.error(f"Error validating refresh token: {str(token_error)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid refresh token: {str(token_error)}"
            )

        user_id = token_data["user_id"]
        logger.info(f"Refresh token is valid for user ID: {user_id}")

        # Get user information
        try:
            user_info = await auth_service.get_user_by_id(user_id)
            if not user_info:
                logger.error(f"User not found for ID: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            logger.info(f"Retrieved user info for user ID: {user_id}")
        except Exception as user_error:
            logger.error(f"Error getting user info: {str(user_error)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting user info: {str(user_error)}"
            )

        # Generate a new access token
        try:
            # First try to use the refresh token directly with Supabase
            try:
                logger.info(f"Attempting to refresh session with token: {refresh_token[:10]}...")
                auth_response = await auth_service.supabase.auth.refresh_session(refresh_token)
                if auth_response and hasattr(auth_response, 'session') and auth_response.session:
                    access_token = auth_response.session.access_token
                    logger.info(f"Successfully refreshed session for user ID: {user_id}")
                else:
                    logger.warning("Refresh session returned invalid response")
                    raise Exception("Invalid response from refresh_session")
            except Exception as refresh_error:
                logger.warning(f"Could not refresh session: {str(refresh_error)}")

                # Fall back to manual token generation
                # Get user email for login
                email = user_info.get("email")
                if not email:
                    logger.error(f"User email not found for ID: {user_id}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="User email not found"
                    )

                # Try to get the user's password or a stored secret
                # This is a simplified approach - in a real system, you'd need a more secure method
                # For testing purposes, we'll use a direct token generation method
                try:
                    # Create a JWT token manually
                    import jwt
                    import time

                    # Create payload with claims
                    payload = {
                        "sub": user_id,
                        "email": email,
                        "iat": int(time.time()),
                        "exp": int(time.time()) + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60),
                        "aud": "authenticated"
                    }

                    # Use a secret key for signing
                    secret_key = settings.SECRET_KEY

                    # Generate the token
                    access_token = jwt.encode(payload, secret_key, algorithm="HS256")
                    logger.info(f"Generated manual JWT token for user ID: {user_id}")
                except Exception as jwt_error:
                    logger.error(f"Error generating manual JWT: {str(jwt_error)}")

                    # Last resort: try the original method
                    access_token = await auth_service.generate_access_token(user_id)
                    logger.info(f"Generated token using original method for user ID: {user_id}")
        except Exception as token_error:
            logger.error(f"All token generation methods failed: {str(token_error)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating access token: {str(token_error)}"
            )

        # Decide whether to rotate the refresh token
        # For security, we can rotate refresh tokens periodically
        # Here we'll implement a simple rotation strategy
        should_rotate = False

        # Option 1: Rotate on every use (most secure)
        # should_rotate = True

        # Option 2: Rotate based on age or usage count
        # This would require additional fields in the token record

        # Option 3: Keep the same refresh token (less secure but simpler)
        # should_rotate = False

        # For now, we'll use the same refresh token
        new_refresh_token = refresh_token

        if should_rotate:
            try:
                # Revoke the old token
                await token_service.revoke_refresh_token(refresh_token)

                # Create a new refresh token
                new_refresh_token = await token_service.create_refresh_token(user_id)
                logger.info(f"Rotated refresh token for user ID: {user_id}")
            except Exception as rotate_error:
                logger.error(f"Error rotating refresh token: {str(rotate_error)}")
                # Continue with the old token if rotation fails
                new_refresh_token = refresh_token
                logger.info(f"Continuing with old refresh token for user ID: {user_id}")

        # Set the tokens as cookies
        response.set_cookie(
            key=ACCESS_TOKEN_COOKIE_NAME,
            value=access_token,
            max_age=ACCESS_TOKEN_MAX_AGE,
            path=COOKIE_PATH,
            domain=COOKIE_DOMAIN,
            secure=COOKIE_SECURE,
            httponly=COOKIE_HTTPONLY,
            samesite=COOKIE_SAMESITE
        )

        response.set_cookie(
            key=REFRESH_TOKEN_COOKIE_NAME,
            value=new_refresh_token,
            max_age=REFRESH_TOKEN_MAX_AGE,
            path=COOKIE_PATH,
            domain=COOKIE_DOMAIN,
            secure=COOKIE_SECURE,
            httponly=COOKIE_HTTPONLY,
            samesite=COOKIE_SAMESITE
        )

        logger.info(f"Successfully refreshed tokens for user ID: {user_id}")
        return {
            "status": "success",
            "message": "Token refreshed successfully",
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # in seconds
            "refresh_expires_in": settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,  # in seconds
            "user": user_info
        }
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        import traceback
        logger.error(f"Unexpected error refreshing token: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error refreshing token: {str(e)}"
        )

@router.post("/refresh-token")
async def refresh_token(
    response: Response,
    current_user = Depends(auth_service.get_current_user)
):
    """
    Refresh an access token for the current user.

    This is the original implementation that requires an active access token.
    Consider using /test-refresh-token instead which follows OAuth best practices.

    Args:
        response: FastAPI Response object for setting cookies
        current_user: Current authenticated user

    Returns:
        New access token and refresh token
    """

    try:
        user_id = current_user["id"]

        # Create a refresh token
        refresh_token = await token_service.create_refresh_token(user_id)

        # Generate a new access token
        access_token = await auth_service.generate_access_token(user_id)

        # Set the new tokens as cookies
        response.set_cookie(
            key=ACCESS_TOKEN_COOKIE_NAME,
            value=access_token,
            max_age=ACCESS_TOKEN_MAX_AGE,
            path=COOKIE_PATH,
            domain=COOKIE_DOMAIN,
            secure=COOKIE_SECURE,
            httponly=COOKIE_HTTPONLY,
            samesite=COOKIE_SAMESITE
        )

        response.set_cookie(
            key=REFRESH_TOKEN_COOKIE_NAME,
            value=refresh_token,
            max_age=REFRESH_TOKEN_MAX_AGE,
            path=COOKIE_PATH,
            domain=COOKIE_DOMAIN,
            secure=COOKIE_SECURE,
            httponly=COOKIE_HTTPONLY,
            samesite=COOKIE_SAMESITE
        )

        return {
            "status": "success",
            "message": "Token refreshed successfully",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # in seconds
            "refresh_expires_in": settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,  # in seconds
            "user": current_user
        }
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error refreshing token: {str(e)}"
        )

@router.post("/logout")
async def logout(response: Response):
    """
    Logout a user by clearing their authentication cookies.

    Args:
        response: FastAPI Response object for clearing cookies

    Returns:
        Success message
    """
    # Clear the auth cookies
    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        path=COOKIE_PATH,
        domain=COOKIE_DOMAIN
    )

    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
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

    # Clear the auth cookies
    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        path=COOKIE_PATH,
        domain=COOKIE_DOMAIN
    )

    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        path=COOKIE_PATH,
        domain=COOKIE_DOMAIN
    )

    return result


