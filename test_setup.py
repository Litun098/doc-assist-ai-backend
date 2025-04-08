import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_environment():
    """Check if the environment is properly set up"""
    required_vars = [
        "OPENAI_API_KEY",
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"Missing environment variables: {', '.join(missing_vars)}")
        print("Please set these variables in your .env file")
        return False
    
    return True

def check_directories():
    """Check if required directories exist"""
    required_dirs = [
        "uploads",
    ]
    
    missing_dirs = []
    for dir_name in required_dirs:
        if not os.path.exists(dir_name):
            missing_dirs.append(dir_name)
    
    if missing_dirs:
        print(f"Missing directories: {', '.join(missing_dirs)}")
        print("Creating missing directories...")
        for dir_name in missing_dirs:
            os.makedirs(dir_name, exist_ok=True)
    
    return True

def check_dependencies():
    """Check if required Python packages are installed"""
    try:
        import fastapi
        import uvicorn
        import celery
        import redis
        import langchain
        import openai
        import weaviate
        
        print("All core dependencies are installed")
        return True
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Please install all dependencies with: pip install -r requirements.txt")
        return False

if __name__ == "__main__":
    print("Testing AnyDocAI setup...")
    
    env_ok = check_environment()
    dirs_ok = check_directories()
    deps_ok = check_dependencies()
    
    if env_ok and dirs_ok and deps_ok:
        print("\n✅ Setup looks good! You can start the application with:")
        print("   uvicorn main:app --reload")
        print("\nTo start the Celery worker:")
        print("   celery -A config.celery_worker worker --loglevel=info")
    else:
        print("\n❌ Setup has issues. Please fix them before starting the application.")
        sys.exit(1)
