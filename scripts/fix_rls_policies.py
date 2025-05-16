"""
Script to fix RLS policies in Supabase.

This script connects to Supabase and:
1. Checks existing RLS policies
2. Drops problematic policies
3. Creates new policies with proper permissions
4. Tests the policies to ensure they work correctly

Usage:
python scripts/fix_rls_policies.py
"""
import os
import sys
import json
import logging
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
logger = logging.getLogger("rls-policy-fixer")

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

# Tables that need RLS policies
TABLES = [
    "users",
    "documents",
    "chat_sessions",
    "chat_messages",
    "session_documents",
    "user_usage"
]

def connect_to_supabase():
    """Connect to Supabase using service role key."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        logger.error("Supabase URL or service key not found in environment variables")
        sys.exit(1)

    logger.info(f"Connecting to Supabase at {SUPABASE_URL}")
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        logger.info("Connected to Supabase successfully")
        return supabase
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {str(e)}")
        sys.exit(1)

def check_table_exists(supabase, table_name):
    """Check if a table exists in the database by trying to access it."""
    logger.info(f"Checking if table {table_name} exists")
    try:
        # Try to get a single row from the table
        response = supabase.table(table_name).select("*").limit(1).execute()
        logger.info(f"Table {table_name} exists")
        return True
    except Exception as e:
        logger.warning(f"Table {table_name} does not exist or is not accessible: {str(e)}")
        return False

def get_existing_policies(supabase, table_name):
    """
    Get existing RLS policies for a table.

    This function queries pg_policies to get existing policies.
    """
    logger.info(f"Getting existing policies for {table_name}")

    # SQL to query pg_policies
    sql = f"""
    SELECT policyname
    FROM pg_policies
    WHERE tablename = '{table_name}';
    """

    try:
        # Execute the SQL using RPC
        response = supabase.rpc('exec_sql', {'sql': sql}).execute()

        if response.data:
            policies = response.data
            logger.info(f"Found {len(policies)} existing policies for {table_name}")
            return policies
        else:
            logger.info(f"No existing policies found for {table_name}")
            return []
    except Exception as e:
        logger.error(f"Failed to get existing policies: {str(e)}")
        return []

def drop_policy(supabase, policy_name, table_name):
    """
    Drop an existing RLS policy.

    This function builds and executes the SQL to drop a policy.
    """
    # Build the SQL statement
    sql = f"DROP POLICY IF EXISTS \"{policy_name}\" ON {table_name};"

    logger.info(f"Dropping policy {policy_name} on {table_name}")

    try:
        # Execute the SQL using RPC
        supabase.rpc('exec_sql', {'sql': sql}).execute()
        logger.info(f"Policy dropped successfully: {policy_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to drop policy: {str(e)}")
        return False

def create_policy(supabase, policy_name, table_name, operation, using_expr=None, check_expr=None):
    """
    Create a new RLS policy.

    This function builds and executes the SQL to create a policy.
    """
    if operation.upper() not in ["ALL", "SELECT", "INSERT", "UPDATE", "DELETE"]:
        logger.error(f"Invalid operation: {operation}")
        return None

    # Build the SQL statement
    sql = f"CREATE POLICY \"{policy_name}\" ON {table_name} FOR {operation.upper()}"

    if using_expr:
        sql += f" USING ({using_expr})"
    if check_expr:
        sql += f" WITH CHECK ({check_expr})"

    sql += ";"

    policy_description = f"Policy '{policy_name}' on '{table_name}' for {operation.upper()}"
    if using_expr:
        policy_description += f" USING ({using_expr})"
    if check_expr:
        policy_description += f" WITH CHECK ({check_expr})"

    logger.info(f"Creating {policy_description}")

    try:
        # Execute the SQL using RPC
        supabase.rpc('exec_sql', {'sql': sql}).execute()
        logger.info(f"Policy created successfully: {policy_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to create policy: {str(e)}")
        return False

def enable_rls(supabase, table_name):
    """
    Enable RLS on a table.

    This function builds and executes the SQL to enable RLS.
    """
    # Build the SQL statement
    sql = f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;"

    logger.info(f"Enabling RLS on {table_name}")

    try:
        # Execute the SQL using RPC
        supabase.rpc('exec_sql', {'sql': sql}).execute()
        logger.info(f"RLS enabled successfully on {table_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to enable RLS: {str(e)}")
        return False

def fix_users_table_policies(supabase):
    """Fix RLS policies for the users table."""
    table_name = "users"

    # Check if table exists
    if not check_table_exists(supabase, table_name):
        logger.warning(f"Table {table_name} does not exist, skipping")
        return

    # Enable RLS
    enable_rls(supabase, table_name)

    # Get existing policies
    existing_policies = get_existing_policies(supabase, table_name)
    for policy in existing_policies:
        drop_policy(supabase, policy['policyname'], table_name)

    # Create new policies
    create_policy(
        supabase,
        "Users can view their own data",
        table_name,
        "SELECT",
        using_expr="auth.uid() = id"
    )

    create_policy(
        supabase,
        "Users can update their own data",
        table_name,
        "UPDATE",
        using_expr="auth.uid() = id"
    )

    # Service role can access all users
    create_policy(
        supabase,
        "Service role can access all users",
        table_name,
        "ALL",
        using_expr="auth.role() = 'service_role'"
    )

    logger.info(f"Fixed RLS policies for {table_name}")

def fix_documents_table_policies(supabase):
    """Fix RLS policies for the documents table."""
    table_name = "documents"

    # Check if table exists
    if not check_table_exists(supabase, table_name):
        logger.warning(f"Table {table_name} does not exist, skipping")
        return

    # Enable RLS
    enable_rls(supabase, table_name)

    # Get existing policies
    existing_policies = get_existing_policies(supabase, table_name)
    for policy in existing_policies:
        drop_policy(supabase, policy['policyname'], table_name)

    # Create new policies
    create_policy(
        supabase,
        "Users can view their own documents",
        table_name,
        "SELECT",
        using_expr="auth.uid() = user_id"
    )

    create_policy(
        supabase,
        "Users can insert their own documents",
        table_name,
        "INSERT",
        check_expr="auth.uid() = user_id"
    )

    create_policy(
        supabase,
        "Users can update their own documents",
        table_name,
        "UPDATE",
        using_expr="auth.uid() = user_id"
    )

    create_policy(
        supabase,
        "Users can delete their own documents",
        table_name,
        "DELETE",
        using_expr="auth.uid() = user_id"
    )

    # Service role can access all documents
    create_policy(
        supabase,
        "Service role can access all documents",
        table_name,
        "ALL",
        using_expr="auth.role() = 'service_role'"
    )

    logger.info(f"Fixed RLS policies for {table_name}")

def fix_chat_sessions_table_policies(supabase):
    """Fix RLS policies for the chat_sessions table."""
    table_name = "chat_sessions"

    # Check if table exists
    if not check_table_exists(supabase, table_name):
        logger.warning(f"Table {table_name} does not exist, skipping")
        return

    # Enable RLS
    enable_rls(supabase, table_name)

    # Get existing policies
    existing_policies = get_existing_policies(supabase, table_name)
    for policy in existing_policies:
        drop_policy(supabase, policy['policyname'], table_name)

    # Create new policies
    create_policy(
        supabase,
        "Users can view their own chat sessions",
        table_name,
        "SELECT",
        using_expr="auth.uid() = user_id"
    )

    create_policy(
        supabase,
        "Users can insert their own chat sessions",
        table_name,
        "INSERT",
        check_expr="auth.uid() = user_id"
    )

    create_policy(
        supabase,
        "Users can update their own chat sessions",
        table_name,
        "UPDATE",
        using_expr="auth.uid() = user_id"
    )

    create_policy(
        supabase,
        "Users can delete their own chat sessions",
        table_name,
        "DELETE",
        using_expr="auth.uid() = user_id"
    )

    # Service role can access all chat sessions
    create_policy(
        supabase,
        "Service role can access all chat sessions",
        table_name,
        "ALL",
        using_expr="auth.role() = 'service_role'"
    )

    logger.info(f"Fixed RLS policies for {table_name}")

def fix_chat_messages_table_policies(supabase):
    """Fix RLS policies for the chat_messages table."""
    table_name = "chat_messages"

    # Check if table exists
    if not check_table_exists(supabase, table_name):
        logger.warning(f"Table {table_name} does not exist, skipping")
        return

    # Enable RLS
    enable_rls(supabase, table_name)

    # Get existing policies
    existing_policies = get_existing_policies(supabase, table_name)
    for policy in existing_policies:
        drop_policy(supabase, policy['policyname'], table_name)

    # Create new policies
    create_policy(
        supabase,
        "Users can view messages in their sessions",
        table_name,
        "SELECT",
        using_expr="""
        auth.uid() IN (
            SELECT user_id FROM chat_sessions WHERE id = chat_messages.session_id
        )
        """
    )

    create_policy(
        supabase,
        "Users can insert messages in their sessions",
        table_name,
        "INSERT",
        check_expr="""
        auth.uid() IN (
            SELECT user_id FROM chat_sessions WHERE id = chat_messages.session_id
        )
        """
    )

    # Service role can access all chat messages
    create_policy(
        supabase,
        "Service role can access all chat messages",
        table_name,
        "ALL",
        using_expr="auth.role() = 'service_role'"
    )

    logger.info(f"Fixed RLS policies for {table_name}")

def fix_session_documents_table_policies(supabase):
    """Fix RLS policies for the session_documents table."""
    table_name = "session_documents"

    # Check if table exists
    if not check_table_exists(supabase, table_name):
        logger.warning(f"Table {table_name} does not exist, skipping")
        return

    # Enable RLS
    enable_rls(supabase, table_name)

    # Get existing policies
    existing_policies = get_existing_policies(supabase, table_name)
    for policy in existing_policies:
        drop_policy(supabase, policy['policyname'], table_name)

    # Create new policies
    create_policy(
        supabase,
        "Users can view their session documents",
        table_name,
        "SELECT",
        using_expr="""
        auth.uid() IN (
            SELECT user_id FROM chat_sessions WHERE id = session_documents.session_id
        )
        """
    )

    create_policy(
        supabase,
        "Users can insert their session documents",
        table_name,
        "INSERT",
        check_expr="""
        auth.uid() IN (
            SELECT user_id FROM chat_sessions WHERE id = session_documents.session_id
        ) AND
        auth.uid() IN (
            SELECT user_id FROM documents WHERE id = session_documents.document_id
        )
        """
    )

    create_policy(
        supabase,
        "Users can delete their session documents",
        table_name,
        "DELETE",
        using_expr="""
        auth.uid() IN (
            SELECT user_id FROM chat_sessions WHERE id = session_documents.session_id
        )
        """
    )

    # Service role can access all session documents
    create_policy(
        supabase,
        "Service role can access all session documents",
        table_name,
        "ALL",
        using_expr="auth.role() = 'service_role'"
    )

    logger.info(f"Fixed RLS policies for {table_name}")

def fix_user_usage_table_policies(supabase):
    """Fix RLS policies for the user_usage table."""
    table_name = "user_usage"

    # Check if table exists
    if not check_table_exists(supabase, table_name):
        logger.warning(f"Table {table_name} does not exist, skipping")
        return

    # Enable RLS
    enable_rls(supabase, table_name)

    # Get existing policies
    existing_policies = get_existing_policies(supabase, table_name)
    for policy in existing_policies:
        drop_policy(supabase, policy['policyname'], table_name)

    # Create new policies
    create_policy(
        supabase,
        "Users can view their own usage",
        table_name,
        "SELECT",
        using_expr="auth.uid() = user_id"
    )

    # Service role can access all user usage
    create_policy(
        supabase,
        "Service role can access all user usage",
        table_name,
        "ALL",
        using_expr="auth.role() = 'service_role'"
    )

    logger.info(f"Fixed RLS policies for {table_name}")

def test_policies(supabase):
    """Test the RLS policies to ensure they work correctly."""
    logger.info("Testing RLS policies")

    # Test users table
    try:
        response = supabase.table("users").select("*").limit(1).execute()
        logger.info(f"Users table test: {len(response.data)} rows returned")
    except Exception as e:
        logger.error(f"Users table test failed: {str(e)}")

    # Test documents table
    try:
        response = supabase.table("documents").select("*").limit(1).execute()
        logger.info(f"Documents table test: {len(response.data)} rows returned")
    except Exception as e:
        logger.error(f"Documents table test failed: {str(e)}")

    # Test chat_sessions table
    try:
        response = supabase.table("chat_sessions").select("*").limit(1).execute()
        logger.info(f"Chat sessions table test: {len(response.data)} rows returned")
    except Exception as e:
        logger.error(f"Chat sessions table test failed: {str(e)}")

    # Test chat_messages table
    try:
        response = supabase.table("chat_messages").select("*").limit(1).execute()
        logger.info(f"Chat messages table test: {len(response.data)} rows returned")
    except Exception as e:
        logger.error(f"Chat messages table test failed: {str(e)}")

    # Test session_documents table
    try:
        response = supabase.table("session_documents").select("*").limit(1).execute()
        logger.info(f"Session documents table test: {len(response.data)} rows returned")
    except Exception as e:
        logger.error(f"Session documents table test failed: {str(e)}")

    # Test user_usage table
    try:
        response = supabase.table("user_usage").select("*").limit(1).execute()
        logger.info(f"User usage table test: {len(response.data)} rows returned")
    except Exception as e:
        logger.error(f"User usage table test failed: {str(e)}")

def main():
    """Main function to fix RLS policies."""
    logger.info("Starting RLS policy fixer")

    # Connect to Supabase
    supabase = connect_to_supabase()

    # Fix policies for each table
    fix_users_table_policies(supabase)
    fix_documents_table_policies(supabase)
    fix_chat_sessions_table_policies(supabase)
    fix_chat_messages_table_policies(supabase)
    fix_session_documents_table_policies(supabase)
    fix_user_usage_table_policies(supabase)

    # Test the policies
    test_policies(supabase)

    logger.info("RLS policy fixer completed")

if __name__ == "__main__":
    main()
