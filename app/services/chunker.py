from typing import List
from datetime import datetime
import uuid

from app.models.db_models import Chunk
from config.config import settings


def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """Split text into chunks with overlap"""
    if not text:
        return []
    
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = min(start + chunk_size, text_length)
        
        # Try to find a good breaking point (newline or space)
        if end < text_length:
            # Look for newline first
            newline_pos = text.rfind("\n", start, end)
            if newline_pos > start:
                end = newline_pos + 1
            else:
                # Look for space
                space_pos = text.rfind(" ", start, end)
                if space_pos > start:
                    end = space_pos + 1
        
        # Add the chunk
        chunks.append(text[start:end])
        
        # Move the start position, considering overlap
        start = end - chunk_overlap if end < text_length else text_length
    
    return chunks


def create_chunks_from_content(file_id: str, content: List[str]) -> List[Chunk]:
    """Create chunks from file content"""
    chunks = []
    chunk_index = 0
    
    for page_num, page_content in enumerate(content):
        page_chunks = chunk_text(
            page_content, 
            chunk_size=settings.CHUNK_SIZE, 
            chunk_overlap=settings.CHUNK_OVERLAP
        )
        
        for chunk_text in page_chunks:
            chunk = Chunk(
                id=str(uuid.uuid4()),
                file_id=file_id,
                content=chunk_text,
                page_number=page_num + 1,
                chunk_index=chunk_index,
                created_at=datetime.now(),
                metadata={
                    "page_number": page_num + 1,
                    "chunk_index": chunk_index
                }
            )
            chunks.append(chunk)
            chunk_index += 1
    
    return chunks
