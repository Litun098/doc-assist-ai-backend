from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class FileStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class FileType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"
    TXT = "txt"
    UNKNOWN = "unknown"


class User(BaseModel):
    id: str
    email: str
    created_at: datetime
    updated_at: datetime
    plan: str = "free"


class File(BaseModel):
    id: str
    user_id: str
    filename: str
    original_filename: str
    file_type: FileType
    file_size: int
    status: FileStatus = FileStatus.PENDING
    s3_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    page_count: Optional[int] = None
    has_images: bool = False


class Chunk(BaseModel):
    id: str
    file_id: str
    content: str
    page_number: Optional[int] = None
    chunk_index: int
    embedding_id: Optional[str] = None
    created_at: datetime
    metadata: dict = Field(default_factory=dict)


class ChatMessage(BaseModel):
    id: str
    user_id: str
    session_id: str
    role: str  # "user" or "assistant"
    content: str
    created_at: datetime
    file_ids: List[str] = Field(default_factory=list)
    chunk_ids: List[str] = Field(default_factory=list)
    tokens_used: Optional[int] = None


class ChatSession(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    file_ids: List[str] = Field(default_factory=list)
