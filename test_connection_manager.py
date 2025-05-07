"""
Test script to verify the connection manager.
This script tests the connection manager's ability to handle connections properly.
"""
import logging
import time
import gc
import sys
import tracemalloc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Start tracemalloc to track memory allocations
tracemalloc.start()

# Import connection manager
from app.utils.connection_manager import connection_manager

def test_supabase_connection():
    """Test Supabase connection."""
    logger.info("Testing Supabase connection...")
    
    # Get Supabase client
    supabase = connection_manager.get_supabase_client("default")
    if supabase:
        logger.info("✅ Supabase connection successful")
        
        # Test a simple query
        try:
            response = supabase.table("users").select("*").limit(1).execute()
            logger.info(f"✅ Supabase query successful: {response}")
        except Exception as e:
            logger.error(f"❌ Supabase query failed: {str(e)}")
    else:
        logger.error("❌ Supabase connection failed")

def test_weaviate_connection():
    """Test Weaviate connection."""
    logger.info("Testing Weaviate connection...")
    
    # Get Weaviate client
    weaviate_client = connection_manager.get_weaviate_client()
    if weaviate_client:
        logger.info("✅ Weaviate connection successful")
        
        # Test a simple query
        try:
            meta = weaviate_client.get_meta()
            logger.info(f"✅ Weaviate query successful: {meta}")
        except Exception as e:
            logger.error(f"❌ Weaviate query failed: {str(e)}")
    else:
        logger.error("❌ Weaviate connection failed")

def test_connection_cleanup():
    """Test connection cleanup."""
    logger.info("Testing connection cleanup...")
    
    # Get memory snapshot before
    snapshot1 = tracemalloc.take_snapshot()
    
    # Create and use connections
    for _ in range(5):
        supabase = connection_manager.get_supabase_client("default")
        if supabase:
            supabase.table("users").select("*").limit(1).execute()
        
        weaviate_client = connection_manager.get_weaviate_client()
        if weaviate_client:
            weaviate_client.get_meta()
    
    # Force garbage collection
    gc.collect()
    
    # Get memory snapshot after
    snapshot2 = tracemalloc.take_snapshot()
    
    # Compare snapshots
    top_stats = snapshot2.compare_to(snapshot1, 'lineno')
    
    logger.info("Top 10 memory differences:")
    for stat in top_stats[:10]:
        logger.info(f"{stat}")
    
    # Close all connections
    connection_manager.close_all_connections()
    
    # Force garbage collection again
    gc.collect()
    
    # Get memory snapshot after cleanup
    snapshot3 = tracemalloc.take_snapshot()
    
    # Compare snapshots
    top_stats = snapshot3.compare_to(snapshot2, 'lineno')
    
    logger.info("Top 10 memory differences after cleanup:")
    for stat in top_stats[:10]:
        logger.info(f"{stat}")

def main():
    """Main function."""
    logger.info("Testing connection manager...")
    
    # Test Supabase connection
    test_supabase_connection()
    
    # Test Weaviate connection
    test_weaviate_connection()
    
    # Test connection cleanup
    test_connection_cleanup()
    
    # Final cleanup
    connection_manager.close_all_connections()
    logger.info("All connections closed")
    
    # Stop tracemalloc
    current, peak = tracemalloc.get_traced_memory()
    logger.info(f"Current memory usage: {current / 1024 / 1024:.2f} MB")
    logger.info(f"Peak memory usage: {peak / 1024 / 1024:.2f} MB")
    tracemalloc.stop()

if __name__ == "__main__":
    main()
