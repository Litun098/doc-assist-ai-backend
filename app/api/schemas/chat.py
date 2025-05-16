from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

# Session schemas
class SessionCreate(BaseModel):
    name: str = Field(..., description="Name of the chat session")
    document_ids: List[str] = Field(default=[], description="List of document IDs to associate with the session")

class SessionUpdate(BaseModel):
    name: str = Field(..., description="New name for the chat session")

class SessionResponse(BaseModel):
    session_id: str = Field(..., description="ID of the chat session")
    name: str = Field(..., description="Name of the chat session")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    last_message_at: Optional[str] = Field(None, description="Timestamp of the last message")
    document_ids: List[str] = Field(default=[], description="List of document IDs associated with the session")

class SessionListResponse(BaseModel):
    sessions: List[SessionResponse] = Field(..., description="List of chat sessions")

# Document schemas
class AddDocumentsRequest(BaseModel):
    document_ids: List[str] = Field(..., description="List of document IDs to add to the session")

class AddDocumentsResponse(BaseModel):
    session_id: str = Field(..., description="ID of the chat session")
    document_ids: List[str] = Field(..., description="Updated list of document IDs in the session")
    message: str = Field(..., description="Status message")

class RemoveDocumentResponse(BaseModel):
    session_id: str = Field(..., description="ID of the chat session")
    document_ids: List[str] = Field(..., description="Updated list of document IDs in the session")
    message: str = Field(..., description="Status message")

class SessionDocumentsResponse(BaseModel):
    document_ids: List[str] = Field(default=[], description="List of document IDs in the session")

# Message schemas
class MessageResponse(BaseModel):
    id: str = Field(..., description="Message ID")
    role: str = Field(..., description="Message role (user or assistant)")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="Message timestamp")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")

class MessageListResponse(BaseModel):
    messages: List[MessageResponse] = Field(default=[], description="List of messages in the session")

# Chat schemas
class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    use_agent: bool = Field(default=False, description="Whether to use the agent service")

class ChatResponse(BaseModel):
    response: str = Field(..., description="Assistant response")
    sources: Optional[List[Dict[str, Any]]] = Field(default=None, description="Source documents")
    chart_data: Optional[Dict[str, Any]] = Field(default=None, description="Chart data if generated")

# Delete response
class DeleteResponse(BaseModel):
    session_id: str = Field(..., description="ID of the deleted session")
    status: str = Field(..., description="Deletion status")
    message: str = Field(..., description="Status message")
