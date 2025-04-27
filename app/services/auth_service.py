"""
Authentication service using Supabase.
"""
import logging
from typing import Dict, Optional, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from supabase import create_client, Client

from config.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Supabase client
try:
    # Create Supabase client without proxy parameter
    supabase: Client = create_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_KEY
    )
    logger.info(f"Connected to Supabase at {settings.SUPABASE_URL}")
except Exception as e:
    logger.error(f"Error connecting to Supabase: {str(e)}")
    supabase = None

# Security scheme
security = HTTPBearer()

class AuthService:
    """Authentication service using Supabase."""

    def __init__(self):
        """Initialize the authentication service."""
        self.supabase = supabase

    async def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
        """
        Validate JWT token and return user information.

        Args:
            credentials: HTTP Authorization credentials

        Returns:
            User information
        """
        if not self.supabase:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is not available"
            )

        try:
            # Get the token
            token = credentials.credentials

            # Verify the token with Supabase
            user = self.supabase.auth.get_user(token)

            if not user or not user.user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Get user details from the database
            user_response = self.supabase.table("users").select("*").eq("id", user.user.id).execute()

            if not user_response.data:
                # User exists in auth but not in our users table, create the record
                user_data = {
                    "id": user.user.id,
                    "email": user.user.email,
                    "last_login": datetime.now().isoformat()
                }
                self.supabase.table("users").insert(user_data).execute()
                return user_data

            # Update last login
            self.supabase.table("users").update({"last_login": datetime.now().isoformat()}).eq("id", user.user.id).execute()

            return user_response.data[0]

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def register_user(self, email: str, password: str, full_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Register a new user.

        Args:
            email: User email
            password: User password
            full_name: User's full name (optional)

        Returns:
            User information and access token
        """
        if not self.supabase:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is not available"
            )

        try:
            # Register user with Supabase Auth
            auth_response = self.supabase.auth.sign_up({
                "email": email,
                "password": password
            })

            if not auth_response.user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User registration failed"
                )

            # Create user record in our users table
            user_data = {
                "id": auth_response.user.id,
                "email": email,
                "full_name": full_name,
                "subscription_tier": "free",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "last_login": datetime.now().isoformat()
            }

            self.supabase.table("users").insert(user_data).execute()

            return {
                "user": {
                    "id": auth_response.user.id,
                    "email": email,
                    "full_name": full_name,
                    "subscription_tier": "free"
                },
                "access_token": auth_response.session.access_token,
                "token_type": "bearer"
            }

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Registration error: {str(e)}"
            )

    async def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """
        Login a user.

        Args:
            email: User email
            password: User password

        Returns:
            User information and access token
        """
        if not self.supabase:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is not available"
            )

        try:
            # Login user with Supabase Auth
            auth_response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if not auth_response.user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )

            # Get user details from the database
            user_response = self.supabase.table("users").select("*").eq("id", auth_response.user.id).execute()

            if not user_response.data:
                # User exists in auth but not in our users table, create the record
                user_data = {
                    "id": auth_response.user.id,
                    "email": email,
                    "subscription_tier": "free",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "last_login": datetime.now().isoformat()
                }
                self.supabase.table("users").insert(user_data).execute()
                user_info = user_data
            else:
                user_info = user_response.data[0]
                # Update last login
                self.supabase.table("users").update({"last_login": datetime.now().isoformat()}).eq("id", auth_response.user.id).execute()

            return {
                "user": {
                    "id": auth_response.user.id,
                    "email": email,
                    "full_name": user_info.get("full_name"),
                    "subscription_tier": user_info.get("subscription_tier", "free")
                },
                "access_token": auth_response.session.access_token,
                "token_type": "bearer"
            }

        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Login error: {str(e)}"
            )

# Create a singleton instance
auth_service = AuthService()
