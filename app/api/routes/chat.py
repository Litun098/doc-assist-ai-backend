"""
API routes for chat functionality.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.services.rag_service import rag_service
from app.services.simple_combined_agent import simple_combined_agent

router = APIRouter()

class ChatMessage(BaseModel):
    """Chat message model."""
    role: str  # "user", "assistant", or "system"
    content: str

class ChatRequest(BaseModel):
    """Request model for chat."""
    message: str
    user_id: str
    file_ids: Optional[List[str]] = None
    chat_history: Optional[List[ChatMessage]] = None
    use_agent: bool = False

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

@router.post("/message", response_model=ChatResponse)
async def chat_message(request: ChatRequest):
    """
    Process a chat message.
    
    Args:
        request: ChatRequest with message details
        
    Returns:
        ChatResponse with assistant's response
    """
    try:
        if request.use_agent:
            # Use the simple combined agent
            result = await simple_combined_agent.process_request(
                query=request.message,
                user_id=request.user_id,
                file_ids=request.file_ids
            )
            
            # Convert to ChatResponse format
            return ChatResponse(
                response=result.get("response", ""),
                message=request.message,
                file_ids=result.get("file_ids", []),
                user_id=result.get("user_id", ""),
                timestamp=result.get("timestamp", ""),
                chart_data=result.get("chart_data"),
                error=result.get("error")
            )
        else:
            # Use the RAG service
            # Convert chat history to the format expected by the RAG service
            chat_history = None
            if request.chat_history:
                chat_history = [
                    {"role": msg.role, "content": msg.content}
                    for msg in request.chat_history
                ]
            
            result = await rag_service.chat_with_documents(
                message=request.message,
                user_id=request.user_id,
                file_ids=request.file_ids,
                chat_history=chat_history
            )
            
            # Convert to ChatResponse format
            return ChatResponse(
                response=result.get("response", ""),
                message=request.message,
                file_ids=result.get("file_ids", []),
                user_id=result.get("user_id", ""),
                timestamp=result.get("timestamp", ""),
                sources=result.get("sources", []),
                error=result.get("error")
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat message: {str(e)}"
        )

@router.post("/query", response_model=ChatResponse)
async def query_documents(request: ChatRequest):
    """
    Query documents without chat history.
    
    Args:
        request: ChatRequest with query details
        
    Returns:
        ChatResponse with query results
    """
    try:
        result = await rag_service.query_documents(
            query=request.message,
            user_id=request.user_id,
            file_ids=request.file_ids
        )
        
        # Convert to ChatResponse format
        return ChatResponse(
            response=result.get("response", ""),
            message=request.message,
            file_ids=result.get("file_ids", []),
            user_id=result.get("user_id", ""),
            timestamp=result.get("timestamp", ""),
            sources=result.get("sources", []),
            error=result.get("error")
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error querying documents: {str(e)}"
        )
