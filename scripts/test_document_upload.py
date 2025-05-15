"""
Test script for document upload and processing.
This script tests the document upload and processing functionality with the improved batch processing.
"""
import os
import sys
import time
import logging
import asyncio
from typing import List, Dict, Any

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import required modules
from fastapi import UploadFile, BackgroundTasks
from app.services.document_service import DocumentService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_document_upload():
    """Test document upload and processing."""
    try:
        # Create a test file
        test_file_path = "test_document.txt"
        with open(test_file_path, "w") as f:
            f.write("This is a test document.\n" * 100)  # Create a small test document
        
        logger.info(f"Created test file: {test_file_path}")
        
        # Create a mock UploadFile
        class MockUploadFile(UploadFile):
            def __init__(self, filename: str):
                self.filename = filename
                self.file = open(filename, "rb")
            
            async def read(self):
                self.file.seek(0)
                return self.file.read()
        
        # Create a mock BackgroundTasks
        class MockBackgroundTasks(BackgroundTasks):
            def __init__(self):
                self.tasks = []
            
            def add_task(self, func, *args, **kwargs):
                self.tasks.append((func, args, kwargs))
                # Execute the task immediately for testing
                asyncio.create_task(func(*args, **kwargs))
        
        # Create document service
        document_service = DocumentService()
        
        # Create mock objects
        upload_file = MockUploadFile(test_file_path)
        background_tasks = MockBackgroundTasks()
        
        # Test user ID
        user_id = "38991bcc-1988-4b00-b0d8-effc02ac15b5"  # Use the same user ID as in the config
        
        # Upload document
        logger.info(f"Uploading document for user: {user_id}")
        result = await document_service.upload_document(
            file=upload_file,
            user_id=user_id,
            background_tasks=background_tasks
        )
        
        logger.info(f"Upload result: {result}")
        
        # Wait for background processing to complete
        logger.info("Waiting for background processing to complete...")
        await asyncio.sleep(10)
        
        # List documents
        logger.info("Listing documents...")
        documents = await document_service.list_documents(user_id)
        logger.info(f"Documents: {documents}")
        
        # Clean up
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            logger.info(f"Removed test file: {test_file_path}")
        
        return True
    except Exception as e:
        logger.error(f"Error testing document upload: {str(e)}")
        return False

async def main():
    """Main function."""
    logger.info("Starting document upload test")
    
    # Test document upload
    success = await test_document_upload()
    
    if success:
        logger.info("Document upload test completed successfully")
    else:
        logger.error("Document upload test failed")

if __name__ == "__main__":
    asyncio.run(main())
