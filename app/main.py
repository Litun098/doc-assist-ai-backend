"""
Main application file.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.api import api_router
from app.middleware import add_security_headers_middleware, add_rate_limit_middleware
from config.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Define lifespan handler
@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Lifespan event handler for FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup: Initialize services safely
    try:
        # Import here to avoid circular imports
        from app.services.llama_index_service import llama_index_service
        logger.info("Services initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing services: {str(e)}")
        # Continue even if there's an error - we'll handle it in the routes

    yield

    # Shutdown: Clean up resources
    try:
        from app.services.llama_index_service import llama_index_service
        if hasattr(llama_index_service, 'weaviate_client') and llama_index_service.weaviate_client:
            try:
                llama_index_service.weaviate_client.close()
                logger.info("Weaviate connection closed successfully")
            except Exception as e:
                logger.error(f"Error closing Weaviate connection: {str(e)}")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

# Create FastAPI app with lifespan handler
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# Add CORS middleware
# Define allowed origins based on environment
allowed_origins = [
    "http://localhost:3000",  # Next.js development server
    "http://127.0.0.1:3000",
    "http://localhost:8000",  # FastAPI development server
    "http://127.0.0.1:8000",
]

# Add production origins if not in development
if getattr(settings, 'ENVIRONMENT', 'development') != "development":
    allowed_origins.extend([
        "https://anydocai.com",
        "https://www.anydocai.com",
        # Add any other production domains here
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Specify allowed origins for security
    allow_credentials=True,  # Required for cookies to work
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
    expose_headers=["Set-Cookie"],
)

# Add security headers middleware
add_security_headers_middleware(app)

# Add rate limiting middleware
add_rate_limit_middleware(app)

# Include API router
app.include_router(api_router, prefix=settings.API_PREFIX)

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "version": settings.APP_VERSION,
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


