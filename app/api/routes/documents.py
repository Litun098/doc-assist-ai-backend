"""
API routes for document management.
"""
import os
import uuid
import shutil
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from datetime import datetime

from app.services.document_processor import document_processor
from app.models.db_models import FileType
from config.config import settings
from app.utils.s3_storage import s3_storage

router = APIRouter()

class DocumentResponse(BaseModel):
    """Response model for document operations."""
    file_id: str
    file_name: str
    file_type: str
    status: str
    message: Optional[str] = None

class DocumentListResponse(BaseModel):
    """Response model for listing documents."""
    documents: List[DocumentResponse]

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Form(...),
):
    """
    Upload a document for processing.

    Args:
        file: The file to upload
        user_id: ID of the user uploading the file

    Returns:
        DocumentResponse with file details
    """
    try:
        # Check file extension
        file_ext = os.path.splitext(file.filename)[1].lower().lstrip('.')
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )

        # Check file size
        file_size = 0
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)

        if file_size > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE / (1024 * 1024):.1f} MB"
            )

        # Create a unique file ID
        file_id = str(uuid.uuid4())

        # Determine storage method
        use_s3 = s3_storage.is_available()

        if use_s3:
            # Upload to Wasabi S3
            s3_key = f"users/{user_id}/documents/{file_id}.{file_ext}"
            s3_result = await s3_storage.upload_file(file, s3_key)
            file_path = s3_result["url"]
            storage_type = "s3"
        else:
            # Fallback to local storage
            os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
            file_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}.{file_ext}")
            file_content = await file.read()
            with open(file_path, "wb") as f:
                f.write(file_content)
            storage_type = "local"

        # Process the document in the background
        background_tasks.add_task(
            document_processor.process_document,
            file_path=file_path,
            file_id=file_id,
            user_id=user_id,
            storage_type=storage_type
        )

        return DocumentResponse(
            file_id=file_id,
            file_name=file.filename,
            file_type=file_ext,
            status="processing",
            message=f"Document uploaded to {storage_type} storage and processing started"
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading document: {str(e)}"
        )

@router.get("/list/{user_id}", response_model=DocumentListResponse)
async def list_documents(user_id: str):
    """
    List all documents for a user.

    Args:
        user_id: ID of the user

    Returns:
        DocumentListResponse with list of documents
    """
    try:
        # In a real implementation, you would get this from a database
        # For now, we'll just list files in the uploads directory
        documents = []

        if os.path.exists(settings.UPLOAD_DIR):
            for filename in os.listdir(settings.UPLOAD_DIR):
                file_path = os.path.join(settings.UPLOAD_DIR, filename)
                if os.path.isfile(file_path):
                    file_id, ext = os.path.splitext(filename)
                    ext = ext.lstrip('.')

                    # In a real implementation, you would check if the file belongs to the user
                    # For now, we'll just include all files
                    documents.append(
                        DocumentResponse(
                            file_id=file_id,
                            file_name=filename,
                            file_type=ext,
                            status="processed"
                        )
                    )

        return DocumentListResponse(documents=documents)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing documents: {str(e)}"
        )

@router.delete("/{file_id}", response_model=DocumentResponse)
async def delete_document(file_id: str, user_id: str):
    """
    Delete a document.

    Args:
        file_id: ID of the file to delete
        user_id: ID of the user

    Returns:
        DocumentResponse with deletion status
    """
    try:
        # In a real implementation, you would check if the file belongs to the user
        # For now, we'll just delete the file if it exists

        # Find the file in the uploads directory
        file_path = None
        file_name = None
        file_type = None

        if os.path.exists(settings.UPLOAD_DIR):
            for filename in os.listdir(settings.UPLOAD_DIR):
                if filename.startswith(file_id):
                    file_path = os.path.join(settings.UPLOAD_DIR, filename)
                    file_name = filename
                    _, ext = os.path.splitext(filename)
                    file_type = ext.lstrip('.')
                    break

        if not file_path:
            raise HTTPException(
                status_code=404,
                detail=f"File with ID {file_id} not found"
            )

        # Delete the file
        os.remove(file_path)

        # In a real implementation, you would also delete the document from the database
        # and remove its embeddings from the vector store

        return DocumentResponse(
            file_id=file_id,
            file_name=file_name,
            file_type=file_type,
            status="deleted",
            message="Document deleted successfully"
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting document: {str(e)}"
        )
