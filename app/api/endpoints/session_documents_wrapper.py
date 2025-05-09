from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict
from app.core.auth import get_current_user
from app.models.user import User
from app.db.session import get_db
from sqlalchemy.orm import Session
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/chat/sessions/{session_id}/documents", response_model=Dict[str, List[str]])
async def get_session_documents_wrapper(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get documents in a chat session.

    Args:
        session_id: ID of the session
        current_user: Current authenticated user

    Returns:
        Dictionary with document_ids key containing a list of document IDs in the session
    """
    try:
        # Import the chat service to avoid circular imports
        from app.services.chat_service import chat_service

        # Call the service directly
        result = await chat_service.get_session_documents(session_id, current_user["id"])

        # The result should already be in the correct format with document_ids key
        return result
    except Exception as e:
        logger.error(f"Error in get_session_documents_wrapper: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get session documents: {str(e)}")
