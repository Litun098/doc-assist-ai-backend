"""
WebSocket routes for real-time communication.
"""
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.services.websocket_manager import websocket_manager
from app.api.dependencies import get_current_user

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/ws", tags=["websocket"])

class FileStatusRequest(BaseModel):
    """Request model for file status updates."""
    file_id: str
    user_id: str
    status: str
    progress: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

class ProcessingProgressRequest(BaseModel):
    """Request model for processing progress updates."""
    file_id: str
    user_id: str
    stage: str
    progress: int
    message: str

class ChatResponseRequest(BaseModel):
    """Request model for chat response chunks."""
    chat_session_id: str
    user_id: str
    chunk: str
    is_final: bool = False
    metadata: Optional[Dict[str, Any]] = None

class ErrorNotificationRequest(BaseModel):
    """Request model for error notifications."""
    user_id: str
    error_type: str
    message: str
    file_id: Optional[str] = None
    chat_session_id: Optional[str] = None

@router.post("/file-status")
async def emit_file_status(request: FileStatusRequest, current_user: dict = Depends(get_current_user)):
    """
    Emit file status update via WebSocket.
    
    This endpoint allows backend services to emit file status updates
    to connected clients in real-time.
    """
    try:
        # Verify user has permission to emit updates for this file
        # In a production system, you'd want to verify the user owns the file
        
        await websocket_manager.emit_file_status_update(
            file_id=request.file_id,
            user_id=request.user_id,
            status=request.status,
            progress=request.progress,
            metadata=request.metadata
        )
        
        return {"success": True, "message": "File status update emitted"}
        
    except Exception as e:
        logger.error(f"Error emitting file status update: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error emitting file status update: {str(e)}"
        )

@router.post("/processing-progress")
async def emit_processing_progress(request: ProcessingProgressRequest, current_user: dict = Depends(get_current_user)):
    """
    Emit processing progress update via WebSocket.
    
    This endpoint allows backend services to emit detailed processing
    progress updates to connected clients in real-time.
    """
    try:
        await websocket_manager.emit_processing_progress(
            file_id=request.file_id,
            user_id=request.user_id,
            stage=request.stage,
            progress=request.progress,
            message=request.message
        )
        
        return {"success": True, "message": "Processing progress update emitted"}
        
    except Exception as e:
        logger.error(f"Error emitting processing progress update: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error emitting processing progress update: {str(e)}"
        )

@router.post("/chat-response")
async def emit_chat_response(request: ChatResponseRequest, current_user: dict = Depends(get_current_user)):
    """
    Emit chat response chunk via WebSocket.
    
    This endpoint allows backend services to emit streaming chat
    responses to connected clients in real-time.
    """
    try:
        await websocket_manager.emit_chat_response_chunk(
            chat_session_id=request.chat_session_id,
            user_id=request.user_id,
            chunk=request.chunk,
            is_final=request.is_final,
            metadata=request.metadata
        )
        
        return {"success": True, "message": "Chat response chunk emitted"}
        
    except Exception as e:
        logger.error(f"Error emitting chat response chunk: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error emitting chat response chunk: {str(e)}"
        )

@router.post("/error")
async def emit_error(request: ErrorNotificationRequest, current_user: dict = Depends(get_current_user)):
    """
    Emit error notification via WebSocket.
    
    This endpoint allows backend services to emit error notifications
    to connected clients in real-time.
    """
    try:
        await websocket_manager.emit_error(
            user_id=request.user_id,
            error_type=request.error_type,
            message=request.message,
            file_id=request.file_id,
            chat_session_id=request.chat_session_id
        )
        
        return {"success": True, "message": "Error notification emitted"}
        
    except Exception as e:
        logger.error(f"Error emitting error notification: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error emitting error notification: {str(e)}"
        )

@router.get("/status")
async def get_websocket_status():
    """
    Get WebSocket server status and connected users.
    """
    try:
        connected_users = websocket_manager.get_connected_users()
        
        return {
            "status": "active",
            "connected_users_count": len(connected_users),
            "connected_users": connected_users
        }
        
    except Exception as e:
        logger.error(f"Error getting WebSocket status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting WebSocket status: {str(e)}"
        )

@router.get("/user/{user_id}/status")
async def get_user_connection_status(user_id: str, current_user: dict = Depends(get_current_user)):
    """
    Check if a specific user is connected via WebSocket.
    """
    try:
        # Verify current user can check this user's status
        # In production, you might want to restrict this to admins or the user themselves
        
        is_connected = websocket_manager.is_user_connected(user_id)
        
        return {
            "user_id": user_id,
            "is_connected": is_connected
        }
        
    except Exception as e:
        logger.error(f"Error checking user connection status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error checking user connection status: {str(e)}"
        )
