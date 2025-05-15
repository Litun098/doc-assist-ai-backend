import os
from dotenv import load_dotenv
from app.models.db_models import FileType

# Load environment variables from .env file
load_dotenv()

class Settings:
    # App settings
    APP_NAME = os.getenv("APP_NAME", "AnyDocAI")
    APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

    # API settings
    API_PREFIX = "/api"

    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # Supabase
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

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
    UPSTASH_REDIS_REST_URL = os.getenv("UPSTASH_REDIS_REST_URL")
    UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    UPSTASH_REDIS_PORT = int(os.getenv("UPSTASH_REDIS_PORT", "6379"))

    # Use Upstash Redis if configured
    USE_UPSTASH_REDIS = bool(UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN)

    # Fallback to local Redis if Upstash is not configured
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # For Celery with Upstash Redis
    CELERY_BROKER_USE_SSL = {
        'ssl_cert_reqs': 'CERT_NONE'
    } if REDIS_URL and REDIS_URL.startswith('rediss://') else None

    # File upload settings
    UPLOAD_DIR = "uploads"
    MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS = {
        "pdf", "docx", "doc", "xlsx", "xls", "pptx", "ppt", "txt"
    }

    # Chunking settings
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    MAX_CHUNK_SIZE = 2000  # Maximum size for any chunk
    MIN_CHUNK_SIZE = 100   # Minimum size for any chunk

    # Topic chunking settings
    HEADING_PATTERNS = [
        # Markdown headings
        r'^#{1,6}\s+(.+)$',
        # Underlined headings (===== or -----)
        r'^([^\n]+)\n[=\-]{3,}$',
        # Numbered headings (1. Title, 1.1 Subtitle, etc.)
        r'^\d+(\.\d+)*\s+(.+)$',
        # Common heading patterns (TITLE:, Chapter X, etc.)
        r'^(CHAPTER|Section|TITLE|PART)\s+\w+:?\s*(.+)$'
    ]

    # Chunking strategy settings
    TOPIC_BASED_FILETYPES = [FileType.PDF, FileType.DOCX, FileType.TXT]
    FIXED_SIZE_FILETYPES = [FileType.XLSX, FileType.PPTX]

    # Model settings
    DEFAULT_MODEL = "gpt-3.5-turbo"  # Using GPT-3.5 for development
    FREE_MODEL = "gpt-3.5-turbo"
    EMBEDDING_MODEL = "text-embedding-3-small"
    VISION_MODEL = "gpt-4-vision-preview"

    # Future model settings (for production)
    # DEFAULT_MODEL = "gpt-4-turbo"

    # LlamaIndex settings
    LLAMAINDEX_CHUNK_SIZE = 1000
    LLAMAINDEX_CHUNK_OVERLAP = 200
    LLAMAINDEX_SIMILARITY_TOP_K = 5  # Number of chunks to retrieve for each query
    LLAMAINDEX_INDEX_NAME = "DocumentChunks"  # Base name of the index in Weaviate (user ID will be appended)

    # Weaviate batch processing settings
    WEAVIATE_BATCH_SIZE = 50  # Maximum number of objects to send in a single batch
    WEAVIATE_BATCH_TIMEOUT = 120  # Timeout in seconds for batch operations
    WEAVIATE_BATCH_NUM_WORKERS = 1  # Number of workers for batch processing
    WEAVIATE_MAX_RETRIES = 5  # Maximum number of retries for failed operations

settings = Settings()
