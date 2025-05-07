"""
Authentication service using Supabase.
"""
import logging
import pyotp
import qrcode
import io
import base64
from typing import Dict, Optional, Any, List
from fastapi import Depends, HTTPException, status, Request, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.utils import get_authorization_scheme_param
from jose import JWTError, jwt
from datetime import datetime, timedelta
from supabase import create_client, Client

from config.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Import connection manager
from app.utils.connection_manager import connection_manager

# Initialize Supabase client using connection manager
try:
    # Check if Supabase URL and key are set
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        logger.error("Supabase URL or key is not set in environment variables")
        supabase = None
    else:
        # Get Supabase client from connection manager
        try:
            logger.info(f"Attempting to connect to Supabase at {settings.SUPABASE_URL}")
            supabase = connection_manager.get_supabase_client("default")
            if supabase:
                logger.info(f"Successfully connected to Supabase at {settings.SUPABASE_URL}")
            else:
                logger.error("Failed to get Supabase client from connection manager")
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
                    # Try using service role key first to avoid RLS issues
                    if settings.SUPABASE_SERVICE_KEY:
                        try:
                            logger.info(f"Inserting user data using service role for: {user.user.id}")
                            service_supabase = create_client(
                                supabase_url=settings.SUPABASE_URL,
                                supabase_key=settings.SUPABASE_SERVICE_KEY
                            )
                            service_supabase.table("users").insert(user_data).execute()
                            logger.info(f"User data inserted successfully using service role for: {user.user.id}")
                        except Exception as service_error:
                            logger.error(f"Error inserting user data using service role: {str(service_error)}")
                            # Fall back to regular key
                            logger.info(f"Falling back to regular key for inserting user data for: {user.user.id}")
                            self.supabase.table("users").insert(user_data).execute()
                            logger.info(f"User data inserted successfully for: {user.user.id}")
                    else:
                        # No service key available, use regular key
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
                # Try using service role key first to avoid RLS issues
                if settings.SUPABASE_SERVICE_KEY:
                    try:
                        logger.info(f"Updating last login using service role for user ID: {user.user.id}")
                        service_supabase = create_client(
                            supabase_url=settings.SUPABASE_URL,
                            supabase_key=settings.SUPABASE_SERVICE_KEY
                        )
                        service_supabase.table("users").update({"last_login": datetime.now().isoformat()}).eq("id", user.user.id).execute()
                        logger.info(f"Last login updated successfully using service role for user ID: {user.user.id}")
                    except Exception as service_error:
                        logger.error(f"Error updating last login using service role: {str(service_error)}")
                        # Fall back to regular key
                        logger.info(f"Falling back to regular key for updating last login for user ID: {user.user.id}")
                        self.supabase.table("users").update({"last_login": datetime.now().isoformat()}).eq("id", user.user.id).execute()
                        logger.info(f"Last login updated successfully for user ID: {user.user.id}")
                else:
                    # No service key available, use regular key
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
                # Include full_name in user metadata
                auth_response = self.supabase.auth.sign_up({
                    "email": email,
                    "password": password,
                    "options": {
                        "data": {
                            "full_name": full_name
                        }
                    }
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
                # Try using service role key first to avoid RLS issues
                if settings.SUPABASE_SERVICE_KEY:
                    try:
                        logger.info(f"Attempting to insert user data using service role for user ID: {auth_response.user.id}")
                        service_supabase = connection_manager.get_supabase_client("service")
                        insert_response = service_supabase.table("users").insert(user_data).execute()
                        logger.info(f"User data inserted successfully using service role: {insert_response}")
                    except Exception as service_error:
                        logger.error(f"Error inserting user data using service role: {str(service_error)}")
                        # Fall back to regular key
                        logger.info(f"Falling back to regular key for inserting user data for user ID: {auth_response.user.id}")
                        insert_response = self.supabase.table("users").insert(user_data).execute()
                        logger.info(f"User data inserted successfully: {insert_response}")
                else:
                    # No service key available, use regular key
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
                # Try to get user metadata for full_name
                user_metadata = auth_response.user.user_metadata or {}
                full_name = user_metadata.get('full_name')

                user_data = {
                    "id": auth_response.user.id,
                    "email": email,
                    "full_name": full_name,  # Include full_name from metadata if available
                    "subscription_tier": "free",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "last_login": datetime.now().isoformat()
                }
                try:
                    # Try using service role key first to avoid RLS issues
                    if settings.SUPABASE_SERVICE_KEY:
                        try:
                            logger.info(f"Inserting user data using service role during login for user ID: {auth_response.user.id}")
                            service_supabase = create_client(
                                supabase_url=settings.SUPABASE_URL,
                                supabase_key=settings.SUPABASE_SERVICE_KEY
                            )
                            service_supabase.table("users").insert(user_data).execute()
                            logger.info(f"User data inserted successfully using service role during login for user ID: {auth_response.user.id}")
                        except Exception as service_error:
                            logger.error(f"Error inserting user data using service role during login: {str(service_error)}")
                            # Fall back to regular key
                            logger.info(f"Falling back to regular key for inserting user data during login for user ID: {auth_response.user.id}")
                            self.supabase.table("users").insert(user_data).execute()
                            logger.info(f"User data inserted successfully during login for user ID: {auth_response.user.id}")
                    else:
                        # No service key available, use regular key
                        self.supabase.table("users").insert(user_data).execute()
                except Exception as insert_error:
                    logger.error(f"Error inserting user data during login: {str(insert_error)}")
                    # Continue with login despite the error
                user_info = user_data
            else:
                user_info = user_response.data[0]
                # Update last login
                try:
                    # Try using service role key first to avoid RLS issues
                    if settings.SUPABASE_SERVICE_KEY:
                        try:
                            logger.info(f"Updating last login using service role during login for user ID: {auth_response.user.id}")
                            service_supabase = create_client(
                                supabase_url=settings.SUPABASE_URL,
                                supabase_key=settings.SUPABASE_SERVICE_KEY
                            )
                            service_supabase.table("users").update({"last_login": datetime.now().isoformat()}).eq("id", auth_response.user.id).execute()
                            logger.info(f"Last login updated successfully using service role during login for user ID: {auth_response.user.id}")
                        except Exception as service_error:
                            logger.error(f"Error updating last login using service role during login: {str(service_error)}")
                            # Fall back to regular key
                            logger.info(f"Falling back to regular key for updating last login during login for user ID: {auth_response.user.id}")
                            self.supabase.table("users").update({"last_login": datetime.now().isoformat()}).eq("id", auth_response.user.id).execute()
                            logger.info(f"Last login updated successfully during login for user ID: {auth_response.user.id}")
                    else:
                        # No service key available, use regular key
                        self.supabase.table("users").update({"last_login": datetime.now().isoformat()}).eq("id", auth_response.user.id).execute()
                except Exception as update_error:
                    logger.error(f"Error updating last login during login: {str(update_error)}")
                    # Continue with login despite the error

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

    async def update_profile(self, user_id: str, full_name: str, email: str) -> Dict[str, Any]:
        """
        Update user profile information.

        Args:
            user_id: ID of the user
            full_name: New full name
            email: New email address

        Returns:
            Updated user information
        """
        if not self.supabase:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is not available"
            )

        try:
            # Get current user data
            user_response = self.supabase.table("users").select("*").eq("id", user_id).execute()

            if not user_response.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            current_user = user_response.data[0]
            current_email = current_user.get("email")

            # Update user data in the database
            update_data = {
                "full_name": full_name,
                "updated_at": datetime.now().isoformat()
            }

            # Try using service role key first to avoid RLS issues
            if settings.SUPABASE_SERVICE_KEY:
                try:
                    logger.info(f"Updating user profile using service role for user ID: {user_id}")
                    service_supabase = create_client(
                        supabase_url=settings.SUPABASE_URL,
                        supabase_key=settings.SUPABASE_SERVICE_KEY
                    )
                    service_supabase.table("users").update(update_data).eq("id", user_id).execute()
                    logger.info(f"User profile updated successfully using service role for user ID: {user_id}")
                except Exception as service_error:
                    logger.error(f"Error updating user profile using service role: {str(service_error)}")
                    # Fall back to regular key
                    logger.info(f"Falling back to regular key for updating user profile for user ID: {user_id}")
                    self.supabase.table("users").update(update_data).eq("id", user_id).execute()
                    logger.info(f"User profile updated successfully for user ID: {user_id}")
            else:
                # No service key available, use regular key
                self.supabase.table("users").update(update_data).eq("id", user_id).execute()

            # If email has changed, update it in Supabase Auth
            if email != current_email:
                # This requires admin privileges, so we need to use the service role key
                if settings.SUPABASE_SERVICE_KEY:
                    try:
                        logger.info(f"Updating user email using service role for user ID: {user_id}")
                        service_supabase = create_client(
                            supabase_url=settings.SUPABASE_URL,
                            supabase_key=settings.SUPABASE_SERVICE_KEY
                        )
                        # Update email in auth.users table
                        service_supabase.auth.admin.update_user_by_id(
                            user_id,
                            {"email": email}
                        )

                        # Also update email in our users table
                        service_supabase.table("users").update({"email": email}).eq("id", user_id).execute()
                        logger.info(f"User email updated successfully using service role for user ID: {user_id}")
                    except Exception as email_error:
                        logger.error(f"Error updating user email: {str(email_error)}")
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Error updating email: {str(email_error)}"
                        )
                else:
                    logger.error("Cannot update email without service role key")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Email update requires admin privileges"
                    )

            # Get updated user data
            updated_user_response = self.supabase.table("users").select("*").eq("id", user_id).execute()

            if not updated_user_response.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found after update"
                )

            updated_user = updated_user_response.data[0]

            return {
                "id": updated_user["id"],
                "email": updated_user["email"],
                "full_name": updated_user["full_name"],
                "subscription_tier": updated_user["subscription_tier"],
                "updated_at": updated_user["updated_at"]
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Profile update error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Profile update error: {str(e)}"
            )

    async def change_password(self, user_id: str, current_password: str, new_password: str) -> Dict[str, Any]:
        """
        Change user password.

        Args:
            user_id: ID of the user
            current_password: Current password
            new_password: New password

        Returns:
            Success message
        """
        if not self.supabase:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is not available"
            )

        try:
            # Get user email
            user_response = self.supabase.table("users").select("email").eq("id", user_id).execute()

            if not user_response.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            email = user_response.data[0]["email"]

            # Verify current password by attempting to sign in
            try:
                self.supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": current_password
                })
            except Exception as auth_error:
                logger.error(f"Current password verification failed: {str(auth_error)}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Current password is incorrect"
                )

            # Update password
            try:
                self.supabase.auth.update_user(
                    {"password": new_password}
                )
                logger.info(f"Password updated successfully for user ID: {user_id}")
            except Exception as update_error:
                logger.error(f"Error updating password: {str(update_error)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error updating password: {str(update_error)}"
                )

            return {
                "status": "success",
                "message": "Password updated successfully"
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Password change error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Password change error: {str(e)}"
            )

    async def delete_account(self, user_id: str, password: str) -> Dict[str, Any]:
        """
        Delete user account.

        Args:
            user_id: ID of the user
            password: User's password for verification

        Returns:
            Success message
        """
        if not self.supabase:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is not available"
            )

        try:
            # Get user email
            user_response = self.supabase.table("users").select("email").eq("id", user_id).execute()

            if not user_response.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            email = user_response.data[0]["email"]

            # Verify password by attempting to sign in
            try:
                self.supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": password
                })
            except Exception as auth_error:
                logger.error(f"Password verification failed during account deletion: {str(auth_error)}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Password is incorrect"
                )

            # Delete user account
            if settings.SUPABASE_SERVICE_KEY:
                try:
                    logger.info(f"Deleting user account using service role for user ID: {user_id}")
                    service_supabase = create_client(
                        supabase_url=settings.SUPABASE_URL,
                        supabase_key=settings.SUPABASE_SERVICE_KEY
                    )

                    # Delete user from our users table first
                    service_supabase.table("users").delete().eq("id", user_id).execute()

                    # Delete user from auth.users table
                    service_supabase.auth.admin.delete_user(user_id)

                    logger.info(f"User account deleted successfully for user ID: {user_id}")
                except Exception as delete_error:
                    logger.error(f"Error deleting user account: {str(delete_error)}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Error deleting account: {str(delete_error)}"
                    )
            else:
                logger.error("Cannot delete account without service role key")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Account deletion requires admin privileges"
                )

            return {
                "status": "success",
                "message": "Account deleted successfully"
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Account deletion error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Account deletion error: {str(e)}"
            )

    async def enable_2fa(self, user_id: str) -> Dict[str, Any]:
        """
        Enable two-factor authentication for a user.

        Args:
            user_id: ID of the user

        Returns:
            2FA setup information (QR code, backup codes)
        """
        if not self.supabase:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is not available"
            )

        try:
            # Check if user exists
            user_response = self.supabase.table("users").select("*").eq("id", user_id).execute()

            if not user_response.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            # Generate a secret key for 2FA
            secret = pyotp.random_base32()

            # Generate a QR code
            totp = pyotp.TOTP(secret)
            user_email = user_response.data[0].get("email", "user")
            provisioning_uri = totp.provisioning_uri(name=user_email, issuer_name="AnyDocAI")

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(provisioning_uri)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            # Convert QR code to base64 string
            buffered = io.BytesIO()
            img.save(buffered)
            qr_code_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

            # Generate backup codes
            backup_codes = []
            for _ in range(10):
                backup_codes.append(pyotp.random_base32(length=8))

            # Store the secret and backup codes in the database
            # We'll store them in a new table called user_2fa
            try:
                # Check if 2FA is already enabled
                twofa_response = self.supabase.table("user_2fa").select("*").eq("user_id", user_id).execute()

                if twofa_response.data:
                    # Update existing record
                    if settings.SUPABASE_SERVICE_KEY:
                        try:
                            service_supabase = create_client(
                                supabase_url=settings.SUPABASE_URL,
                                supabase_key=settings.SUPABASE_SERVICE_KEY
                            )
                            service_supabase.table("user_2fa").update({
                                "secret": secret,
                                "backup_codes": backup_codes,
                                "enabled": False,  # Not yet verified
                                "updated_at": datetime.now().isoformat()
                            }).eq("user_id", user_id).execute()
                        except Exception:
                            self.supabase.table("user_2fa").update({
                                "secret": secret,
                                "backup_codes": backup_codes,
                                "enabled": False,  # Not yet verified
                                "updated_at": datetime.now().isoformat()
                            }).eq("user_id", user_id).execute()
                    else:
                        self.supabase.table("user_2fa").update({
                            "secret": secret,
                            "backup_codes": backup_codes,
                            "enabled": False,  # Not yet verified
                            "updated_at": datetime.now().isoformat()
                        }).eq("user_id", user_id).execute()
                else:
                    # Create new record
                    if settings.SUPABASE_SERVICE_KEY:
                        try:
                            service_supabase = create_client(
                                supabase_url=settings.SUPABASE_URL,
                                supabase_key=settings.SUPABASE_SERVICE_KEY
                            )
                            service_supabase.table("user_2fa").insert({
                                "user_id": user_id,
                                "secret": secret,
                                "backup_codes": backup_codes,
                                "enabled": False,  # Not yet verified
                                "created_at": datetime.now().isoformat(),
                                "updated_at": datetime.now().isoformat()
                            }).execute()
                        except Exception:
                            self.supabase.table("user_2fa").insert({
                                "user_id": user_id,
                                "secret": secret,
                                "backup_codes": backup_codes,
                                "enabled": False,  # Not yet verified
                                "created_at": datetime.now().isoformat(),
                                "updated_at": datetime.now().isoformat()
                            }).execute()
                    else:
                        self.supabase.table("user_2fa").insert({
                            "user_id": user_id,
                            "secret": secret,
                            "backup_codes": backup_codes,
                            "enabled": False,  # Not yet verified
                            "created_at": datetime.now().isoformat(),
                            "updated_at": datetime.now().isoformat()
                        }).execute()
            except Exception as db_error:
                logger.error(f"Error storing 2FA data: {str(db_error)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error storing 2FA data: {str(db_error)}"
                )

            return {
                "qr_code": f"data:image/png;base64,{qr_code_base64}",
                "secret": secret,
                "backup_codes": backup_codes,
                "message": "Scan the QR code with your authenticator app and verify with a code to complete setup"
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"2FA setup error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"2FA setup error: {str(e)}"
            )

    async def verify_2fa(self, user_id: str, code: str) -> Dict[str, Any]:
        """
        Verify and enable two-factor authentication.

        Args:
            user_id: ID of the user
            code: Verification code from authenticator app

        Returns:
            Success message
        """
        if not self.supabase:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is not available"
            )

        try:
            # Get 2FA data for the user
            twofa_response = self.supabase.table("user_2fa").select("*").eq("user_id", user_id).execute()

            if not twofa_response.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="2FA setup not found for this user"
                )

            twofa_data = twofa_response.data[0]
            secret = twofa_data.get("secret")

            if not secret:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid 2FA setup"
                )

            # Verify the code
            totp = pyotp.TOTP(secret)
            if not totp.verify(code):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid verification code"
                )

            # Enable 2FA for the user
            if settings.SUPABASE_SERVICE_KEY:
                try:
                    service_supabase = create_client(
                        supabase_url=settings.SUPABASE_URL,
                        supabase_key=settings.SUPABASE_SERVICE_KEY
                    )
                    service_supabase.table("user_2fa").update({
                        "enabled": True,
                        "updated_at": datetime.now().isoformat()
                    }).eq("user_id", user_id).execute()
                except Exception:
                    self.supabase.table("user_2fa").update({
                        "enabled": True,
                        "updated_at": datetime.now().isoformat()
                    }).eq("user_id", user_id).execute()
            else:
                self.supabase.table("user_2fa").update({
                    "enabled": True,
                    "updated_at": datetime.now().isoformat()
                }).eq("user_id", user_id).execute()

            # Also update the user record to indicate 2FA is enabled
            if settings.SUPABASE_SERVICE_KEY:
                try:
                    service_supabase = create_client(
                        supabase_url=settings.SUPABASE_URL,
                        supabase_key=settings.SUPABASE_SERVICE_KEY
                    )
                    service_supabase.table("users").update({
                        "has_2fa": True,
                        "updated_at": datetime.now().isoformat()
                    }).eq("id", user_id).execute()
                except Exception:
                    self.supabase.table("users").update({
                        "has_2fa": True,
                        "updated_at": datetime.now().isoformat()
                    }).eq("id", user_id).execute()
            else:
                self.supabase.table("users").update({
                    "has_2fa": True,
                    "updated_at": datetime.now().isoformat()
                }).eq("id", user_id).execute()

            return {
                "status": "success",
                "message": "Two-factor authentication enabled successfully"
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"2FA verification error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"2FA verification error: {str(e)}"
            )

    async def disable_2fa(self, user_id: str, code: str) -> Dict[str, Any]:
        """
        Disable two-factor authentication.

        Args:
            user_id: ID of the user
            code: Verification code from authenticator app

        Returns:
            Success message
        """
        if not self.supabase:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is not available"
            )

        try:
            # Get 2FA data for the user
            twofa_response = self.supabase.table("user_2fa").select("*").eq("user_id", user_id).execute()

            if not twofa_response.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="2FA not enabled for this user"
                )

            twofa_data = twofa_response.data[0]
            secret = twofa_data.get("secret")
            backup_codes = twofa_data.get("backup_codes", [])

            if not secret:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid 2FA setup"
                )

            # Verify the code (either TOTP or backup code)
            totp = pyotp.TOTP(secret)
            is_valid = totp.verify(code) or code in backup_codes

            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid verification code"
                )

            # If it's a backup code, remove it from the list
            if code in backup_codes:
                backup_codes.remove(code)

                # Update backup codes in the database
                if settings.SUPABASE_SERVICE_KEY:
                    try:
                        service_supabase = create_client(
                            supabase_url=settings.SUPABASE_URL,
                            supabase_key=settings.SUPABASE_SERVICE_KEY
                        )
                        service_supabase.table("user_2fa").update({
                            "backup_codes": backup_codes,
                            "updated_at": datetime.now().isoformat()
                        }).eq("user_id", user_id).execute()
                    except Exception:
                        self.supabase.table("user_2fa").update({
                            "backup_codes": backup_codes,
                            "updated_at": datetime.now().isoformat()
                        }).eq("user_id", user_id).execute()
                else:
                    self.supabase.table("user_2fa").update({
                        "backup_codes": backup_codes,
                        "updated_at": datetime.now().isoformat()
                    }).eq("user_id", user_id).execute()

            # Delete 2FA data for the user
            if settings.SUPABASE_SERVICE_KEY:
                try:
                    service_supabase = create_client(
                        supabase_url=settings.SUPABASE_URL,
                        supabase_key=settings.SUPABASE_SERVICE_KEY
                    )
                    service_supabase.table("user_2fa").delete().eq("user_id", user_id).execute()
                except Exception:
                    self.supabase.table("user_2fa").delete().eq("user_id", user_id).execute()
            else:
                self.supabase.table("user_2fa").delete().eq("user_id", user_id).execute()

            # Update the user record to indicate 2FA is disabled
            if settings.SUPABASE_SERVICE_KEY:
                try:
                    service_supabase = create_client(
                        supabase_url=settings.SUPABASE_URL,
                        supabase_key=settings.SUPABASE_SERVICE_KEY
                    )
                    service_supabase.table("users").update({
                        "has_2fa": False,
                        "updated_at": datetime.now().isoformat()
                    }).eq("id", user_id).execute()
                except Exception:
                    self.supabase.table("users").update({
                        "has_2fa": False,
                        "updated_at": datetime.now().isoformat()
                    }).eq("id", user_id).execute()
            else:
                self.supabase.table("users").update({
                    "has_2fa": False,
                    "updated_at": datetime.now().isoformat()
                }).eq("id", user_id).execute()

            return {
                "status": "success",
                "message": "Two-factor authentication disabled successfully"
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"2FA disabling error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"2FA disabling error: {str(e)}"
            )


# Create a singleton instance
auth_service = AuthService()
