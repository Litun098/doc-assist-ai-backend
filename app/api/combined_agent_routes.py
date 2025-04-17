"""
FastAPI routes for combined agent capabilities.
"""
from fastapi import APIRouter, Depends, HTTPException, Form, Query
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import logging

from app.api.schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    ErrorResponse
)
from app.services.combined_agent_service import combined_agent_service
from config.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/combined-agent", tags=["CombinedAgent"])


@router.post("/process", response_model=Dict[str, Any])
async def process_combined_agent_request(
    query_request: ChatMessageRequest,
    user_id: str = Form(...)
):
    """
    Process a request using the combined agent.
    
    Args:
        query_request: The query request
        user_id: ID of the user making the query
        
    Returns:
        Dict containing the agent's response
    """
    try:
        # Execute the query
        result = await combined_agent_service.process_request(
            query=query_request.content,
            user_id=user_id,
            file_ids=query_request.file_ids
        )
        
        # Create a chat message
        message_id = str(uuid.uuid4())
        session_id = query_request.session_id or str(uuid.uuid4())
        
        # Create response
        response = {
            "id": message_id,
            "role": "assistant",
            "content": result.get("response", ""),
            "created_at": datetime.now(),
            "file_ids": query_request.file_ids,
            "session_id": session_id,
            "agent_result": result
        }
        
        # TODO: Save chat message to database
        
        return response
    
    except Exception as e:
        logger.error(f"Error processing agent request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
