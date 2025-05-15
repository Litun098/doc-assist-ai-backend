"""
Celery tasks for LlamaIndex document processing.
"""
import os
import asyncio
from datetime import datetime
import traceback
import logging

from config.celery_worker import celery_app
from app.models.db_models import FileStatus, FileType
from app.services.llama_index_service import llama_index_service, ChunkingStrategy

# Configure logging
logger = logging.getLogger(__name__)


@celery_app.task(name="process_file_with_llama_index")
def process_file_with_llama_index(file_id: str, user_id: str, file_path: str = None, file_type: str = None, session_id: str = None):
    """
    Process a file using LlamaIndex.

    Args:
        file_id: Unique ID for the file
        user_id: ID of the user who uploaded the file
        file_path: Path to the file (optional)
        file_type: Type of the file (optional)
        session_id: ID of the session to associate the document with (optional)

    Returns:
        Dict containing processing results
    """
    try:
        # Log the start of processing
        logger.info(f"Processing file {file_id} for user {user_id}")

        # If file_path is not provided, construct it from file_id and file_type
        if not file_path:
            # Try to get file info from database
            # TODO: Get file info from database

            # For now, assume the file is in the uploads directory
            if not file_type:
                # Try to find the file by looking for any file with the file_id prefix
                upload_dir = os.environ.get("UPLOAD_DIR", "uploads")
                for filename in os.listdir(upload_dir):
                    if filename.startswith(file_id):
                        file_path = os.path.join(upload_dir, filename)
                        file_type = filename.split(".")[-1]
                        break
            else:
                file_path = os.path.join("uploads", f"{file_id}.{file_type}")

        if not file_path or not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")

        # Convert file_type string to FileType enum
        if isinstance(file_type, str):
            file_type = FileType(file_type)

        # Update file status to processing
        # TODO: Update file status in database
        logger.info(f"Processing file {file_id} at path {file_path}")

        # Run the async processing function in a synchronous context
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(
            llama_index_service.process_file(
                file_path=file_path,
                file_id=file_id,
                user_id=user_id,
                file_type=file_type,
                chunking_strategy=ChunkingStrategy.HYBRID,
                session_id=session_id
            )
        )

        # Save chunks to database
        # TODO: Save chunks to database

        # Update file status to processed
        # TODO: Update file status in database
        logger.info(f"File {file_id} processed successfully with {result.get('chunk_count', 0)} chunks")

        return {
            "file_id": file_id,
            "status": "processed",
            "page_count": result.get("page_count", 0),
            "has_images": result.get("has_images", False),
            "chunk_count": result.get("chunk_count", 0)
        }

    except Exception as e:
        # Log the error
        error_message = str(e)
        traceback_str = traceback.format_exc()
        logger.error(f"File processing failed for file {file_id}: {error_message}")
        logger.error(traceback_str)

        # Update file status to failed
        # TODO: Update file status in database

        # Re-raise the exception
        raise
