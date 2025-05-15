"""
Test script for Weaviate batch processing.
This script tests the batch processing functionality with different batch sizes.
"""
import os
import sys
import time
import asyncio
import logging
from typing import List, Dict, Any

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import required modules
import weaviate
from weaviate.classes.init import Auth, AdditionalConfig, Timeout
from llama_index.core import Document, VectorStoreIndex, StorageContext
from llama_index.core.schema import TextNode
from llama_index.vector_stores.weaviate import WeaviateVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.core import Settings

# Import settings
from config.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test batch sizes
TEST_BATCH_SIZES = [50, 100, 200]

async def test_batch_processing(batch_size: int, num_nodes: int = 1000):
    """
    Test batch processing with a specific batch size.
    
    Args:
        batch_size: Size of each batch
        num_nodes: Total number of nodes to process
    """
    logger.info(f"Testing batch processing with batch_size={batch_size}, num_nodes={num_nodes}")
    
    # Configure LlamaIndex settings
    Settings.llm = OpenAI(
        model=settings.DEFAULT_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.1
    )
    Settings.embed_model = OpenAIEmbedding(
        model_name=settings.EMBEDDING_MODEL,
        api_key=settings.OPENAI_API_KEY,
        embed_batch_size=10,  # Process 10 chunks at a time to avoid rate limits
    )
    
    # Initialize Weaviate client
    weaviate_url = settings.WEAVIATE_URL
    if not weaviate_url.startswith("https://"):
        weaviate_url = f"https://{weaviate_url}"
    
    logger.info(f"Connecting to Weaviate at {weaviate_url}")
    
    # Connect to Weaviate with increased timeout
    weaviate_client = weaviate.connect_to_weaviate_cloud(
        cluster_url=weaviate_url,
        auth_credentials=Auth.api_key(settings.WEAVIATE_API_KEY),
        skip_init_checks=True,  # Skip initialization checks
        additional_config=AdditionalConfig(
            timeout=Timeout(
                init=120,  # Increase timeout for initialization
                query=120,  # Increase timeout for queries
                batch=120   # Increase timeout for batch operations
            )
        )
    )
    
    # Create a test collection name with timestamp to avoid conflicts
    test_collection_name = f"TestBatch{int(time.time())}"
    logger.info(f"Creating test collection: {test_collection_name}")
    
    # Create the collection
    weaviate_client.collections.create(
        name=test_collection_name,
        description="Test collection for batch processing",
        vectorizer_config=None,  # We'll provide our own vectors
        properties=[
            {
                "name": "content",
                "dataType": ["text"],
                "description": "The text content of the chunk"
            },
            {
                "name": "file_id",
                "dataType": ["text"],
                "description": "The ID of the file this chunk belongs to"
            },
            {
                "name": "user_id",
                "dataType": ["text"],
                "description": "The ID of the user who owns this chunk"
            },
            {
                "name": "metadata",
                "dataType": ["text"],
                "description": "Additional metadata about the chunk"
            }
        ]
    )
    
    # Create vector store
    vector_store = WeaviateVectorStore(
        weaviate_client=weaviate_client,
        index_name=test_collection_name,
        text_key="content",
        metadata_keys=["file_id", "user_id", "metadata"]
    )
    
    # Create test nodes
    logger.info(f"Creating {num_nodes} test nodes")
    nodes = []
    for i in range(num_nodes):
        node = TextNode(
            text=f"This is test node {i} with some additional text to make it more realistic. " * 5,
            metadata={
                "file_id": f"test_file_{i % 10}",
                "user_id": f"test_user_{i % 5}",
                "chunk_index": i,
                "heading": f"Test Heading {i // 100}"
            }
        )
        nodes.append(node)
    
    # Process nodes in batches
    logger.info(f"Processing nodes in batches of {batch_size}")
    start_time = time.time()
    
    # Calculate number of batches
    num_batches = (num_nodes + batch_size - 1) // batch_size  # Ceiling division
    
    # Process nodes in batches
    success_count = 0
    failure_count = 0
    
    for batch_idx in range(num_batches):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, num_nodes)
        batch_nodes = nodes[start_idx:end_idx]
        
        logger.info(f"Processing batch {batch_idx + 1}/{num_batches} with {len(batch_nodes)} nodes")
        
        # Create a temporary storage context for this batch
        batch_storage_context = StorageContext.from_defaults(
            vector_store=vector_store
        )
        
        # Process the batch with retries
        retry_count = 0
        max_retries = 3
        success = False
        
        while retry_count < max_retries and not success:
            try:
                # Create a temporary index for this batch
                VectorStoreIndex(
                    nodes=batch_nodes,
                    storage_context=batch_storage_context,
                )
                success = True
                success_count += 1
                logger.info(f"Successfully processed batch {batch_idx + 1}/{num_batches}")
            except Exception as e:
                retry_count += 1
                logger.warning(f"Batch {batch_idx + 1} attempt {retry_count} failed: {str(e)}")
                if retry_count < max_retries:
                    logger.info(f"Retrying batch {batch_idx + 1} (attempt {retry_count + 1}/{max_retries})...")
                    # Wait before retrying with exponential backoff
                    await asyncio.sleep(2 ** retry_count)
                else:
                    logger.error(f"Failed to process batch {batch_idx + 1} after {max_retries} attempts")
                    failure_count += 1
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    logger.info(f"Batch processing completed in {elapsed_time:.2f} seconds")
    logger.info(f"Success: {success_count}/{num_batches} batches")
    logger.info(f"Failure: {failure_count}/{num_batches} batches")
    
    # Clean up the test collection
    logger.info(f"Cleaning up test collection: {test_collection_name}")
    try:
        weaviate_client.collections.delete(test_collection_name)
        logger.info(f"Successfully deleted test collection: {test_collection_name}")
    except Exception as e:
        logger.error(f"Error deleting test collection: {str(e)}")
    
    return {
        "batch_size": batch_size,
        "num_nodes": num_nodes,
        "elapsed_time": elapsed_time,
        "success_count": success_count,
        "failure_count": failure_count
    }

async def main():
    """Run the batch processing tests with different batch sizes."""
    results = []
    
    for batch_size in TEST_BATCH_SIZES:
        result = await test_batch_processing(batch_size)
        results.append(result)
    
    # Print summary
    logger.info("=== Test Results Summary ===")
    for result in results:
        logger.info(f"Batch Size: {result['batch_size']}, Time: {result['elapsed_time']:.2f}s, "
                   f"Success: {result['success_count']}, Failure: {result['failure_count']}")

if __name__ == "__main__":
    asyncio.run(main())
