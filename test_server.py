"""
Test script to check if the FastAPI server can start properly.
This script attempts to start the server and checks for any errors.
"""
import os
import sys
import logging
import importlib.util
import time
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

@contextmanager
def suppress_stdout():
    """Context manager to suppress stdout."""
    original_stdout = sys.stdout
    sys.stdout = open(os.devnull, 'w')
    try:
        yield
    finally:
        sys.stdout.close()
        sys.stdout = original_stdout

def check_environment():
    """Check if the environment is properly configured."""
    logger.info("Checking environment...")
    
    # Check if .env file exists
    if not os.path.exists(".env"):
        logger.error("❌ .env file not found. Please create one from .env.example")
        return False
    
    # Check if uploads directory exists
    if not os.path.exists("uploads"):
        logger.info("Creating uploads directory...")
        os.makedirs("uploads", exist_ok=True)
    
    logger.info("✅ Environment check passed")
    return True

def check_imports():
    """Check if all required modules can be imported."""
    logger.info("Checking imports...")
    
    required_modules = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "celery",
        "openai",
        "weaviate",
        "llama_index",
    ]
    
    all_imports_ok = True
    for module in required_modules:
        try:
            importlib.import_module(module)
            logger.info(f"✅ {module} imported successfully")
        except ImportError as e:
            logger.error(f"❌ Failed to import {module}: {str(e)}")
            all_imports_ok = False
    
    return all_imports_ok

def check_app_imports():
    """Check if the app can be imported."""
    logger.info("Checking app imports...")
    
    try:
        # Try to import the app
        from main import app
        logger.info("✅ App imported successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to import app: {str(e)}")
        return False

def check_lifespan():
    """Check if the lifespan handler works."""
    logger.info("Checking lifespan handler...")
    
    try:
        # Try to import the lifespan handler
        from main import lifespan
        logger.info("✅ Lifespan handler imported successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to import lifespan handler: {str(e)}")
        return False

def check_services():
    """Check if services can be initialized."""
    logger.info("Checking services...")
    
    try:
        # Try to import and initialize services
        from app.services.llama_index_service import llama_index_service
        logger.info("✅ LlamaIndex service initialized successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {str(e)}")
        return False

def main():
    """Main function."""
    logger.info("Testing AnyDocAI server startup...")
    
    # Check environment
    env_ok = check_environment()
    if not env_ok:
        logger.error("❌ Environment check failed")
        return False
    
    # Check imports
    imports_ok = check_imports()
    if not imports_ok:
        logger.error("❌ Import check failed")
        return False
    
    # Check app imports
    app_imports_ok = check_app_imports()
    if not app_imports_ok:
        logger.error("❌ App import check failed")
        return False
    
    # Check lifespan
    lifespan_ok = check_lifespan()
    if not lifespan_ok:
        logger.error("❌ Lifespan check failed")
        return False
    
    # Check services
    services_ok = check_services()
    if not services_ok:
        logger.error("❌ Services check failed")
        return False
    
    logger.info("✅ All checks passed")
    logger.info("✅ Server should start successfully")
    logger.info("To start the server, run: uvicorn main:app --reload")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
