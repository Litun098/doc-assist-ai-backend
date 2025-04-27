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

class ChatService:
    """Chat service for managing chat sessions and messages with Supabase."""

    def __init__(self):
        """Initialize the chat service."""
        self.supabase = supabase
        self.rag_service = rag_service
        self.agent_service = agent_service

    async def create_session(self, user_id: str, name: str, document_ids: List[str]) -> Dict[str, Any]:
        """
        Create a new chat session.

        Args:
            user_id: ID of the user
            name: Name of the session
            document_ids: List of document IDs to associate with the session

        Returns:
            Session information
        """
        try:
            # Create session ID
            session_id = str(uuid.uuid4())

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

                self.supabase.table("chat_sessions").insert(session_data).execute()

                # Associate documents with session
                for doc_id in document_ids:
                    self.supabase.table("session_documents").insert({
                        "session_id": session_id,
                        "document_id": doc_id
                    }).execute()

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

            return {"sessions": sessions}

        except Exception as e:
            logger.error(f"Error listing chat sessions: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error listing chat sessions: {str(e)}"
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
                response = self.supabase.table("chat_sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()

                if not response.data:
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
                    chat_history=chat_history
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
