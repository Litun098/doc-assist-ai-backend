from celery import Task
import os
from datetime import datetime
import traceback

from config.celery_worker import celery_app
from app.models.db_models import FileStatus, FileType
from app.services.file_parser import parse_file, determine_file_type
from app.services.chunker import create_chunks_from_content
from app.services.embedder import EmbeddingService


class FileProcessingTask(Task):
    """Task for processing uploaded files"""
    name = "file_processing_task"

    def __init__(self):
        self.embedding_service = None

    def __call__(self, *args, **kwargs):
        if self.embedding_service is None:
            self.embedding_service = EmbeddingService()
        return super().__call__(*args, **kwargs)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        file_id = args[0]
        error_message = str(exc)
        traceback_str = traceback.format_exc()

        # Update file status to failed
        # TODO: Update file status in database
        print(f"File processing failed for file {file_id}: {error_message}")
        print(traceback_str)


@celery_app.task(bind=True, base=FileProcessingTask)
def process_file_task(self, file_id: str):
    """Process an uploaded file"""
    # TODO: Get file info from database
    # For now, we'll use dummy data
    file_path = os.path.join("uploads", f"{file_id}.pdf")
    file_type = FileType.PDF

    # Update file status to processing
    # TODO: Update file status in database
    print(f"Processing file {file_id}")

    try:
        # Parse the file
        content, has_images, page_count = parse_file(file_path, file_type)

        # Create chunks using the hybrid chunking system
        chunks = create_chunks_from_content(file_id, content, file_type)

        # Generate embeddings
        chunk_embedding_ids = self.embedding_service.embed_chunks(chunks)

        # Update chunks with embedding IDs
        for chunk in chunks:
            if chunk.id in chunk_embedding_ids:
                chunk.embedding_id = chunk_embedding_ids[chunk.id]

        # Save chunks to database
        # TODO: Save chunks to database

        # Update file status to processed
        # TODO: Update file status in database
        print(f"File {file_id} processed successfully")

        return {
            "file_id": file_id,
            "status": "processed",
            "page_count": page_count,
            "has_images": has_images,
            "chunk_count": len(chunks)
        }

    except Exception as e:
        # Update file status to failed
        # TODO: Update file status in database
        print(f"File processing failed for file {file_id}: {str(e)}")
        raise
