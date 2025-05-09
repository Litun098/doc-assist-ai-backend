"""
Authentication utilities for the application.
"""
import logging
from typing import Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.utils import get_authorization_scheme_param

from app.services.auth_service import auth_service

# Configure logging
logger = logging.getLogger(__name__)

# Cookie name for authentication
AUTH_COOKIE_NAME = "auth_token"

# Custom security scheme that supports both cookies and bearer tokens
class CookieOrHeaderAuth:
    async def __call__(self, request: Request):
        # First try to get the token from the cookie
        token = request.cookies.get(AUTH_COOKIE_NAME)

        # If no cookie, try to get from Authorization header
        if not token:
            authorization = request.headers.get("Authorization")
            if authorization:
                scheme, token = get_authorization_scheme_param(authorization)
                if scheme.lower() != "bearer":
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid authentication scheme. Expected 'Bearer'",
                        headers={"WWW-Authenticate": "Bearer"},
                    )

        # If no token found in either place, raise an exception
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Return the token
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

# Initialize the security scheme
security = CookieOrHeaderAuth()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Validate JWT token and return user information.
    This is a wrapper around auth_service.get_current_user for easier imports.

    Args:
        credentials: HTTP Authorization credentials

    Returns:
        User information
    """
    return await auth_service.get_current_user(credentials)
