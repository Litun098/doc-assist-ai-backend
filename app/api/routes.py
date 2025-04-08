from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from typing import List, Optional
import uuid
from datetime import datetime
import os

from app.api.schemas import (
    UserCreate, UserLogin, UserResponse,
    FileUploadResponse, FileListResponse,
    ChatMessageRequest, ChatMessageResponse,
    ChatSessionResponse, ChatSessionListResponse,
    ErrorResponse
)
from app.models.db_models import FileStatus, FileType
from app.services.file_parser import determine_file_type, save_uploaded_file
from app.workers.tasks import process_file_task
from config.config import settings

router = APIRouter()


# Auth routes
@router.post("/auth/register", response_model=UserResponse)
def register_user(user_data: UserCreate):
    """Register a new user"""
    # TODO: Implement with Supabase
    user_id = str(uuid.uuid4())
    return {
        "id": user_id,
        "email": user_data.email,
        "plan": "free",
        "created_at": datetime.now()
    }


@router.post("/auth/login")
def login_user(user_data: UserLogin):
    """Login a user"""
    # TODO: Implement with Supabase
    user_id = str(uuid.uuid4())
    return {
        "id": user_id,
        "email": user_data.email,
        "plan": "free",
        "created_at": datetime.now(),
        "token": "dummy_token"
    }


# File routes
@router.post("/files/upload", response_model=FileUploadResponse)
def upload_file(
    file: UploadFile = File(...),
    user_id: str = Form(...),
):
    """Upload a file for processing"""
    # Check file size
    file_size = 0
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File too large")

    # Check file type
    file_type = determine_file_type(file.filename)
    if file_type == FileType.UNKNOWN:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    # Generate a unique ID for the file
    file_id = str(uuid.uuid4())

    # Save the file
    s3_key = save_uploaded_file(file, file_id, file_type)

    # Create file record
    file_record = {
        "id": file_id,
        "user_id": user_id,
        "filename": file.filename,
        "original_filename": file.filename,
        "file_type": file_type,
        "file_size": file_size,
        "status": FileStatus.PENDING,
        "s3_key": s3_key,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }

    # TODO: Save file record to database

    # Start processing task
    process_file_task.delay(file_id)

    return {
        "id": file_id,
        "filename": file.filename,
        "file_type": file_type,
        "file_size": file_size,
        "status": FileStatus.PENDING,
        "created_at": datetime.now()
    }


@router.get("/files", response_model=FileListResponse)
def list_files(
    user_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    """List files for a user"""
    # TODO: Implement with database
    return {
        "files": [],
        "total": 0
    }


@router.get("/files/{file_id}", response_model=FileUploadResponse)
def get_file(file_id: str, user_id: str):
    """Get file details"""
    # TODO: Implement with database
    return {
        "id": file_id,
        "filename": "example.pdf",
        "file_type": FileType.PDF,
        "file_size": 1024,
        "status": FileStatus.PROCESSED,
        "created_at": datetime.now()
    }


# Chat routes
@router.post("/chat/message", response_model=ChatMessageResponse)
def send_message(message: ChatMessageRequest, user_id: str):
    """Send a message to the AI"""
    # TODO: Implement with LangChain and OpenAI
    message_id = str(uuid.uuid4())

    # Create a dummy response for now
    return {
        "id": message_id,
        "role": "assistant",
        "content": "This is a placeholder response. The actual AI integration will be implemented soon.",
        "created_at": datetime.now(),
        "file_ids": message.file_ids
    }


@router.get("/chat/sessions", response_model=ChatSessionListResponse)
def list_chat_sessions(
    user_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    """List chat sessions for a user"""
    # TODO: Implement with database
    return {
        "sessions": [],
        "total": 0
    }


@router.get("/chat/sessions/{session_id}", response_model=ChatSessionResponse)
def get_chat_session(session_id: str, user_id: str):
    """Get chat session details"""
    # TODO: Implement with database
    return {
        "id": session_id,
        "title": "Example Chat",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "file_ids": [],
        "last_message": None
    }


@router.get("/chat/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
def get_chat_messages(
    session_id: str,
    user_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100)
):
    """Get messages for a chat session"""
    # TODO: Implement with database
    return []
