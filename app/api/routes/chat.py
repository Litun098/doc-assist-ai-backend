"""
API routes for chat functionality.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from datetime import datetime

from app.services.chat_service import chat_service
from app.services.auth_service import auth_service
from app.services.suggestion_service import suggestion_service

router = APIRouter()

class ChatMessage(BaseModel):
    """Chat message model."""
    role: str  # "user", "assistant", or "system"
    content: str

class ChatRequest(BaseModel):
    """Request model for chat."""
    message: str
    file_ids: Optional[List[str]] = None
    chat_history: Optional[List[ChatMessage]] = None
    use_agent: bool = False

class SessionRequest(BaseModel):
    """Request model for creating a chat session."""
    name: str
    document_ids: Optional[List[str]] = Field(default=None, description="Optional list of document IDs to associate with the session")

class SessionUpdateRequest(BaseModel):
    """Request model for updating a chat session."""
    name: str

class ChatResponse(BaseModel):
    """Response model for chat."""
    response: str
    message: str
    file_ids: List[str]
    user_id: str
    timestamp: str
    sources: Optional[List[Dict[str, Any]]] = None
    chart_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class SessionResponse(BaseModel):
    """Response model for session operations."""
    session_id: str
    name: str
    document_ids: List[str]
    created_at: str

class SessionListResponse(BaseModel):
    """Response model for listing sessions."""
    sessions: List[Dict[str, Any]]

class MessageListResponse(BaseModel):
    """Response model for listing messages."""
    messages: List[Dict[str, Any]]

class DocumentListResponse(BaseModel):
    """Response model for listing documents in a session."""
    documents: List[Dict[str, Any]]

class DeleteResponse(BaseModel):
    """Response model for delete operations."""
    session_id: str
    status: str
    message: str

class AddDocumentsRequest(BaseModel):
    """Request model for adding documents to a session."""
    document_ids: List[str]

class AddDocumentsResponse(BaseModel):
    """Response model for adding documents to a session."""
    session_id: str
    document_ids: List[str]
    added_document_ids: List[str]
    updated_at: str

class RemoveDocumentResponse(BaseModel):
    """Response model for removing a document from a session."""
    session_id: str
    document_ids: List[str]
    removed_document_id: str
    updated_at: str

<<<<<<< HEAD
class SessionDocumentsResponse(BaseModel):
    """Response model for getting documents in a session."""
    document_ids: List[str]
=======
class SuggestionResponse(BaseModel):
    """Response model for query suggestions."""
    session_id: str
    suggestions: List[str]
>>>>>>> feature-session-management

@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    request: SessionRequest,
    current_user = Depends(auth_service.get_current_user)
):
    """
    Create a new chat session.

    Args:
        request: SessionRequest with session details
        current_user: Current authenticated user

    Returns:
        SessionResponse with session details
    """
    return await chat_service.create_session(
        user_id=current_user["id"],
        name=request.name,
        document_ids=request.document_ids
    )

@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(current_user = Depends(auth_service.get_current_user)):
    """
    List all chat sessions for the current user.

    Args:
        current_user: Current authenticated user

    Returns:
        SessionListResponse with list of sessions
    """
    return await chat_service.list_sessions(current_user["id"])

@router.put("/sessions/{session_id}/documents", response_model=AddDocumentsResponse)
async def add_documents_to_session(
    session_id: str,
    request: AddDocumentsRequest,
    current_user = Depends(auth_service.get_current_user)
):
    """
    Add documents to an existing chat session.

    Args:
        session_id: ID of the session
        request: AddDocumentsRequest with document IDs
        current_user: Current authenticated user

    Returns:
        AddDocumentsResponse with updated session details
    """
    return await chat_service.add_documents_to_session(
        session_id=session_id,
        user_id=current_user["id"],
        document_ids=request.document_ids
    )

@router.delete("/sessions/{session_id}/documents/{document_id}", response_model=RemoveDocumentResponse)
async def remove_document_from_session(
    session_id: str,
    document_id: str,
    current_user = Depends(auth_service.get_current_user)
):
    """
    Remove a document from a chat session.

    Args:
        session_id: ID of the session
        document_id: ID of the document to remove
        current_user: Current authenticated user

    Returns:
        RemoveDocumentResponse with updated session details
    """
    return await chat_service.remove_document_from_session(
        session_id=session_id,
        user_id=current_user["id"],
        document_id=document_id
    )

@router.delete("/sessions/{session_id}", response_model=DeleteResponse)
async def delete_session(
    session_id: str,
    current_user = Depends(auth_service.get_current_user)
):
    """
    Delete a chat session.

    Args:
        session_id: ID of the session to delete
        current_user: Current authenticated user

    Returns:
        DeleteResponse with deletion status
    """
    return await chat_service.delete_session(session_id, current_user["id"])

@router.get("/sessions/{session_id}/documents", response_model=DocumentListResponse)
async def get_session_documents(
    session_id: str,
    current_user = Depends(auth_service.get_current_user)
):
    """
    Get all documents for a chat session with their details.

    Args:
        session_id: ID of the session
        current_user: Current authenticated user

    Returns:
        DocumentListResponse with list of documents and their details
    """
    return await chat_service.get_session_documents(session_id, current_user["id"])

@router.get("/sessions/{session_id}/messages", response_model=MessageListResponse)
async def get_messages(
    session_id: str,
    current_user = Depends(auth_service.get_current_user)
):
    """
    Get all messages for a chat session.

    Args:
        session_id: ID of the session
        current_user: Current authenticated user

    Returns:
        MessageListResponse with list of messages
    """
    return await chat_service.get_messages(session_id, current_user["id"])

@router.post("/sessions/{session_id}/messages", response_model=ChatResponse)
async def send_message(
    session_id: str,
    request: ChatRequest,
    current_user = Depends(auth_service.get_current_user)
):
    """
    Send a message in a chat session.

    Args:
        session_id: ID of the session
        request: ChatRequest with message details
        current_user: Current authenticated user

    Returns:
        ChatResponse with assistant's response
    """
    return await chat_service.send_message(
        session_id=session_id,
        user_id=current_user["id"],
        message=request.message,
        use_agent=request.use_agent
    )

@router.get("/sessions/{session_id}/suggestions", response_model=SuggestionResponse)
async def get_suggestions(
    session_id: str,
    current_user = Depends(auth_service.get_current_user)
):
    """
    Get suggested queries for a chat session based on the documents.

    Args:
        session_id: ID of the session
        current_user: Current authenticated user

    Returns:
        SuggestionResponse with list of suggested queries
    """
    # Verify session belongs to user
    session = await chat_service.get_session(session_id, current_user["id"])

    # Get document IDs from session
    document_ids = []
    if "document_ids" in session:
        document_ids = session["document_ids"]

    # Generate suggestions
    suggestions = await suggestion_service.generate_suggestions(
        session_id=session_id,
        user_id=current_user["id"],
        document_ids=document_ids
    )

    return {
        "session_id": session_id,
        "suggestions": suggestions
    }

# Legacy endpoints for backward compatibility

@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    current_user = Depends(auth_service.get_current_user)
):
    """
    Get a specific chat session.

    Args:
        session_id: ID of the session
        current_user: Current authenticated user

    Returns:
        SessionResponse with session details
    """
    return await chat_service.get_session(
        session_id=session_id,
        user_id=current_user["id"]
    )

@router.put("/sessions/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    request: SessionUpdateRequest,
    current_user = Depends(auth_service.get_current_user)
):
    """
    Update a chat session (rename, etc.).

    Args:
        session_id: ID of the session
        request: SessionUpdateRequest with new session details
        current_user: Current authenticated user

    Returns:
        SessionResponse with updated session details
    """
    return await chat_service.update_session(
        session_id=session_id,
        user_id=current_user["id"],
        name=request.name
    )

@router.get("/sessions/{session_id}/documents", response_model=SessionDocumentsResponse)
async def get_session_documents(
    session_id: str,
    current_user = Depends(auth_service.get_current_user)
):
    """
    Get documents in a chat session.

    Args:
        session_id: ID of the session
        current_user: Current authenticated user

    Returns:
        SessionDocumentsResponse with list of document IDs in the session
    """
    result = await chat_service.get_session_documents(
        session_id=session_id,
        user_id=current_user["id"]
    )
    # Extract just the document_ids from the result
    return {"document_ids": result["document_ids"]}

@router.post("/message", response_model=ChatResponse)
async def chat_message(
    request: ChatRequest,
    current_user = Depends(auth_service.get_current_user)
):
    """
    Process a chat message (legacy endpoint).

    Args:
        request: ChatRequest with message details
        current_user: Current authenticated user

    Returns:
        ChatResponse with assistant's response
    """
    # Create a temporary session if file_ids are provided
    if request.file_ids:
        session = await chat_service.create_session(
            user_id=current_user["id"],
            name=f"Temp Session {datetime.now().isoformat()}",
            document_ids=request.file_ids
        )

        return await chat_service.send_message(
            session_id=session["session_id"],
            user_id=current_user["id"],
            message=request.message,
            use_agent=request.use_agent
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="file_ids are required for this endpoint"
        )
