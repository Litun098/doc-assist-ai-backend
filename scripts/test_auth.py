"""
Script to test authentication with Supabase.

This script:
1. Tests connection to Supabase
2. Tests user authentication
3. Tests token validation
4. Tests RLS policies with authenticated user

Usage:
python scripts/test_auth.py [email] [password]
"""
import os
import sys
import json
import logging
import argparse
from datetime import datetime
from supabase import create_client, Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("auth-tester")

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

def test_connection():
    """Test connection to Supabase."""
    logger.info("Testing connection to Supabase")

    # Connect with regular key
    regular_supabase = connect_to_supabase()

    # Test a simple query
    try:
        response = regular_supabase.rpc('exec_sql', {'sql': 'SELECT 1 as test'}).execute()
        logger.info("Connection test successful")
    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}")

    # Connect with service key if available
    if SUPABASE_SERVICE_KEY:
        logger.info("Testing connection with service role key")
        service_supabase = connect_to_supabase(SUPABASE_SERVICE_KEY)

        # Test a simple query
        try:
            response = service_supabase.rpc('exec_sql', {'sql': 'SELECT 1 as test'}).execute()
            logger.info("Service role connection test successful")
        except Exception as e:
            logger.error(f"Service role connection test failed: {str(e)}")
    else:
        logger.warning("Service role key not available, skipping service role connection test")

def test_authentication(email, password):
    """Test user authentication with Supabase."""
    logger.info(f"Testing authentication for user: {email}")

    # Connect to Supabase
    supabase = connect_to_supabase()

    # Test sign in
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if auth_response.user:
            logger.info(f"Authentication successful for user: {auth_response.user.id}")
            logger.info(f"Email: {auth_response.user.email}")
            logger.info(f"Created at: {auth_response.user.created_at}")

            # Get the access token
            access_token = auth_response.session.access_token
            logger.info(f"Access token: {access_token[:10]}...")
            logger.info(f"Token length: {len(access_token)}")
            logger.info(f"Token parts: {len(access_token.split('.'))}")

            # Create a new Supabase client with the token
            # This is the most reliable way to use the token for authenticated requests
            authenticated_supabase = create_client(
                supabase_url=SUPABASE_URL,
                supabase_key=SUPABASE_KEY,
                options={
                    "global": {
                        "headers": {
                            "Authorization": f"Bearer {access_token}"
                        }
                    }
                }
            )
            logger.info("Created new Supabase client with authentication token")

            # Return both the token and the authenticated client
            return access_token, authenticated_supabase
        else:
            logger.error("Authentication failed: No user returned")
            return None, None
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        return None, None

def test_token_validation(token):
    """Test token validation with Supabase."""
    if not token:
        logger.error("No token provided for validation test")
        return None

    logger.info("Testing token validation")

    # Connect to Supabase
    supabase = connect_to_supabase()

    # Test getting the user with the token
    try:
        user = supabase.auth.get_user(token)

        if user and user.user:
            logger.info(f"Token validation successful for user: {user.user.id}")
            logger.info(f"Email: {user.user.email}")
            return user.user.id
        else:
            logger.error("Token validation failed: No user returned")
            return None
    except Exception as e:
        logger.error(f"Token validation failed: {str(e)}")
        return None

def test_rls_policies(token, user_id, auth_client=None):
    """Test RLS policies with authenticated user."""
    if not token or not user_id:
        logger.error("No token or user ID provided for RLS policy test")
        return

    logger.info("Testing RLS policies with authenticated user")
    logger.info(f"User ID: {user_id}")
    logger.info(f"Token: {token[:10]}...")

    # If no authenticated client was provided, create one
    if not auth_client:
        try:
            auth_client = create_client(
                supabase_url=SUPABASE_URL,
                supabase_key=SUPABASE_KEY,
                options={
                    "global": {
                        "headers": {
                            "Authorization": f"Bearer {token}"
                        }
                    }
                }
            )
            logger.info("Created new authenticated Supabase client")
        except Exception as e:
            logger.error(f"Failed to create authenticated client: {str(e)}")
            return

    # Test users table
    logger.info("\n=== Testing Users Table RLS ===")
    try:
        response = auth_client.table("users").select("*").eq("id", user_id).execute()
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
        response = auth_client.table("documents").select("*").eq("user_id", user_id).execute()
        logger.info(f"✅ Documents table test: {len(response.data)} rows returned")
    except Exception as e:
        logger.error(f"❌ Documents table test failed: {str(e)}")
        logger.error("This indicates an RLS policy issue with the documents table")

    # Test chat_sessions table
    logger.info("\n=== Testing Chat Sessions Table RLS ===")
    try:
        response = auth_client.table("chat_sessions").select("*").eq("user_id", user_id).execute()
        logger.info(f"✅ Chat sessions table test: {len(response.data)} rows returned")
    except Exception as e:
        logger.error(f"❌ Chat sessions table test failed: {str(e)}")
        logger.error("This indicates an RLS policy issue with the chat_sessions table")

    # Test inserting a record (chat session)
    logger.info("\n=== Testing Insert/Delete Operations with RLS ===")
    try:
        session_name = f"Test Session {datetime.now().isoformat()}"
        response = auth_client.table("chat_sessions").insert({
            "user_id": user_id,
            "name": session_name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "last_message_at": datetime.now().isoformat()
        }).execute()

        if response.data:
            session_id = response.data[0]['id']
            logger.info(f"✅ Insert test successful: Created session {session_id}")

            # Test chat_messages table with the new session
            logger.info("\n=== Testing Chat Messages Table RLS ===")
            try:
                message_response = auth_client.table("chat_messages").insert({
                    "session_id": session_id,
                    "role": "user",
                    "content": "Test message",
                    "timestamp": datetime.now().isoformat()
                }).execute()

                if message_response.data:
                    logger.info(f"✅ Chat messages insert test successful")

                    # Test selecting the message
                    select_response = auth_client.table("chat_messages").select("*").eq("session_id", session_id).execute()
                    logger.info(f"✅ Chat messages select test: {len(select_response.data)} rows returned")
                else:
                    logger.warning("⚠️ Chat messages insert test: No data returned")
            except Exception as e:
                logger.error(f"❌ Chat messages test failed: {str(e)}")
                logger.error("This indicates an RLS policy issue with the chat_messages table")

            # Test deleting the session
            try:
                delete_response = auth_client.table("chat_sessions").delete().eq("id", session_id).execute()
                logger.info(f"✅ Delete test successful: Deleted {len(delete_response.data)} rows")
            except Exception as e:
                logger.error(f"❌ Delete test failed: {str(e)}")
                logger.error("This indicates an RLS policy issue with DELETE operations")
        else:
            logger.warning("⚠️ Insert test: No data returned - This may indicate an RLS policy issue")
    except Exception as e:
        logger.error(f"❌ Insert test failed: {str(e)}")
        logger.error("This indicates an RLS policy issue with INSERT operations")

    logger.info("\n=== RLS Testing Complete ===")
    logger.info("If you see any errors above, follow the instructions in scripts/FIX_RLS_ISSUES.md to fix them")

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
    except Exception as e:
        logger.error(f"Service role users table test failed: {str(e)}")

    # Test documents table
    try:
        response = supabase.table("documents").select("*").limit(5).execute()
        logger.info(f"Service role documents table test: {len(response.data)} rows returned")
    except Exception as e:
        logger.error(f"Service role documents table test failed: {str(e)}")

    # Test chat_sessions table
    try:
        response = supabase.table("chat_sessions").select("*").limit(5).execute()
        logger.info(f"Service role chat sessions table test: {len(response.data)} rows returned")
    except Exception as e:
        logger.error(f"Service role chat sessions table test failed: {str(e)}")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Test authentication with Supabase")
    parser.add_argument("email", nargs="?", help="Email address for authentication test")
    parser.add_argument("password", nargs="?", help="Password for authentication test")
    return parser.parse_args()

def main():
    """Main function to test authentication."""
    logger.info("Starting authentication tester")

    # Parse command line arguments
    args = parse_arguments()

    # Test connection
    test_connection()

    # Test service role access
    test_service_role_access()

    # Test authentication if email and password provided
    if args.email and args.password:
        token, auth_client = test_authentication(args.email, args.password)

        if token:
            # Test token validation
            user_id = test_token_validation(token)

            if user_id and auth_client:
                # Test RLS policies
                test_rls_policies(token, user_id, auth_client)
    else:
        logger.info("Email and password not provided, skipping authentication tests")
        logger.info("To test authentication, run: python scripts/test_auth.py [email] [password]")

    logger.info("Authentication tester completed")

if __name__ == "__main__":
    main()
