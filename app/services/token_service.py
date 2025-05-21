"""
Token management service for handling refresh tokens and token blacklisting.
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from fastapi import HTTPException, status
from supabase import create_client

from config.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Import connection manager
from app.utils.connection_manager import connection_manager

# Get Supabase client
supabase = connection_manager.get_supabase_client()

class TokenService:
    """Token management service for handling refresh tokens and token blacklisting."""

    def __init__(self):
        """Initialize the token service."""
        self.supabase = supabase

    async def create_refresh_token(self, user_id: str) -> str:
        """
        Create a new refresh token for a user.

        Args:
            user_id: User ID

        Returns:
            Refresh token
        """
        if not self.supabase:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Token service is not available"
            )

        try:
            # Generate a unique token
            token = str(uuid.uuid4())

            # Calculate expiration time (use timezone-aware datetime)
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

            # Create token data
            token_data = {
                "user_id": user_id,
                "token": token,
                "expires_at": expires_at.isoformat(),
                "created_at": now.isoformat(),
                "is_revoked": False
            }

            # Store the token in the database using service role to bypass RLS
            if settings.SUPABASE_SERVICE_KEY:
                try:
                    logger.info(f"Using service role to create refresh token for user: {user_id}")
                    service_supabase = create_client(
                        supabase_url=settings.SUPABASE_URL,
                        supabase_key=settings.SUPABASE_SERVICE_KEY
                    )
                    insert_response = service_supabase.table("refresh_tokens").insert(token_data).execute()
                    logger.info(f"Refresh token created with service role: {insert_response}")
                except Exception as e:
                    logger.error(f"Error creating refresh token with service key: {str(e)}")
                    # Fall back to regular key
                    insert_response = self.supabase.table("refresh_tokens").insert(token_data).execute()
                    logger.info(f"Refresh token created with regular key: {insert_response}")
            else:
                insert_response = self.supabase.table("refresh_tokens").insert(token_data).execute()
                logger.info(f"Refresh token created with regular key: {insert_response}")

            return token
        except Exception as e:
            logger.error(f"Error creating refresh token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating refresh token: {str(e)}"
            )

    async def get_token_details(self, token: str) -> Dict[str, Any]:
        """
        Get details about a refresh token.

        Args:
            token: Refresh token

        Returns:
            Token details
        """
        if not self.supabase:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Token service is not available"
            )

        try:
            # Use service role key if available to bypass RLS
            if settings.SUPABASE_SERVICE_KEY:
                try:
                    logger.info(f"Using service role to get token details for: {token[:10]}...")
                    service_supabase = create_client(
                        supabase_url=settings.SUPABASE_URL,
                        supabase_key=settings.SUPABASE_SERVICE_KEY
                    )
                    token_response = service_supabase.table("refresh_tokens").select("*").eq("token", token).execute()
                except Exception as service_error:
                    logger.error(f"Error using service role to get token details: {str(service_error)}")
                    # Fall back to regular key
                    token_response = self.supabase.table("refresh_tokens").select("*").eq("token", token).execute()
            else:
                # No service key available, use regular key
                token_response = self.supabase.table("refresh_tokens").select("*").eq("token", token).execute()

            logger.info(f"Token details response: {token_response}")

            if not token_response.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Token not found"
                )

            return token_response.data[0]
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Error getting token details: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting token details: {str(e)}"
            )

    async def validate_refresh_token(self, token: str) -> Dict[str, Any]:
        """
        Validate a refresh token.

        Args:
            token: Refresh token

        Returns:
            User ID associated with the token
        """
        if not self.supabase:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Token service is not available"
            )

        try:
            # Get the token from the database using service role to bypass RLS
            logger.info(f"Querying database for token: {token[:10]}...")

            # Use service role key if available to bypass RLS
            if settings.SUPABASE_SERVICE_KEY:
                try:
                    logger.info(f"Using service role to validate token: {token[:10]}...")
                    service_supabase = create_client(
                        supabase_url=settings.SUPABASE_URL,
                        supabase_key=settings.SUPABASE_SERVICE_KEY
                    )
                    token_response = service_supabase.table("refresh_tokens").select("*").eq("token", token).execute()
                except Exception as service_error:
                    logger.error(f"Error using service role to validate token: {str(service_error)}")
                    # Fall back to regular key
                    token_response = self.supabase.table("refresh_tokens").select("*").eq("token", token).execute()
            else:
                # No service key available, use regular key
                token_response = self.supabase.table("refresh_tokens").select("*").eq("token", token).execute()

            logger.info(f"Token query response: {token_response}")

            if not token_response.data:
                logger.warning(f"Token not found in database: {token[:10]}...")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )

            token_data = token_response.data[0]
            logger.info(f"Token data retrieved: {token_data}")

            # Check if the token is revoked
            if token_data.get("is_revoked", False):
                logger.warning(f"Token has been revoked: {token[:10]}...")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token has been revoked"
                )

            # Check if the token is expired
            try:
                # Parse the expiration time from the database
                expires_at = datetime.fromisoformat(token_data.get("expires_at"))

                # Make sure we're comparing timezone-aware datetimes
                now = datetime.now(expires_at.tzinfo) if expires_at.tzinfo else datetime.now()

                if expires_at < now:
                    logger.warning(f"Token has expired: {token[:10]}... Expired at: {expires_at}, Now: {now}")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Refresh token has expired"
                    )

                logger.info(f"Token is valid. Expires at: {expires_at}, Now: {now}")
            except ValueError as ve:
                logger.error(f"Error parsing datetime: {str(ve)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error validating token expiration: {str(ve)}"
                )

            # Return the user ID
            return {
                "user_id": token_data.get("user_id"),
                "token_id": token_data.get("id")
            }
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Error validating refresh token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error validating refresh token: {str(e)}"
            )

    async def revoke_refresh_token(self, token: str) -> None:
        """
        Revoke a refresh token.

        Args:
            token: Refresh token
        """
        if not self.supabase:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Token service is not available"
            )

        try:
            # Update data (use timezone-aware datetime)
            now = datetime.now(timezone.utc)
            update_data = {
                "is_revoked": True,
                "revoked_at": now.isoformat()
            }

            # Mark the token as revoked in the database using service role to bypass RLS
            if settings.SUPABASE_SERVICE_KEY:
                try:
                    logger.info(f"Using service role to revoke token: {token[:10]}...")
                    service_supabase = create_client(
                        supabase_url=settings.SUPABASE_URL,
                        supabase_key=settings.SUPABASE_SERVICE_KEY
                    )
                    revoke_response = service_supabase.table("refresh_tokens").update(update_data).eq("token", token).execute()
                    logger.info(f"Token revoked with service role: {revoke_response}")
                except Exception as e:
                    logger.error(f"Error revoking token with service key: {str(e)}")
                    # Fall back to regular key
                    revoke_response = self.supabase.table("refresh_tokens").update(update_data).eq("token", token).execute()
                    logger.info(f"Token revoked with regular key: {revoke_response}")
            else:
                revoke_response = self.supabase.table("refresh_tokens").update(update_data).eq("token", token).execute()
                logger.info(f"Token revoked with regular key: {revoke_response}")
        except Exception as e:
            logger.error(f"Error revoking refresh token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error revoking refresh token: {str(e)}"
            )

    async def revoke_all_user_tokens(self, user_id: str) -> None:
        """
        Revoke all refresh tokens for a user.

        Args:
            user_id: User ID
        """
        if not self.supabase:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Token service is not available"
            )

        try:
            # Mark all tokens for the user as revoked
            if settings.SUPABASE_SERVICE_KEY:
                try:
                    service_supabase = create_client(
                        supabase_url=settings.SUPABASE_URL,
                        supabase_key=settings.SUPABASE_SERVICE_KEY
                    )
                    service_supabase.table("refresh_tokens").update({
                        "is_revoked": True,
                        "revoked_at": datetime.now().isoformat()
                    }).eq("user_id", user_id).execute()
                except Exception:
                    # Fall back to regular key
                    self.supabase.table("refresh_tokens").update({
                        "is_revoked": True,
                        "revoked_at": datetime.now().isoformat()
                    }).eq("user_id", user_id).execute()
            else:
                self.supabase.table("refresh_tokens").update({
                    "is_revoked": True,
                    "revoked_at": datetime.now().isoformat()
                }).eq("user_id", user_id).execute()
        except Exception as e:
            logger.error(f"Error revoking all user tokens: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error revoking all user tokens: {str(e)}"
            )

# Initialize the token service
token_service = TokenService()
