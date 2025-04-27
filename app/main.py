"""
Main application file.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.api import api_router
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
    # Startup: Nothing to do here for now
    yield

    # Shutdown: Clean up resources
    from app.services.llama_index_service import llama_index_service
    if hasattr(llama_index_service, 'weaviate_client') and llama_index_service.weaviate_client:
        try:
            llama_index_service.weaviate_client.close()
            logger.info("Weaviate connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing Weaviate connection: {str(e)}")

# Create FastAPI app with lifespan handler
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, you should specify the allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


