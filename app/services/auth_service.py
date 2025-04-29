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
    # Check if Supabase URL and key are set
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        logger.error("Supabase URL or key is not set in environment variables")
        supabase = None
    else:
        # Create Supabase client with detailed error handling
        try:
            logger.info(f"Attempting to connect to Supabase at {settings.SUPABASE_URL}")
            supabase: Client = create_client(
                supabase_url=settings.SUPABASE_URL,
                supabase_key=settings.SUPABASE_KEY
            )
            logger.info(f"Successfully connected to Supabase at {settings.SUPABASE_URL}")
        except Exception as e:
            import traceback
            logger.error(f"Error connecting to Supabase: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            supabase = None
except Exception as e:
    import traceback
    logger.error(f"Unexpected error in Supabase initialization: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
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
        logger.info("Authenticating user with credentials")

        if not self.supabase:
            logger.error("Authentication service is not available")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is not available"
            )

        try:
            # Get the token
            token = credentials.credentials
            logger.info(f"Token received: {token[:10]}...")

            # Verify the token with Supabase
            logger.info("Verifying token with Supabase")
            user = self.supabase.auth.get_user(token)

            if not user or not user.user:
                logger.error("Invalid user or user.user is None")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            logger.info(f"Token verified for user ID: {user.user.id}")

            # Get user details from the database
            logger.info(f"Fetching user data from database for user ID: {user.user.id}")
            user_response = self.supabase.table("users").select("*").eq("id", user.user.id).execute()

            if not user_response.data:
                logger.info(f"User not found in database, creating record for: {user.user.id}")
                # User exists in auth but not in our users table, create the record
                user_data = {
                    "id": user.user.id,
                    "email": user.user.email,
                    "subscription_tier": "free",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "last_login": datetime.now().isoformat()
                }
                try:
                    logger.info(f"Inserting user data into database for: {user.user.id}")
                    self.supabase.table("users").insert(user_data).execute()
                    logger.info(f"User data inserted successfully for: {user.user.id}")
                except Exception as insert_error:
                    import traceback
                    logger.error(f"Error inserting user data during authentication: {str(insert_error)}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    logger.info(f"Continuing with authentication despite the error for: {user.user.id}")
                    # Continue with authentication despite the error
                return user_data

            # Update last login
            logger.info(f"Updating last login for user ID: {user.user.id}")
            try:
                self.supabase.table("users").update({"last_login": datetime.now().isoformat()}).eq("id", user.user.id).execute()
                logger.info(f"Last login updated successfully for user ID: {user.user.id}")
            except Exception as update_error:
                logger.error(f"Error updating last login: {str(update_error)}")
                # Continue with authentication despite the error

            return user_response.data[0]

        except Exception as e:
            import traceback
            logger.error(f"Authentication error: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")

            # Check if the token is in the correct format
            if 'token' in locals() and len(token.split('.')) != 3:
                logger.error(f"Invalid token format: {token[:10]}...")

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
            logger.info(f"Attempting to register user with email: {email}")
            try:
                auth_response = self.supabase.auth.sign_up({
                    "email": email,
                    "password": password
                })

                logger.info(f"User registration successful for email: {email}")

                if not auth_response.user:
                    logger.error("Auth response user is None")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="User registration failed - no user in response"
                    )

                logger.info(f"User ID from auth response: {auth_response.user.id}")
            except Exception as auth_error:
                import traceback
                logger.error(f"Error during auth.sign_up: {str(auth_error)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Authentication error: {str(auth_error)}"
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

            try:
                # Try to insert the user data
                logger.info(f"Attempting to insert user data into users table for user ID: {auth_response.user.id}")
                insert_response = self.supabase.table("users").insert(user_data).execute()
                logger.info(f"User data inserted successfully: {insert_response}")
            except Exception as insert_error:
                import traceback
                logger.error(f"Error inserting user data: {str(insert_error)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                # If the insert fails due to RLS, we'll continue anyway
                # The user is already created in the auth system
                logger.info("Continuing with user registration despite database insert error")

            # Check if session exists in auth_response
            if not hasattr(auth_response, 'session') or not auth_response.session:
                logger.warning("No session in auth_response, attempting to sign in")

                # Try to sign in immediately after registration
                try:
                    # Some Supabase configurations allow immediate sign-in without email verification
                    login_response = self.supabase.auth.sign_in_with_password({
                        "email": email,
                        "password": password
                    })

                    if login_response and hasattr(login_response, 'session') and login_response.session:
                        logger.info("Successfully signed in after registration")
                        return {
                            "user": {
                                "id": auth_response.user.id,
                                "email": email,
                                "full_name": full_name,
                                "subscription_tier": "free"
                            },
                            "access_token": login_response.session.access_token,
                            "token_type": "bearer"
                        }
                except Exception as login_error:
                    logger.warning(f"Could not sign in after registration: {str(login_error)}")

                # If sign-in fails, return a message about email verification
                return {
                    "user": {
                        "id": auth_response.user.id,
                        "email": email,
                        "full_name": full_name,
                        "subscription_tier": "free"
                    },
                    "message": "User registered successfully. Please verify your email to login.",
                    "requires_verification": True
                }

            logger.info("Registration completed successfully with session")
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

        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            import traceback
            logger.error(f"Unexpected registration error: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
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
                try:
                    self.supabase.table("users").insert(user_data).execute()
                except Exception as insert_error:
                    logger.error(f"Error inserting user data during login: {str(insert_error)}")
                    # Continue with login despite the error
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
