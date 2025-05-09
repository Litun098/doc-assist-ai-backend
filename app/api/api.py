"""
Main API router.
"""
from fastapi import APIRouter

from app.api.routes import documents, chat, auth
from app.api.endpoints import session_documents_wrapper

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])

# Include the session documents wrapper directly (no prefix)
api_router.include_router(session_documents_wrapper.router, tags=["chat"])
