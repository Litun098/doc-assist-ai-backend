from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.models.db_models import FileStatus, FileType


class UserCreate(BaseModel):
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    plan: str
    created_at: datetime


class FileUploadResponse(BaseModel):
    id: str
    filename: str
    file_type: FileType
    file_size: int
    status: FileStatus
    created_at: datetime


class FileListResponse(BaseModel):
    files: List[FileUploadResponse]
    total: int


class ChatMessageRequest(BaseModel):
    content: str
    file_ids: List[str] = Field(default_factory=list)
    session_id: Optional[str] = None


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime
    file_ids: List[str] = Field(default_factory=list)


class ChatSessionResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    file_ids: List[str] = Field(default_factory=list)
    last_message: Optional[ChatMessageResponse] = None


class ChatSessionListResponse(BaseModel):
    sessions: List[ChatSessionResponse]
    total: int


class ErrorResponse(BaseModel):
    detail: str
