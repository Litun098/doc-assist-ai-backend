"""
Simple script to test RLS policies in Supabase.

This script:
1. Connects to Supabase with the service role key
2. Attempts to access tables with RLS policies
3. Reports any issues found

Usage:
python scripts/test_rls.py
"""
import os
import sys
import json
import logging
from datetime import datetime
from supabase import create_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("rls-tester")

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("Loaded environment variables from .env file")
except ImportError:
    logger.warning("python-dotenv not installed, using environment variables directly")

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def connect_to_supabase(key=None):
    """Connect to Supabase using the provided key or default key."""
    if not SUPABASE_URL:
        logger.error("Supabase URL not found in environment variables")
        sys.exit(1)

    if not key and not SUPABASE_KEY:
        logger.error("Supabase key not found in environment variables")
        sys.exit(1)

    supabase_key = key or SUPABASE_KEY

    logger.info(f"Connecting to Supabase at {SUPABASE_URL}")
    try:
        supabase = create_client(SUPABASE_URL, supabase_key)
        logger.info("Connected to Supabase successfully")
        return supabase
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {str(e)}")
        sys.exit(1)

def test_service_role_access():
    """Test service role access to tables."""
    if not SUPABASE_SERVICE_KEY:
        logger.warning("Service role key not available, skipping service role access test")
        return

    logger.info("Testing service role access to tables")

    # Connect to Supabase with service role key
    supabase = connect_to_supabase(SUPABASE_SERVICE_KEY)

    # Test users table
    try:
        response = supabase.table("users").select("*").limit(5).execute()
        logger.info(f"Service role users table test: {len(response.data)} rows returned")
        
        # If we have users, get the first user ID for further testing
        if response.data:
            user_id = response.data[0]['id']
            logger.info(f"Found user ID for testing: {user_id}")
            return user_id
        else:
            logger.warning("No users found in the database")
            return None
    except Exception as e:
        logger.error(f"Service role users table test failed: {str(e)}")
        return None

def test_rls_policies_for_user(user_id):
    """Test RLS policies for a specific user."""
    if not user_id:
        logger.error("No user ID provided for RLS policy test")
        return

    logger.info(f"Testing RLS policies for user: {user_id}")

    # Connect to Supabase with service role key
    supabase = connect_to_supabase(SUPABASE_SERVICE_KEY)

    # Test users table
    logger.info("\n=== Testing Users Table RLS ===")
    try:
        response = supabase.table("users").select("*").eq("id", user_id).execute()
        if response.data:
            logger.info(f"✅ Users table test successful: {len(response.data)} rows returned")
            logger.info(f"User data: {json.dumps(response.data[0], indent=2)}")
        else:
            logger.warning("⚠️ Users table test: No data returned - This may indicate an RLS policy issue")
    except Exception as e:
        logger.error(f"❌ Users table test failed: {str(e)}")
        logger.error("This indicates an RLS policy issue with the users table")

    # Test documents table
    logger.info("\n=== Testing Documents Table RLS ===")
    try:
        response = supabase.table("documents").select("*").eq("user_id", user_id).execute()
        logger.info(f"✅ Documents table test: {len(response.data)} rows returned")
    except Exception as e:
        logger.error(f"❌ Documents table test failed: {str(e)}")
        logger.error("This indicates an RLS policy issue with the documents table")

    # Test chat_sessions table
    logger.info("\n=== Testing Chat Sessions Table RLS ===")
    try:
        response = supabase.table("chat_sessions").select("*").eq("user_id", user_id).execute()
        logger.info(f"✅ Chat sessions table test: {len(response.data)} rows returned")
        
        # If we have sessions, get the first session ID for further testing
        if response.data:
            session_id = response.data[0]['id']
            logger.info(f"Found session ID for testing: {session_id}")
            
            # Test chat_messages table
            logger.info("\n=== Testing Chat Messages Table RLS ===")
            try:
                response = supabase.table("chat_messages").select("*").eq("session_id", session_id).execute()
                logger.info(f"✅ Chat messages table test: {len(response.data)} rows returned")
            except Exception as e:
                logger.error(f"❌ Chat messages table test failed: {str(e)}")
                logger.error("This indicates an RLS policy issue with the chat_messages table")
                
            # Test session_documents table
            logger.info("\n=== Testing Session Documents Table RLS ===")
            try:
                response = supabase.table("session_documents").select("*").eq("session_id", session_id).execute()
                logger.info(f"✅ Session documents table test: {len(response.data)} rows returned")
            except Exception as e:
                logger.error(f"❌ Session documents table test failed: {str(e)}")
                logger.error("This indicates an RLS policy issue with the session_documents table")
        else:
            logger.warning("No chat sessions found for this user")
    except Exception as e:
        logger.error(f"❌ Chat sessions table test failed: {str(e)}")
        logger.error("This indicates an RLS policy issue with the chat_sessions table")

    # Test user_usage table
    logger.info("\n=== Testing User Usage Table RLS ===")
    try:
        response = supabase.table("user_usage").select("*").eq("user_id", user_id).execute()
        logger.info(f"✅ User usage table test: {len(response.data)} rows returned")
    except Exception as e:
        logger.error(f"❌ User usage table test failed: {str(e)}")
        logger.error("This indicates an RLS policy issue with the user_usage table")

def main():
    """Main function to test RLS policies."""
    logger.info("Starting RLS policy tester")

    # Test service role access and get a user ID
    user_id = test_service_role_access()

    if user_id:
        # Test RLS policies for the user
        test_rls_policies_for_user(user_id)
    else:
        logger.error("No user ID available for testing RLS policies")

    logger.info("RLS policy tester completed")
    logger.info("If you see any errors above, follow the instructions in scripts/FIX_RLS_ISSUES.md to fix them")

if __name__ == "__main__":
    main()
