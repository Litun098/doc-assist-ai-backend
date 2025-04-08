import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    # App settings
    APP_NAME = os.getenv("APP_NAME", "AnyDocAI")
    APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    
    # API settings
    API_PREFIX = "/api"
    
    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Supabase
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    
    # Weaviate
    WEAVIATE_URL = os.getenv("WEAVIATE_URL")
    WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
    
    # S3 Storage (Wasabi)
    S3_ENDPOINT = os.getenv("S3_ENDPOINT")
    S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
    S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
    S3_REGION = os.getenv("S3_REGION")
    
    # Redis (for Celery)
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # File upload settings
    UPLOAD_DIR = "uploads"
    MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS = {
        "pdf", "docx", "doc", "xlsx", "xls", "pptx", "ppt", "txt"
    }
    
    # Chunking settings
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    
    # Model settings
    DEFAULT_MODEL = "gpt-4-turbo"
    FREE_MODEL = "gpt-3.5-turbo"
    EMBEDDING_MODEL = "text-embedding-3-small"
    VISION_MODEL = "gpt-4-vision-preview"

settings = Settings()
