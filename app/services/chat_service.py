"""
Chat service for managing chat sessions and messages with Supabase.
"""
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from supabase import create_client, Client

from app.services.rag_service import rag_service
from app.services.agent_service import agent_service
from app.utils.s3_storage import s3_storage
from config.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Import connection manager
from app.utils.connection_manager import connection_manager

# Initialize Supabase client using connection manager
try:
    # Get Supabase client from connection manager
    supabase = connection_manager.get_supabase_client("default")
    if supabase:
        logger.info(f"Connected to Supabase at {settings.SUPABASE_URL}")
    else:
        logger.error("Failed to get Supabase client from connection manager")
except Exception as e:
    logger.error(f"Error connecting to Supabase: {str(e)}")
    supabase = None

class ChatService:
    """Chat service for managing chat sessions and messages with Supabase."""

    def __init__(self):
        """Initialize the chat service."""
        self.supabase = supabase
        self.rag_service = rag_service
        self.agent_service = agent_service

    async def create_session(self, user_id: str, name: str, document_ids: List[str] = None) -> Dict[str, Any]:
        """
        Create a new chat session.

        Args:
            user_id: ID of the user
            name: Name of the session
            document_ids: List of document IDs to associate with the session (optional)

        Returns:
            Session information
        """
        try:
            # Create session ID
            session_id = str(uuid.uuid4())

            # Initialize document_ids if None
            if document_ids is None:
                document_ids = []

            # Create session in Supabase if available
            if self.supabase:
                session_data = {
                    "id": session_id,
                    "user_id": user_id,
                    "name": name,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "last_message_at": datetime.now().isoformat()
                }

                # Try using service role key first to avoid RLS issues
                if settings.SUPABASE_SERVICE_KEY:
                    try:
                        logger.info(f"Creating chat session using service role for user ID: {user_id}")
                        service_supabase = create_client(
                            supabase_url=settings.SUPABASE_URL,
                            supabase_key=settings.SUPABASE_SERVICE_KEY
                        )
                        service_supabase.table("chat_sessions").insert(session_data).execute()
                        logger.info(f"Chat session created successfully using service role for user ID: {user_id}")

                        # Associate documents with session using service role (if any)
                        if document_ids and isinstance(document_ids, list) and len(document_ids) > 0:
                            # Validate document IDs to ensure they're valid UUIDs
                            valid_doc_ids = []
                            for doc_id in document_ids:
                                try:
                                    # Validate UUID format
                                    uuid_obj = uuid.UUID(doc_id)
                                    valid_doc_ids.append(str(uuid_obj))
                                except (ValueError, TypeError):
                                    logger.warning(f"Invalid document ID format: {doc_id}, skipping")

                            # Insert valid document associations
                            for doc_id in valid_doc_ids:
                                try:
                                    service_supabase.table("session_documents").insert({
                                        "session_id": session_id,
                                        "document_id": doc_id
                                    }).execute()
                                except Exception as doc_error:
                                    logger.error(f"Error associating document {doc_id} with session: {str(doc_error)}")

                            if valid_doc_ids:
                                logger.info(f"Documents associated with session successfully using service role")
                    except Exception as service_error:
                        logger.error(f"Error creating chat session using service role: {str(service_error)}")
                        # Fall back to regular key
                        logger.info(f"Falling back to regular key for creating chat session for user ID: {user_id}")
                        self.supabase.table("chat_sessions").insert(session_data).execute()
                        logger.info(f"Chat session created successfully for user ID: {user_id}")

                        # Associate documents with session (if any)
                        if document_ids and isinstance(document_ids, list) and len(document_ids) > 0:
                            # Validate document IDs to ensure they're valid UUIDs
                            valid_doc_ids = []
                            for doc_id in document_ids:
                                try:
                                    # Validate UUID format
                                    uuid_obj = uuid.UUID(doc_id)
                                    valid_doc_ids.append(str(uuid_obj))
                                except (ValueError, TypeError):
                                    logger.warning(f"Invalid document ID format: {doc_id}, skipping")

                            # Insert valid document associations
                            for doc_id in valid_doc_ids:
                                try:
                                    self.supabase.table("session_documents").insert({
                                        "session_id": session_id,
                                        "document_id": doc_id
                                    }).execute()
                                except Exception as doc_error:
                                    logger.error(f"Error associating document {doc_id} with session: {str(doc_error)}")

                            if valid_doc_ids:
                                logger.info(f"Documents associated with session successfully")
                else:
                    # No service key available, use regular key
                    self.supabase.table("chat_sessions").insert(session_data).execute()

                    # Associate documents with session (if any)
                    if document_ids and isinstance(document_ids, list) and len(document_ids) > 0:
                        # Validate document IDs to ensure they're valid UUIDs
                        valid_doc_ids = []
                        for doc_id in document_ids:
                            try:
                                # Validate UUID format
                                uuid_obj = uuid.UUID(doc_id)
                                valid_doc_ids.append(str(uuid_obj))
                            except (ValueError, TypeError):
                                logger.warning(f"Invalid document ID format: {doc_id}, skipping")

                        # Insert valid document associations
                        for doc_id in valid_doc_ids:
                            try:
                                self.supabase.table("session_documents").insert({
                                    "session_id": session_id,
                                    "document_id": doc_id
                                }).execute()
                            except Exception as doc_error:
                                logger.error(f"Error associating document {doc_id} with session: {str(doc_error)}")

            return {
                "session_id": session_id,
                "name": name,
                "document_ids": document_ids,
                "created_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error creating chat session: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error creating chat session: {str(e)}"
            )

    async def list_sessions(self, user_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        List all chat sessions for a user.

        Args:
            user_id: ID of the user

        Returns:
            List of chat sessions
        """
        try:
            sessions = []

            # Get sessions from Supabase if available
            if self.supabase:
                try:
                    # Try using service role key first to avoid RLS issues
                    if settings.SUPABASE_SERVICE_KEY:
                        try:
                            logger.info(f"Listing chat sessions using service role for user ID: {user_id}")
                            service_supabase = create_client(
                                supabase_url=settings.SUPABASE_URL,
                                supabase_key=settings.SUPABASE_SERVICE_KEY
                            )
                            response = service_supabase.table("chat_sessions").select("*").eq("user_id", user_id).order("last_message_at", desc=True).execute()
                            logger.info(f"Chat sessions listed successfully using service role for user ID: {user_id}")

                            for session in response.data:
                                # Get associated documents using service role
                                doc_response = service_supabase.table("session_documents").select("document_id").eq("session_id", session["id"]).execute()
                                document_ids = [doc["document_id"] for doc in doc_response.data]

                                sessions.append({
                                    "session_id": session["id"],
                                    "name": session["name"],
                                    "created_at": session["created_at"],
                                    "last_message_at": session["last_message_at"],
                                    "document_ids": document_ids
                                })
                        except Exception as service_error:
                            logger.error(f"Error listing chat sessions using service role: {str(service_error)}")
                            # Fall back to regular key
                            logger.info(f"Falling back to regular key for listing chat sessions for user ID: {user_id}")
                            response = self.supabase.table("chat_sessions").select("*").eq("user_id", user_id).order("last_message_at", desc=True).execute()
                            logger.info(f"Chat sessions listed successfully for user ID: {user_id}")

                            for session in response.data:
                                # Get associated documents
                                doc_response = self.supabase.table("session_documents").select("document_id").eq("session_id", session["id"]).execute()
                                document_ids = [doc["document_id"] for doc in doc_response.data]

                                sessions.append({
                                    "session_id": session["id"],
                                    "name": session["name"],
                                    "created_at": session["created_at"],
                                    "last_message_at": session["last_message_at"],
                                    "document_ids": document_ids
                                })
                    else:
                        # No service key available, use regular key
                        response = self.supabase.table("chat_sessions").select("*").eq("user_id", user_id).order("last_message_at", desc=True).execute()

                        for session in response.data:
                            # Get associated documents
                            doc_response = self.supabase.table("session_documents").select("document_id").eq("session_id", session["id"]).execute()
                            document_ids = [doc["document_id"] for doc in doc_response.data]

                            sessions.append({
                                "session_id": session["id"],
                                "name": session["name"],
                                "created_at": session["created_at"],
                                "last_message_at": session["last_message_at"],
                                "document_ids": document_ids
                            })
                except Exception as list_error:
                    logger.error(f"Error listing chat sessions: {str(list_error)}")
                    # Continue with empty sessions list

            return {"sessions": sessions}

        except Exception as e:
            logger.error(f"Error listing chat sessions: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error listing chat sessions: {str(e)}"
            )

    async def add_documents_to_session(self, session_id: str, user_id: str, document_ids: List[str]) -> Dict[str, Any]:
        """
        Add documents to an existing chat session.

        Args:
            session_id: ID of the session
            user_id: ID of the user
            document_ids: List of document IDs to add to the session

        Returns:
            Updated session information
        """
        try:
            # Check if session exists and belongs to user
            if self.supabase:
                # Try using service role key first to avoid RLS issues
                if settings.SUPABASE_SERVICE_KEY:
                    try:
                        logger.info(f"Checking session using service role for user ID: {user_id}")
                        service_supabase = create_client(
                            supabase_url=settings.SUPABASE_URL,
                            supabase_key=settings.SUPABASE_SERVICE_KEY
                        )
                        session_response = service_supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()
                        logger.info(f"Session checked successfully using service role")
                    except Exception as service_error:
                        logger.error(f"Error checking session using service role: {str(service_error)}")
                        # Fall back to regular key
                        logger.info(f"Falling back to regular key for checking session")
                        session_response = self.supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()
                else:
                    # No service key available, use regular key
                    session_response = self.supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()

                if not session_response.data:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Chat session with ID {session_id} not found or does not belong to user"
                    )

                # Get existing document IDs for this session
                if settings.SUPABASE_SERVICE_KEY:
                    try:
                        doc_response = service_supabase.table("session_documents").select("document_id").eq("session_id", session_id).execute()
                    except Exception:
                        doc_response = self.supabase.table("session_documents").select("document_id").eq("session_id", session_id).execute()
                else:
                    doc_response = self.supabase.table("session_documents").select("document_id").eq("session_id", session_id).execute()

                existing_doc_ids = [doc["document_id"] for doc in doc_response.data]

                # Add new documents to session
                added_doc_ids = []
                for doc_id in document_ids:
                    # Skip if document is already associated with this session
                    if doc_id in existing_doc_ids:
                        continue

                    # Add document to session
                    if settings.SUPABASE_SERVICE_KEY:
                        try:
                            service_supabase.table("session_documents").insert({
                                "session_id": session_id,
                                "document_id": doc_id
                            }).execute()
                        except Exception:
                            self.supabase.table("session_documents").insert({
                                "session_id": session_id,
                                "document_id": doc_id
                            }).execute()
                    else:
                        self.supabase.table("session_documents").insert({
                            "session_id": session_id,
                            "document_id": doc_id
                        }).execute()

                    added_doc_ids.append(doc_id)

                # Update session last updated time
                if settings.SUPABASE_SERVICE_KEY:
                    try:
                        service_supabase.table("chat_sessions").update({
                            "updated_at": datetime.now().isoformat()
                        }).eq("id", session_id).execute()
                    except Exception:
                        self.supabase.table("chat_sessions").update({
                            "updated_at": datetime.now().isoformat()
                        }).eq("id", session_id).execute()
                else:
                    self.supabase.table("chat_sessions").update({
                        "updated_at": datetime.now().isoformat()
                    }).eq("id", session_id).execute()

                # Get all document IDs for this session after adding new ones
                all_doc_ids = existing_doc_ids + added_doc_ids

                return {
                    "session_id": session_id,
                    "document_ids": all_doc_ids,
                    "added_document_ids": added_doc_ids,
                    "updated_at": datetime.now().isoformat()
                }

            raise HTTPException(
                status_code=500,
                detail="Database connection not available"
            )

        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Error adding documents to chat session: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error adding documents to chat session: {str(e)}"
            )

    async def remove_document_from_session(self, session_id: str, user_id: str, document_id: str) -> Dict[str, Any]:
        """
        Remove a document from a chat session.

        Args:
            session_id: ID of the session
            user_id: ID of the user
            document_id: ID of the document to remove

        Returns:
            Updated session information
        """
        try:
            # Check if session exists and belongs to user
            if self.supabase:
                # Try using service role key first to avoid RLS issues
                if settings.SUPABASE_SERVICE_KEY:
                    try:
                        logger.info(f"Checking session using service role for user ID: {user_id}")
                        service_supabase = create_client(
                            supabase_url=settings.SUPABASE_URL,
                            supabase_key=settings.SUPABASE_SERVICE_KEY
                        )
                        session_response = service_supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()
                        logger.info(f"Session checked successfully using service role")
                    except Exception as service_error:
                        logger.error(f"Error checking session using service role: {str(service_error)}")
                        # Fall back to regular key
                        logger.info(f"Falling back to regular key for checking session")
                        session_response = self.supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()
                else:
                    # No service key available, use regular key
                    session_response = self.supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()

                if not session_response.data:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Chat session with ID {session_id} not found or does not belong to user"
                    )

                # Remove document from session
                if settings.SUPABASE_SERVICE_KEY:
                    try:
                        service_supabase.table("session_documents").delete().eq("session_id", session_id).eq("document_id", document_id).execute()
                    except Exception:
                        self.supabase.table("session_documents").delete().eq("session_id", session_id).eq("document_id", document_id).execute()
                else:
                    self.supabase.table("session_documents").delete().eq("session_id", session_id).eq("document_id", document_id).execute()

                # Update session last updated time
                if settings.SUPABASE_SERVICE_KEY:
                    try:
                        service_supabase.table("chat_sessions").update({
                            "updated_at": datetime.now().isoformat()
                        }).eq("id", session_id).execute()
                    except Exception:
                        self.supabase.table("chat_sessions").update({
                            "updated_at": datetime.now().isoformat()
                        }).eq("id", session_id).execute()
                else:
                    self.supabase.table("chat_sessions").update({
                        "updated_at": datetime.now().isoformat()
                    }).eq("id", session_id).execute()

                # Get remaining document IDs for this session
                if settings.SUPABASE_SERVICE_KEY:
                    try:
                        doc_response = service_supabase.table("session_documents").select("document_id").eq("session_id", session_id).execute()
                    except Exception:
                        doc_response = self.supabase.table("session_documents").select("document_id").eq("session_id", session_id).execute()
                else:
                    doc_response = self.supabase.table("session_documents").select("document_id").eq("session_id", session_id).execute()

                remaining_doc_ids = [doc["document_id"] for doc in doc_response.data]

                return {
                    "session_id": session_id,
                    "document_ids": remaining_doc_ids,
                    "removed_document_id": document_id,
                    "updated_at": datetime.now().isoformat()
                }

            raise HTTPException(
                status_code=500,
                detail="Database connection not available"
            )

        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Error removing document from chat session: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error removing document from chat session: {str(e)}"
            )

    async def update_session(self, session_id: str, user_id: str, name: str) -> Dict[str, Any]:
        """
        Update a chat session (rename, etc.).

        Args:
            session_id: ID of the session to update
            user_id: ID of the user
            name: New name for the session

        Returns:
            Updated session information
        """
        try:
            # Check if session exists and belongs to user
            if self.supabase:
                # Try using service role key first to avoid RLS issues
                if settings.SUPABASE_SERVICE_KEY:
                    try:
                        logger.info(f"Checking session using service role for user ID: {user_id}")
                        service_supabase = create_client(
                            supabase_url=settings.SUPABASE_URL,
                            supabase_key=settings.SUPABASE_SERVICE_KEY
                        )
                        session_response = service_supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()
                        logger.info(f"Session checked successfully using service role")
                    except Exception as service_error:
                        logger.error(f"Error checking session using service role: {str(service_error)}")
                        # Fall back to regular key
                        logger.info(f"Falling back to regular key for checking session")
                        session_response = self.supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()
                else:
                    # No service key available, use regular key
                    session_response = self.supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()

                if not session_response.data:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Chat session with ID {session_id} not found or does not belong to user"
                    )

                # Update session name
                update_data = {
                    "name": name,
                    "updated_at": datetime.now().isoformat()
                }

                if settings.SUPABASE_SERVICE_KEY:
                    try:
                        service_supabase.table("chat_sessions").update(update_data).eq("id", session_id).execute()
                    except Exception:
                        self.supabase.table("chat_sessions").update(update_data).eq("id", session_id).execute()
                else:
                    self.supabase.table("chat_sessions").update(update_data).eq("id", session_id).execute()

                # Get associated documents
                if settings.SUPABASE_SERVICE_KEY:
                    try:
                        doc_response = service_supabase.table("session_documents").select("document_id").eq("session_id", session_id).execute()
                    except Exception:
                        doc_response = self.supabase.table("session_documents").select("document_id").eq("session_id", session_id).execute()
                else:
                    doc_response = self.supabase.table("session_documents").select("document_id").eq("session_id", session_id).execute()

                document_ids = [doc["document_id"] for doc in doc_response.data]

                return {
                    "session_id": session_id,
                    "name": name,
                    "document_ids": document_ids,
                    "updated_at": datetime.now().isoformat()
                }

            raise HTTPException(
                status_code=500,
                detail="Database connection not available"
            )

        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Error updating chat session: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error updating chat session: {str(e)}"
            )

    async def get_session(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get a specific chat session.

        Args:
            session_id: ID of the session
            user_id: ID of the user

        Returns:
            Session details
        """
        try:
            # Check if session exists and belongs to user
            if self.supabase:
                # Try using service role key first to avoid RLS issues
                if settings.SUPABASE_SERVICE_KEY:
                    try:
                        logger.info(f"Getting session using service role for user ID: {user_id}")
                        service_supabase = create_client(
                            supabase_url=settings.SUPABASE_URL,
                            supabase_key=settings.SUPABASE_SERVICE_KEY
                        )
                        session_response = service_supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()
                        logger.info(f"Session retrieved successfully using service role")
                    except Exception as service_error:
                        logger.error(f"Error getting session using service role: {str(service_error)}")
                        # Fall back to regular key
                        logger.info(f"Falling back to regular key for getting session")
                        session_response = self.supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()
                else:
                    # No service key available, use regular key
                    session_response = self.supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()

                if not session_response.data:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Chat session with ID {session_id} not found or does not belong to user"
                    )

                session = session_response.data[0]

                # Get associated documents
                if settings.SUPABASE_SERVICE_KEY:
                    try:
                        doc_response = service_supabase.table("session_documents").select("document_id").eq("session_id", session_id).execute()
                    except Exception:
                        doc_response = self.supabase.table("session_documents").select("document_id").eq("session_id", session_id).execute()
                else:
                    doc_response = self.supabase.table("session_documents").select("document_id").eq("session_id", session_id).execute()

                document_ids = [doc["document_id"] for doc in doc_response.data]

                return {
                    "session_id": session["id"],
                    "name": session["name"],
                    "created_at": session["created_at"],
                    "updated_at": session["updated_at"],
                    "last_message_at": session["last_message_at"],
                    "document_ids": document_ids
                }

            raise HTTPException(
                status_code=500,
                detail="Database connection not available"
            )

        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Error getting chat session: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error getting chat session: {str(e)}"
            )

    async def get_session_documents(self, session_id: str, user_id: str) -> Dict[str, List[str]]:
        """
        Get documents in a chat session.

        Args:
            session_id: ID of the session
            user_id: ID of the user

        Returns:
            List of document IDs in the session
        """
        try:
            # Check if session exists and belongs to user
            if self.supabase:
                # Try using service role key first to avoid RLS issues
                if settings.SUPABASE_SERVICE_KEY:
                    try:
                        logger.info(f"Checking session using service role for user ID: {user_id}")
                        service_supabase = create_client(
                            supabase_url=settings.SUPABASE_URL,
                            supabase_key=settings.SUPABASE_SERVICE_KEY
                        )
                        session_response = service_supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()
                        logger.info(f"Session checked successfully using service role")
                    except Exception as service_error:
                        logger.error(f"Error checking session using service role: {str(service_error)}")
                        # Fall back to regular key
                        logger.info(f"Falling back to regular key for checking session")
                        session_response = self.supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()
                else:
                    # No service key available, use regular key
                    session_response = self.supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()

                if not session_response.data:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Chat session with ID {session_id} not found or does not belong to user"
                    )

                # Get associated documents
                if settings.SUPABASE_SERVICE_KEY:
                    try:
                        doc_response = service_supabase.table("session_documents").select("document_id").eq("session_id", session_id).execute()
                    except Exception:
                        doc_response = self.supabase.table("session_documents").select("document_id").eq("session_id", session_id).execute()
                else:
                    doc_response = self.supabase.table("session_documents").select("document_id").eq("session_id", session_id).execute()

                document_ids = [doc["document_id"] for doc in doc_response.data]

                return {
                    "session_id": session_id,
                    "document_ids": document_ids
                }

            raise HTTPException(
                status_code=500,
                detail="Database connection not available"
            )

        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Error getting session documents: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error getting session documents: {str(e)}"
            )

    async def delete_session(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """
        Delete a chat session.

        Args:
            session_id: ID of the session to delete
            user_id: ID of the user

        Returns:
            Deletion status
        """
        try:
            # Check if session exists and belongs to user
            if self.supabase:
                # Try using service role key first to avoid RLS issues
                if settings.SUPABASE_SERVICE_KEY:
                    try:
                        logger.info(f"Checking session using service role for user ID: {user_id}")
                        service_supabase = create_client(
                            supabase_url=settings.SUPABASE_URL,
                            supabase_key=settings.SUPABASE_SERVICE_KEY
                        )
                        session_response = service_supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()
                        logger.info(f"Session checked successfully using service role")

                        if not session_response.data:
                            raise HTTPException(
                                status_code=404,
                                detail=f"Chat session with ID {session_id} not found or does not belong to user"
                            )

                        # Delete session (cascade will delete messages and document associations)
                        service_supabase.table("chat_sessions").delete().eq("id", session_id).execute()
                        logger.info(f"Session deleted successfully using service role")
                    except Exception as service_error:
                        logger.error(f"Error using service role: {str(service_error)}")
                        # Fall back to regular key
                        logger.info(f"Falling back to regular key for session deletion")
                        session_response = self.supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()

                        if not session_response.data:
                            raise HTTPException(
                                status_code=404,
                                detail=f"Chat session with ID {session_id} not found or does not belong to user"
                            )

                        # Delete session (cascade will delete messages and document associations)
                        self.supabase.table("chat_sessions").delete().eq("id", session_id).execute()
                else:
                    # No service key available, use regular key
                    session_response = self.supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()

                    if not session_response.data:
                        raise HTTPException(
                            status_code=404,
                            detail=f"Chat session with ID {session_id} not found or does not belong to user"
                        )

                    # Delete session (cascade will delete messages and document associations)
                    self.supabase.table("chat_sessions").delete().eq("id", session_id).execute()

            return {
                "session_id": session_id,
                "status": "deleted",
                "message": "Chat session deleted successfully"
            }

        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Error deleting chat session: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error deleting chat session: {str(e)}"
            )

    async def get_session_documents(self, session_id: str, user_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all documents for a chat session with their details.

        Args:
            session_id: ID of the session
            user_id: ID of the user

        Returns:
            List of documents with their details
        """
        try:
            documents = []

            # Check if session exists and belongs to user
            if self.supabase:
                # Try using service role key first to avoid RLS issues
                if settings.SUPABASE_SERVICE_KEY:
                    try:
                        logger.info(f"Checking session using service role for user ID: {user_id}")
                        service_supabase = create_client(
                            supabase_url=settings.SUPABASE_URL,
                            supabase_key=settings.SUPABASE_SERVICE_KEY
                        )
                        session_response = service_supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()
                        logger.info(f"Session checked successfully using service role")
                    except Exception as service_error:
                        logger.error(f"Error checking session using service role: {str(service_error)}")
                        # Fall back to regular key
                        logger.info(f"Falling back to regular key for checking session")
                        session_response = self.supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()
                else:
                    # No service key available, use regular key
                    session_response = self.supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()

                if not session_response.data:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Chat session with ID {session_id} not found or does not belong to user"
                    )

                # Get document IDs for this session
                if settings.SUPABASE_SERVICE_KEY:
                    try:
                        doc_response = service_supabase.table("session_documents").select("document_id").eq("session_id", session_id).execute()
                    except Exception:
                        doc_response = self.supabase.table("session_documents").select("document_id").eq("session_id", session_id).execute()
                else:
                    doc_response = self.supabase.table("session_documents").select("document_id").eq("session_id", session_id).execute()

                document_ids = [doc["document_id"] for doc in doc_response.data]

                # Get document details for each document ID
                for doc_id in document_ids:
                    if settings.SUPABASE_SERVICE_KEY:
                        try:
                            doc_details_response = service_supabase.table("documents").select("*").eq("id", doc_id).execute()
                        except Exception:
                            doc_details_response = self.supabase.table("documents").select("*").eq("id", doc_id).execute()
                    else:
                        doc_details_response = self.supabase.table("documents").select("*").eq("id", doc_id).execute()

                    if doc_details_response.data:
                        doc_details = doc_details_response.data[0]

                        # Generate presigned URL for S3 documents if available
                        document_url = None
                        if "s3_key" in doc_details and doc_details["s3_key"] and s3_storage.is_available():
                            document_url = s3_storage.generate_presigned_url(doc_details["s3_key"])

                        documents.append({
                            "id": doc_details["id"],
                            "file_id": doc_details["id"],
                            "file_name": doc_details["file_name"],
                            "file_type": doc_details["file_type"],
                            "file_size": doc_details.get("file_size", 0),
                            "status": doc_details["status"],
                            "created_at": doc_details["created_at"],
                            "s3_key": doc_details.get("s3_key"),
                            "url": document_url
                        })

            return {"documents": documents}

        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Error getting documents for chat session: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error getting documents for chat session: {str(e)}"
            )

    async def get_session(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get a chat session by ID.

        Args:
            session_id: ID of the session
            user_id: ID of the user

        Returns:
            Session information
        """
        try:
            # Check if session exists and belongs to user
            if self.supabase:
                # Try using service role key first to avoid RLS issues
                if settings.SUPABASE_SERVICE_KEY:
                    try:
                        logger.info(f"Getting session using service role for user ID: {user_id}")
                        service_supabase = create_client(
                            supabase_url=settings.SUPABASE_URL,
                            supabase_key=settings.SUPABASE_SERVICE_KEY
                        )
                        session_response = service_supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()
                        logger.info(f"Session retrieved successfully using service role")
                    except Exception as service_error:
                        logger.error(f"Error getting session using service role: {str(service_error)}")
                        # Fall back to regular key
                        logger.info(f"Falling back to regular key for getting session")
                        session_response = self.supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()
                else:
                    # No service key available, use regular key
                    session_response = self.supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()

                if not session_response.data:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Chat session with ID {session_id} not found or does not belong to user"
                    )

                session = session_response.data[0]

                # Get document IDs for this session
                if settings.SUPABASE_SERVICE_KEY:
                    try:
                        doc_response = service_supabase.table("session_documents").select("document_id").eq("session_id", session_id).execute()
                    except Exception:
                        doc_response = self.supabase.table("session_documents").select("document_id").eq("session_id", session_id).execute()
                else:
                    doc_response = self.supabase.table("session_documents").select("document_id").eq("session_id", session_id).execute()

                document_ids = [doc["document_id"] for doc in doc_response.data]

                return {
                    "session_id": session["id"],
                    "name": session["name"],
                    "user_id": session["user_id"],
                    "created_at": session["created_at"],
                    "updated_at": session["updated_at"],
                    "last_message_at": session["last_message_at"],
                    "document_ids": document_ids
                }

            raise HTTPException(
                status_code=500,
                detail="Database connection not available"
            )

        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Error getting chat session: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error getting chat session: {str(e)}"
            )

    async def get_messages(self, session_id: str, user_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all messages for a chat session.

        Args:
            session_id: ID of the session
            user_id: ID of the user

        Returns:
            List of chat messages
        """
        try:
            # Check if session exists and belongs to user
            if self.supabase:
                # Try using service role key first to avoid RLS issues
                if settings.SUPABASE_SERVICE_KEY:
                    try:
                        logger.info(f"Checking session using service role for user ID: {user_id}")
                        service_supabase = create_client(
                            supabase_url=settings.SUPABASE_URL,
                            supabase_key=settings.SUPABASE_SERVICE_KEY
                        )
                        session_response = service_supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()
                        logger.info(f"Session checked successfully using service role")

                        if not session_response.data:
                            raise HTTPException(
                                status_code=404,
                                detail=f"Chat session with ID {session_id} not found or does not belong to user"
                            )

                        # Get messages using service role
                        message_response = service_supabase.table("chat_messages").select("*").eq("session_id", session_id).order("timestamp").execute()
                        logger.info(f"Messages retrieved successfully using service role")
                    except Exception as service_error:
                        logger.error(f"Error using service role: {str(service_error)}")
                        # Fall back to regular key
                        logger.info(f"Falling back to regular key for session and messages")
                        session_response = self.supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()

                        if not session_response.data:
                            raise HTTPException(
                                status_code=404,
                                detail=f"Chat session with ID {session_id} not found or does not belong to user"
                            )

                        # Get messages with regular key
                        message_response = self.supabase.table("chat_messages").select("*").eq("session_id", session_id).order("timestamp").execute()
                else:
                    # No service key available, use regular key
                    session_response = self.supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()

                    if not session_response.data:
                        raise HTTPException(
                            status_code=404,
                            detail=f"Chat session with ID {session_id} not found or does not belong to user"
                        )

                    # Get messages
                    message_response = self.supabase.table("chat_messages").select("*").eq("session_id", session_id).order("timestamp").execute()

                messages = []
                for msg in message_response.data:
                    messages.append({
                        "id": msg["id"],
                        "role": msg["role"],
                        "content": msg["content"],
                        "timestamp": msg["timestamp"],
                        "metadata": msg["metadata"]
                    })

                return {"messages": messages}

            return {"messages": []}

        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Error getting chat messages: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error getting chat messages: {str(e)}"
            )

    async def send_message(
        self,
        session_id: str,
        user_id: str,
        message: str,
        use_agent: bool = False
    ) -> Dict[str, Any]:
        """
        Send a message in a chat session.

        Args:
            session_id: ID of the session
            user_id: ID of the user
            message: Message content
            use_agent: Whether to use the agent service

        Returns:
            Chat response
        """
        try:
            # Check if session exists and belongs to user
            if self.supabase:
                # Try using service role key first to avoid RLS issues
                service_supabase = None
                if settings.SUPABASE_SERVICE_KEY:
                    try:
                        logger.info(f"Checking session using service role for user ID: {user_id}")
                        service_supabase = create_client(
                            supabase_url=settings.SUPABASE_URL,
                            supabase_key=settings.SUPABASE_SERVICE_KEY
                        )
                        session_response = service_supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()
                        logger.info(f"Session checked successfully using service role")

                        if not session_response.data:
                            raise HTTPException(
                                status_code=404,
                                detail=f"Chat session with ID {session_id} not found or does not belong to user"
                            )

                        # Get associated documents using service role
                        doc_response = service_supabase.table("session_documents").select("document_id").eq("session_id", session_id).execute()
                        document_ids = [doc["document_id"] for doc in doc_response.data]

                        # Get chat history using service role
                        message_response = service_supabase.table("chat_messages").select("*").eq("session_id", session_id).order("timestamp").execute()
                    except Exception as service_error:
                        logger.error(f"Error using service role: {str(service_error)}")
                        service_supabase = None
                        # Fall back to regular key
                        logger.info(f"Falling back to regular key for session and messages")
                        session_response = self.supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()

                        if not session_response.data:
                            raise HTTPException(
                                status_code=404,
                                detail=f"Chat session with ID {session_id} not found or does not belong to user"
                            )

                        # Get associated documents with regular key
                        doc_response = self.supabase.table("session_documents").select("document_id").eq("session_id", session_id).execute()
                        document_ids = [doc["document_id"] for doc in doc_response.data]

                        # Get chat history with regular key
                        message_response = self.supabase.table("chat_messages").select("*").eq("session_id", session_id).order("timestamp").execute()
                else:
                    # No service key available, use regular key
                    session_response = self.supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()

                    if not session_response.data:
                        raise HTTPException(
                            status_code=404,
                            detail=f"Chat session with ID {session_id} not found or does not belong to user"
                        )

                    # Get associated documents
                    doc_response = self.supabase.table("session_documents").select("document_id").eq("session_id", session_id).execute()
                    document_ids = [doc["document_id"] for doc in doc_response.data]

                    # Get chat history
                    message_response = self.supabase.table("chat_messages").select("*").eq("session_id", session_id).order("timestamp").execute()

                chat_history = []
                for msg in message_response.data:
                    chat_history.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

                # Store user message
                user_message_id = str(uuid.uuid4())
                user_message_data = {
                    "id": user_message_id,
                    "session_id": session_id,
                    "role": "user",
                    "content": message,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {}
                }

                # Use service role if available
                if service_supabase:
                    service_supabase.table("chat_messages").insert(user_message_data).execute()

                    # Update session last message time
                    service_supabase.table("chat_sessions").update({
                        "last_message_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }).eq("id", session_id).execute()
                else:
                    self.supabase.table("chat_messages").insert(user_message_data).execute()

                    # Update session last message time
                    self.supabase.table("chat_sessions").update({
                        "last_message_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }).eq("id", session_id).execute()

            # Process the message
            if use_agent:
                response = await self.agent_service.chat_with_agent(
                    message=message,
                    user_id=user_id,
                    file_ids=document_ids,
                    chat_history=chat_history
                )
            else:
                response = await self.rag_service.chat_with_documents(
                    message=message,
                    user_id=user_id,
                    file_ids=document_ids,
                    chat_history=chat_history,
                    session_id=session_id
                )

            # Store assistant message
            if self.supabase:
                assistant_message_id = str(uuid.uuid4())
                assistant_message_data = {
                    "id": assistant_message_id,
                    "session_id": session_id,
                    "role": "assistant",
                    "content": response["response"],
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {
                        "sources": response.get("sources", []),
                        "chart_data": response.get("chart_data")
                    }
                }

                # Use service role if available
                if service_supabase:
                    service_supabase.table("chat_messages").insert(assistant_message_data).execute()

                    # Update session last message time
                    service_supabase.table("chat_sessions").update({
                        "last_message_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }).eq("id", session_id).execute()
                else:
                    self.supabase.table("chat_messages").insert(assistant_message_data).execute()

                    # Update session last message time
                    self.supabase.table("chat_sessions").update({
                        "last_message_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }).eq("id", session_id).execute()

            return response

        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Error sending chat message: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error sending chat message: {str(e)}"
            )

# Create a singleton instance
chat_service = ChatService()
