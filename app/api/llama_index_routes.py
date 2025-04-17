"""
FastAPI routes for LlamaIndex integration.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import os
import logging

from app.api.schemas import (
    FileUploadResponse, 
    ChatMessageRequest, 
    ChatMessageResponse,
    ErrorResponse
)
from app.models.db_models import FileStatus, FileType
from app.services.llama_index_service import llama_index_service, ChunkingStrategy
from app.workers.llama_index_tasks import process_file_with_llama_index
from config.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/llama-index", tags=["LlamaIndex"])


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file_llama_index(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Form(...),
    process_immediately: bool = Form(False),
    chunking_strategy: ChunkingStrategy = Form(ChunkingStrategy.HYBRID)
):
    """
    Upload a file for processing with LlamaIndex.
    
    Args:
        file: The file to upload
        user_id: ID of the user uploading the file
        process_immediately: Whether to process the file immediately or in the background
        chunking_strategy: Chunking strategy to use
        
    Returns:
        FileUploadResponse: Information about the uploaded file
    """
    try:
        # Check file size
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)
        
        if file_size > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=400, detail="File too large")
        
        # Determine file type
        file_type = llama_index_service._determine_file_type(file.filename)
        if file_type == FileType.UNKNOWN:
            raise HTTPException(status_code=400, detail="Unsupported file type")
        
        # Generate a unique ID for the file
        file_id = str(uuid.uuid4())
        
        # Save the file temporarily
        temp_file_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}.{file_type.value}")
        os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)
        
        with open(temp_file_path, "wb") as buffer:
            content = file.file.read()
            buffer.write(content)
            file.file.seek(0)
        
        # Create file record
        file_record = {
            "id": file_id,
            "user_id": user_id,
            "filename": file.filename,
            "original_filename": file.filename,
            "file_type": file_type,
            "file_size": file_size,
            "status": FileStatus.PENDING,
            "s3_key": temp_file_path,  # For now, just store the local path
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        # TODO: Save file record to database
        
        if process_immediately:
            # Process the file immediately
            background_tasks.add_task(
                process_file_immediately,
                file_id=file_id,
                user_id=user_id,
                file_path=temp_file_path,
                file_type=file_type,
                chunking_strategy=chunking_strategy
            )
            status = FileStatus.PROCESSING
        else:
            # Start processing task in the background with Celery
            process_file_with_llama_index.delay(
                file_id=file_id,
                user_id=user_id,
                file_path=temp_file_path,
                file_type=file_type.value
            )
            status = FileStatus.PENDING
        
        return {
            "id": file_id,
            "filename": file.filename,
            "file_type": file_type,
            "file_size": file_size,
            "status": status,
            "created_at": datetime.now()
        }
    
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_file_immediately(file_id: str, user_id: str, file_path: str, 
                                  file_type: FileType, chunking_strategy: ChunkingStrategy):
    """
    Process a file immediately (for small files or testing).
    
    Args:
        file_id: Unique ID for the file
        user_id: ID of the user who uploaded the file
        file_path: Path to the file
        file_type: Type of the file
        chunking_strategy: Chunking strategy to use
    """
    try:
        # Process the file
        result = await llama_index_service.process_file(
            file_path=file_path,
            file_id=file_id,
            user_id=user_id,
            file_type=file_type,
            chunking_strategy=chunking_strategy
        )
        
        # Update file record
        # TODO: Update file record in database with processed status
        
        logger.info(f"File {file_id} processed immediately with {result.get('chunk_count', 0)} chunks")
    
    except Exception as e:
        logger.error(f"Error processing file immediately: {str(e)}")
        # Update file record with error
        # TODO: Update file record in database with error status


@router.post("/query", response_model=Dict[str, Any])
async def query_documents_llama_index(
    query_request: ChatMessageRequest,
    user_id: str = Form(...)
):
    """
    Query documents using LlamaIndex.
    
    Args:
        query_request: The query request
        user_id: ID of the user making the query
        
    Returns:
        Dict containing query results
    """
    try:
        # Execute the query
        result = await llama_index_service.query_documents(
            query=query_request.content,
            file_ids=query_request.file_ids,
            user_id=user_id,
            top_k=5
        )
        
        # Create a chat message
        message_id = str(uuid.uuid4())
        session_id = query_request.session_id or str(uuid.uuid4())
        
        # Create response
        response = {
            "id": message_id,
            "role": "assistant",
            "content": result["response"],
            "created_at": datetime.now(),
            "file_ids": query_request.file_ids,
            "session_id": session_id,
            "source_documents": result["source_documents"],
            "model_used": result["model_used"]
        }
        
        # TODO: Save chat message to database
        
        return response
    
    except Exception as e:
        logger.error(f"Error querying documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
