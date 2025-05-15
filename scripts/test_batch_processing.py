"""
Test script for batch processing with user-specific collections.
This script tests the batch processing functionality with user-specific collections.
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
from app.services.document_processor import document_processor
from app.services.embedder import embedder
from app.models.db_models import Chunk
from config.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_batch_processing():
    """Test batch processing with user-specific collections."""
    try:
        # Test user ID
        user_id = "38991bcc-1988-4b00-b0d8-effc02ac15b5"  # Use the same user ID as in the config
        
        # Create test chunks
        logger.info(f"Creating test chunks for user: {user_id}")
        chunks = []
        for i in range(100):  # Create 100 test chunks
            chunk = Chunk(
                id=f"test_chunk_{i}",
                file_id=f"test_file_{i % 10}",
                content=f"This is test chunk {i} with some additional text to make it more realistic. " * 5,
                page_number=i % 20,
                chunk_index=i,
                metadata={
                    "user_id": user_id,
                    "file_name": f"test_file_{i % 10}.txt",
                    "heading": f"Test Heading {i // 10}"
                }
            )
            chunks.append(chunk)
        
        # Embed chunks
        logger.info(f"Embedding {len(chunks)} chunks")
        chunk_embedding_ids = embedder.embed_chunks(chunks)
        
        logger.info(f"Embedded {len(chunk_embedding_ids)} chunks successfully")
        
        # Test search
        logger.info("Testing search functionality")
        query = "test chunk"
        search_results = embedder.search_similar_chunks(query, user_id=user_id, limit=5)
        
        logger.info(f"Search results: {len(search_results)} chunks found")
        for i, result in enumerate(search_results):
            logger.info(f"Result {i+1}: {result.get('content', '')[:50]}...")
        
        return True
    except Exception as e:
        logger.error(f"Error testing batch processing: {str(e)}")
        return False

async def main():
    """Main function."""
    logger.info("Starting batch processing test")
    
    # Test batch processing
    success = await test_batch_processing()
    
    if success:
        logger.info("Batch processing test completed successfully")
    else:
        logger.error("Batch processing test failed")

if __name__ == "__main__":
    asyncio.run(main())
