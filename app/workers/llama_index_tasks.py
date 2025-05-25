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

# Import WebSocket manager for real-time updates
def get_websocket_manager():
    """Get WebSocket manager instance."""
    try:
        from app.services.websocket_manager import websocket_manager
        return websocket_manager
    except ImportError:
        logger.warning("WebSocket manager not available in Celery worker")
        return None


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

        # Get WebSocket manager for real-time updates
        ws_manager = get_websocket_manager()

        # Update file status to processing
        # TODO: Update file status in database
        logger.info(f"Processing file {file_id} at path {file_path}")

        # Emit processing started update
        if ws_manager:
            try:
                # In Celery worker context, we need to create a new event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    ws_manager.emit_file_status_update(file_id, user_id, "processing", 0)
                )
                loop.run_until_complete(
                    ws_manager.emit_processing_progress(file_id, user_id, "parsing", 10, "Starting document parsing...")
                )
                loop.close()
            except Exception as ws_error:
                logger.warning(f"Error emitting WebSocket update in Celery worker: {str(ws_error)}")

        # Run the async processing function in a synchronous context
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Emit progress updates during processing
        if ws_manager:
            loop.run_until_complete(
                ws_manager.emit_processing_progress(file_id, user_id, "chunking", 30, "Creating document chunks...")
            )

        # Determine file type from file_type parameter or file path
        if isinstance(file_type, str):
            # Convert string to FileType enum
            try:
                file_type_enum = FileType(file_type.lower())
            except ValueError:
                logger.warning(f"Unknown file type: {file_type}, attempting to detect from file path")
                # Try to detect from file extension
                _, ext = os.path.splitext(file_path)
                ext = ext.lower().lstrip('.')
                if ext == 'pdf':
                    file_type_enum = FileType.PDF
                elif ext in ['docx', 'doc']:
                    file_type_enum = FileType.DOCX
                elif ext in ['xlsx', 'xls']:
                    file_type_enum = FileType.XLSX
                elif ext in ['pptx', 'ppt']:
                    file_type_enum = FileType.PPTX
                elif ext == 'txt':
                    file_type_enum = FileType.TXT
                else:
                    file_type_enum = FileType.UNKNOWN
        else:
            file_type_enum = file_type

        result = loop.run_until_complete(
            llama_index_service.process_file(
                file_path=file_path,
                file_id=file_id,
                user_id=user_id,
                file_type=file_type_enum,
                chunking_strategy=ChunkingStrategy.HYBRID,
                session_id=session_id
            )
        )

        # Emit embedding progress
        if ws_manager:
            loop.run_until_complete(
                ws_manager.emit_processing_progress(file_id, user_id, "embedding", 70, "Generating embeddings...")
            )

        # Emit indexing progress
        if ws_manager:
            loop.run_until_complete(
                ws_manager.emit_processing_progress(file_id, user_id, "indexing", 90, "Indexing document...")
            )

        # Save chunks to database
        # TODO: Save chunks to database

        # Update file status to processed
        # TODO: Update file status in database
        logger.info(f"File {file_id} processed successfully with {result.get('chunk_count', 0)} chunks")

        # Emit completion update
        if ws_manager:
            loop.run_until_complete(
                ws_manager.emit_file_status_update(
                    file_id, user_id, "processed", 100,
                    metadata={
                        "page_count": result.get("page_count", 0),
                        "has_images": result.get("has_images", False),
                        "chunk_count": result.get("chunk_count", 0)
                    }
                )
            )
            loop.run_until_complete(
                ws_manager.emit_processing_progress(file_id, user_id, "completed", 100, "Document processing completed!")
            )

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

        # Emit failure update
        if ws_manager:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    ws_manager.emit_file_status_update(file_id, user_id, "failed", 0, metadata={"error": error_message})
                )
                loop.run_until_complete(
                    ws_manager.emit_error(user_id, "file_processing", f"Failed to process file: {error_message}", file_id=file_id)
                )
            except Exception as ws_error:
                logger.error(f"Failed to emit WebSocket error update: {str(ws_error)}")

        # Re-raise the exception
        raise
