"""
Test script for Weaviate connection.
This script tests the Weaviate connection and batch processing.
"""
import os
import sys
import time
import logging
from typing import List, Dict, Any

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import required modules
import weaviate
from weaviate.classes.init import Auth, AdditionalConfig, Timeout
from config.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_weaviate_connection():
    """Test Weaviate connection."""
    try:
        # Initialize Weaviate client
        weaviate_url = settings.WEAVIATE_URL
        if not weaviate_url.startswith("https://"):
            weaviate_url = f"https://{weaviate_url}"

        logger.info(f"Connecting to Weaviate at {weaviate_url}")
        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=weaviate_url,
            auth_credentials=Auth.api_key(settings.WEAVIATE_API_KEY),
            skip_init_checks=True,  # Skip initialization checks
            additional_config=AdditionalConfig(
                timeout=Timeout(
                    init=settings.WEAVIATE_BATCH_TIMEOUT,
                    query=settings.WEAVIATE_BATCH_TIMEOUT,
                    batch=settings.WEAVIATE_BATCH_TIMEOUT
                )
            )
        )

        # List all collections
        collections = client.collections.list_all()
        collection_names = []

        # Handle different return types
        for collection in collections:
            if hasattr(collection, 'name'):
                collection_names.append(collection.name)
            elif isinstance(collection, str):
                collection_names.append(collection)
            elif isinstance(collection, dict) and 'name' in collection:
                collection_names.append(collection['name'])

        logger.info(f"Found collections: {collection_names}")

        # Get details for each collection
        for name in collection_names:
            try:
                collection = client.collections.get(name)
                object_count = collection.aggregate.over_all().total_count
                logger.info(f"Collection: {name}, Objects: {object_count}")
            except Exception as e:
                logger.error(f"Error getting details for collection {name}: {str(e)}")

        # Test batch processing
        test_collection_name = f"TestBatch{int(time.time())}"
        logger.info(f"Creating test collection: {test_collection_name}")

        # Create the collection
        from weaviate.classes.config import DataType

        client.collections.create(
            name=test_collection_name,
            description="Test collection for batch processing",
            vectorizer_config=None,  # We'll provide our own vectors
            properties=[
                {
                    "name": "content",
                    "data_type": [DataType.TEXT],
                    "description": "The text content of the chunk"
                },
                {
                    "name": "file_id",
                    "data_type": [DataType.TEXT],
                    "description": "The ID of the file this chunk belongs to"
                }
            ]
        )

        # Create a batch
        with client.batch.dynamic() as batch:
            # Configure batch
            batch.batch_size = settings.WEAVIATE_BATCH_SIZE
            batch.timeout_retries = settings.WEAVIATE_MAX_RETRIES
            batch.callback = lambda x: logger.info(f"Batch callback: {x}")

            # Add objects to batch
            for i in range(100):  # Add 100 test objects
                properties = {
                    "content": f"This is test content {i}",
                    "file_id": f"test_file_{i % 10}"
                }
                vector = [0.1] * 1536  # Create a dummy vector of the right size
                batch.add_data_object(properties, test_collection_name, vector=vector)

        # Check if objects were added
        collection = client.collections.get(test_collection_name)
        object_count = collection.aggregate.over_all().total_count
        logger.info(f"Added {object_count} objects to test collection")

        # Clean up
        client.collections.delete(test_collection_name)
        logger.info(f"Deleted test collection: {test_collection_name}")

        # Close the connection
        client.close()
        logger.info("Weaviate connection test completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error testing Weaviate connection: {str(e)}")
        return False

if __name__ == "__main__":
    test_weaviate_connection()
