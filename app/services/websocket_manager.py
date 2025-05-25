"""
WebSocket manager for real-time communication with frontend.
Handles file processing updates, chat responses, and other real-time events.
"""
import logging
import asyncio
from typing import Dict, Any, Optional, List
import socketio
from datetime import datetime

from config.config import settings

# Configure logging
logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages WebSocket connections and real-time updates."""

    def __init__(self):
        """Initialize the WebSocket manager."""
        # Create SocketIO server with more compatible settings
        self.sio = socketio.AsyncServer(
            cors_allowed_origins=[
                "http://localhost:3000",
                "http://192.168.226.219:3000",
                "http://localhost:5500",
                "http://127.0.0.1:5500",
                "http://localhost:8000",
                "http://127.0.0.1:8000"
            ],
            logger=True,
            engineio_logger=True,
            async_mode='asgi'
        )

        # Track connected users
        self.connected_users: Dict[str, List[str]] = {}  # user_id -> [session_ids]
        self.session_users: Dict[str, str] = {}  # session_id -> user_id

        # Setup event handlers
        self._setup_event_handlers()

    def _setup_event_handlers(self):
        """Setup SocketIO event handlers."""

        @self.sio.event
        async def connect(sid, environ, auth):
            """Handle client connection."""
            logger.info(f"Client connected: {sid}")

            # Extract user_id from auth if provided
            user_id = None
            if auth and isinstance(auth, dict):
                user_id = auth.get('user_id')

            if user_id:
                # Track user connection
                if user_id not in self.connected_users:
                    self.connected_users[user_id] = []
                self.connected_users[user_id].append(sid)
                self.session_users[sid] = user_id

                # Join user-specific room
                self.sio.enter_room(sid, f"user_{user_id}")
                logger.info(f"User {user_id} connected with session {sid}")
            else:
                logger.warning(f"Client {sid} connected without user authentication")

        @self.sio.event
        async def disconnect(sid):
            """Handle client disconnection."""
            logger.info(f"Client disconnected: {sid}")

            # Remove from tracking
            if sid in self.session_users:
                user_id = self.session_users[sid]
                if user_id in self.connected_users:
                    self.connected_users[user_id].remove(sid)
                    if not self.connected_users[user_id]:
                        del self.connected_users[user_id]
                del self.session_users[sid]

                # Leave user-specific room
                self.sio.leave_room(sid, f"user_{user_id}")
                logger.info(f"User {user_id} disconnected from session {sid}")

        @self.sio.event
        async def join_file_room(sid, data):
            """Join a file-specific room for updates."""
            file_id = data.get('file_id')
            if file_id:
                self.sio.enter_room(sid, f"file_{file_id}")
                logger.info(f"Session {sid} joined file room: {file_id}")

        @self.sio.event
        async def leave_file_room(sid, data):
            """Leave a file-specific room."""
            file_id = data.get('file_id')
            if file_id:
                self.sio.leave_room(sid, f"file_{file_id}")
                logger.info(f"Session {sid} left file room: {file_id}")

        @self.sio.event
        async def join_chat_room(sid, data):
            """Join a chat session room for updates."""
            chat_session_id = data.get('chat_session_id')
            if chat_session_id:
                self.sio.enter_room(sid, f"chat_{chat_session_id}")
                logger.info(f"Session {sid} joined chat room: {chat_session_id}")

    async def emit_file_status_update(self, file_id: str, user_id: str, status: str,
                                    progress: Optional[int] = None, metadata: Optional[Dict[str, Any]] = None):
        """
        Emit file processing status update to connected clients.

        Args:
            file_id: ID of the file being processed
            user_id: ID of the user who owns the file
            status: Current status (pending, processing, processed, failed)
            progress: Processing progress percentage (0-100)
            metadata: Additional metadata about the processing
        """
        try:
            update_data = {
                'file_id': file_id,
                'status': status,
                'timestamp': datetime.now().isoformat(),
                'progress': progress,
                'metadata': metadata or {}
            }

            # Emit to user-specific room
            await self.sio.emit('file_status_update', update_data, room=f"user_{user_id}")

            # Also emit to file-specific room
            await self.sio.emit('file_status_update', update_data, room=f"file_{file_id}")

            logger.info(f"Emitted file status update for file {file_id}: {status}")

        except Exception as e:
            logger.error(f"Error emitting file status update: {str(e)}")

    async def emit_chat_response_chunk(self, chat_session_id: str, user_id: str,
                                     chunk: str, is_final: bool = False, metadata: Optional[Dict[str, Any]] = None):
        """
        Emit chat response chunk for streaming responses.

        Args:
            chat_session_id: ID of the chat session
            user_id: ID of the user
            chunk: Response chunk text
            is_final: Whether this is the final chunk
            metadata: Additional metadata
        """
        try:
            chunk_data = {
                'chat_session_id': chat_session_id,
                'chunk': chunk,
                'is_final': is_final,
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata or {}
            }

            # Only emit to chat-specific room to avoid duplicates
            # Users join chat rooms when they start chatting, so they'll receive the message
            await self.sio.emit('chat_response_chunk', chunk_data, room=f"chat_{chat_session_id}")

            logger.debug(f"Emitted chat chunk for session {chat_session_id}")

        except Exception as e:
            logger.error(f"Error emitting chat response chunk: {str(e)}")

    async def emit_processing_progress(self, file_id: str, user_id: str,
                                     stage: str, progress: int, message: str):
        """
        Emit detailed processing progress updates.

        Args:
            file_id: ID of the file being processed
            user_id: ID of the user
            stage: Current processing stage (upload, parsing, chunking, embedding, indexing)
            progress: Progress percentage for current stage
            message: Human-readable progress message
        """
        try:
            progress_data = {
                'file_id': file_id,
                'stage': stage,
                'progress': progress,
                'message': message,
                'timestamp': datetime.now().isoformat()
            }

            # Emit to user-specific room
            await self.sio.emit('processing_progress', progress_data, room=f"user_{user_id}")

            # Also emit to file-specific room
            await self.sio.emit('processing_progress', progress_data, room=f"file_{file_id}")

            logger.info(f"Emitted processing progress for file {file_id}: {stage} - {progress}%")

        except Exception as e:
            logger.error(f"Error emitting processing progress: {str(e)}")

    async def emit_error(self, user_id: str, error_type: str, message: str,
                        file_id: Optional[str] = None, chat_session_id: Optional[str] = None):
        """
        Emit error notifications to users.

        Args:
            user_id: ID of the user
            error_type: Type of error (file_processing, chat, upload, etc.)
            message: Error message
            file_id: Optional file ID if error is related to file processing
            chat_session_id: Optional chat session ID if error is related to chat
        """
        try:
            error_data = {
                'error_type': error_type,
                'message': message,
                'timestamp': datetime.now().isoformat(),
                'file_id': file_id,
                'chat_session_id': chat_session_id
            }

            # Emit to user-specific room
            await self.sio.emit('error', error_data, room=f"user_{user_id}")

            logger.warning(f"Emitted error to user {user_id}: {error_type} - {message}")

        except Exception as e:
            logger.error(f"Error emitting error notification: {str(e)}")

    def get_connected_users(self) -> List[str]:
        """Get list of currently connected user IDs."""
        return list(self.connected_users.keys())

    def is_user_connected(self, user_id: str) -> bool:
        """Check if a user is currently connected."""
        return user_id in self.connected_users and len(self.connected_users[user_id]) > 0

# Create singleton instance
websocket_manager = WebSocketManager()
