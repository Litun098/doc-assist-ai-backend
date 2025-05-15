"""
Test script for Weaviate collections.
This script tests the different collection names and ensures they're working properly.
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

def list_collections():
    """List all collections in Weaviate."""
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
                
                # Get schema details
                properties = collection.properties.get()
                logger.info(f"Collection {name} has {len(properties)} properties:")
                for prop in properties:
                    logger.info(f"  - {prop.name}: {prop.data_type}")
            except Exception as e:
                logger.error(f"Error getting details for collection {name}: {str(e)}")

        return collection_names
    except Exception as e:
        logger.error(f"Error listing collections: {str(e)}")
        return []

def fix_collection_issues():
    """Fix issues with collections."""
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
        collections = list_collections()
        
        # Check if we have both DocumentChunks and DocumentChunks38991bcc
        if "DocumentChunks" in collections and "DocumentChunks38991bcc" in collections:
            logger.info("Found both DocumentChunks and DocumentChunks38991bcc collections")
            
            # Get object counts
            base_collection = client.collections.get("DocumentChunks")
            user_collection = client.collections.get("DocumentChunks38991bcc")
            
            base_count = base_collection.aggregate.over_all().total_count
            user_count = user_collection.aggregate.over_all().total_count
            
            logger.info(f"DocumentChunks has {base_count} objects")
            logger.info(f"DocumentChunks38991bcc has {user_count} objects")
            
            # If the base collection is empty, we can delete it
            if base_count == 0:
                logger.info("Base collection is empty, deleting it")
                client.collections.delete("DocumentChunks")
                logger.info("Base collection deleted")
            
            # Update the config to use the user collection by default
            logger.info("Recommend updating LLAMAINDEX_INDEX_NAME in config to 'DocumentChunks38991bcc'")
        
        return True
    except Exception as e:
        logger.error(f"Error fixing collection issues: {str(e)}")
        return False

def main():
    """Main function."""
    logger.info("Starting Weaviate collections test")
    
    # List all collections
    collections = list_collections()
    
    # Fix collection issues if needed
    if collections:
        fix_collection_issues()
    
    logger.info("Weaviate collections test completed")

if __name__ == "__main__":
    main()
