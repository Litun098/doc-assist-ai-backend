"""
Script to fix authentication issues in the AnyDocAI backend.

This script:
1. Checks for common authentication issues in the codebase
2. Provides guidance on how to fix them

Usage:
python scripts/fix_auth_service.py
"""
import os
import sys
import re
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("auth-fixer")

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

def check_auth_service():
    """Check the auth_service.py file for common issues."""
    auth_service_path = Path("app/services/auth_service.py")
    
    if not auth_service_path.exists():
        logger.error(f"Auth service file not found at {auth_service_path}")
        return
    
    logger.info(f"Checking auth service file: {auth_service_path}")
    
    with open(auth_service_path, "r") as f:
        content = f.read()
    
    # Check for common issues
    issues = []
    
    # Check if service role key is being used for client authentication
    if re.search(r"supabase_key=settings\.SUPABASE_SERVICE_KEY", content):
        issues.append("Using service role key for client authentication")
    
    # Check if JWT token is being passed correctly
    if not re.search(r"Authorization.*Bearer", content):
        issues.append("JWT token may not be passed correctly in Authorization header")
    
    # Check for RLS bypass workarounds
    if re.search(r"RLS.*bypass|bypass.*RLS", content):
        issues.append("Using workarounds to bypass RLS")
    
    # Report issues
    if issues:
        logger.warning(f"Found {len(issues)} potential issues in auth_service.py:")
        for i, issue in enumerate(issues, 1):
            logger.warning(f"{i}. {issue}")
    else:
        logger.info("No common issues found in auth_service.py")

def check_connection_manager():
    """Check the connection_manager.py file for common issues."""
    connection_manager_path = Path("app/utils/connection_manager.py")
    
    if not connection_manager_path.exists():
        logger.error(f"Connection manager file not found at {connection_manager_path}")
        return
    
    logger.info(f"Checking connection manager file: {connection_manager_path}")
    
    with open(connection_manager_path, "r") as f:
        content = f.read()
    
    # Check for common issues
    issues = []
    
    # Check if service role key is being used as default
    if re.search(r"default.*service_role|service_role.*default", content):
        issues.append("Using service role key as default")
    
    # Check if JWT token is being handled correctly
    if not re.search(r"Authorization.*Bearer|Bearer.*Authorization", content):
        issues.append("JWT token may not be handled correctly")
    
    # Report issues
    if issues:
        logger.warning(f"Found {len(issues)} potential issues in connection_manager.py:")
        for i, issue in enumerate(issues, 1):
            logger.warning(f"{i}. {issue}")
    else:
        logger.info("No common issues found in connection_manager.py")

def check_api_endpoints():
    """Check API endpoint files for common authentication issues."""
    api_dir = Path("app/api")
    
    if not api_dir.exists() or not api_dir.is_dir():
        logger.error(f"API directory not found at {api_dir}")
        return
    
    logger.info(f"Checking API endpoint files in: {api_dir}")
    
    issues_by_file = {}
    
    for file_path in api_dir.glob("**/*.py"):
        with open(file_path, "r") as f:
            content = f.read()
        
        # Check for common issues
        issues = []
        
        # Check if service role key is being used unnecessarily
        if re.search(r"service_role|SUPABASE_SERVICE_KEY", content):
            issues.append("Using service role key in API endpoint")
        
        # Check if JWT token is being extracted correctly
        if re.search(r"auth.*token|token.*auth", content) and not re.search(r"Authorization.*Bearer|Bearer.*Authorization", content):
            issues.append("JWT token may not be extracted correctly from request")
        
        # Report issues for this file
        if issues:
            issues_by_file[file_path.name] = issues
    
    # Report all issues
    if issues_by_file:
        logger.warning(f"Found issues in {len(issues_by_file)} API endpoint files:")
        for file_name, issues in issues_by_file.items():
            logger.warning(f"Issues in {file_name}:")
            for i, issue in enumerate(issues, 1):
                logger.warning(f"  {i}. {issue}")
    else:
        logger.info("No common issues found in API endpoint files")

def provide_fix_guidance():
    """Provide guidance on how to fix common authentication issues."""
    logger.info("\n=== Guidance for Fixing Authentication Issues ===")
    
    logger.info("\n1. Use the anon key for client authentication:")
    logger.info("   - In auth_service.py, ensure you're using SUPABASE_KEY, not SUPABASE_SERVICE_KEY")
    logger.info("   - Example:")
    logger.info("     ```python")
    logger.info("     supabase = create_client(")
    logger.info("         supabase_url=settings.SUPABASE_URL,")
    logger.info("         supabase_key=settings.SUPABASE_KEY")
    logger.info("     )")
    logger.info("     ```")
    
    logger.info("\n2. Pass the JWT token correctly:")
    logger.info("   - Extract the token from the Authorization header")
    logger.info("   - Example:")
    logger.info("     ```python")
    logger.info("     auth_header = request.headers.get('Authorization')")
    logger.info("     if auth_header and auth_header.startswith('Bearer '):")
    logger.info("         token = auth_header.replace('Bearer ', '')")
    logger.info("     ```")
    
    logger.info("\n3. Use the token for authentication:")
    logger.info("   - Pass the token to Supabase auth.get_user()")
    logger.info("   - Example:")
    logger.info("     ```python")
    logger.info("     user = supabase.auth.get_user(token)")
    logger.info("     ```")
    
    logger.info("\n4. Only use service role key when necessary:")
    logger.info("   - Use it only for admin operations or when RLS needs to be bypassed")
    logger.info("   - Example:")
    logger.info("     ```python")
    logger.info("     # Only for admin operations")
    logger.info("     service_supabase = create_client(")
    logger.info("         supabase_url=settings.SUPABASE_URL,")
    logger.info("         supabase_key=settings.SUPABASE_SERVICE_KEY")
    logger.info("     )")
    logger.info("     ```")

def main():
    """Main function to check for authentication issues."""
    logger.info("Starting authentication issue checker")
    
    # Check auth service
    check_auth_service()
    
    # Check connection manager
    check_connection_manager()
    
    # Check API endpoints
    check_api_endpoints()
    
    # Provide guidance
    provide_fix_guidance()
    
    logger.info("Authentication issue checker completed")
    logger.info("For more detailed guidance, see scripts/FIX_RLS_ISSUES.md")

if __name__ == "__main__":
    main()
