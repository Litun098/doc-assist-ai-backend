"""
API routes for document management.
"""
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel

from app.services.document_service import document_service
from app.services.auth_service import auth_service

router = APIRouter()

class DocumentResponse(BaseModel):
    """Response model for document operations."""
    file_id: str
    file_name: str
    file_type: str
    status: str
    message: Optional[str] = None
    file_size: Optional[int] = None

class DocumentListResponse(BaseModel):
    """Response model for listing documents."""
    documents: List[DocumentResponse]

class DocumentPreviewResponse(BaseModel):
    """Response model for document preview."""
    file_id: str
    file_name: str
    file_type: str
    preview_text: str

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user = Depends(auth_service.get_current_user)
):
    """
    Upload a document for processing.

    Args:
        file: The file to upload
        current_user: Current authenticated user

    Returns:
        DocumentResponse with file details
    """
    return await document_service.upload_document(file, current_user["id"], background_tasks)

@router.get("/list", response_model=DocumentListResponse)
async def list_documents(current_user = Depends(auth_service.get_current_user)):
    """
    List all documents for the current user.

    Args:
        current_user: Current authenticated user

    Returns:
        DocumentListResponse with list of documents
    """
    return await document_service.list_documents(current_user["id"])

@router.get("/{file_id}/preview", response_model=DocumentPreviewResponse)
async def get_document_preview(
    file_id: str,
    current_user = Depends(auth_service.get_current_user)
):
    """
    Get a preview of a document.

    Args:
        file_id: ID of the file to preview
        current_user: Current authenticated user

    Returns:
        DocumentPreviewResponse with preview text
    """
    return await document_service.get_document_preview(file_id, current_user["id"])

@router.delete("/{file_id}", response_model=DocumentResponse)
async def delete_document(
    file_id: str,
    current_user = Depends(auth_service.get_current_user)
):
    """
    Delete a document.

    Args:
        file_id: ID of the file to delete
        current_user: Current authenticated user

    Returns:
        DocumentResponse with deletion status
    """
    return await document_service.delete_document(file_id, current_user["id"])
