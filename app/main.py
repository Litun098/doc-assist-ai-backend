"""
Main application file.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import socketio

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
        logger.info("Shutting down AnyDocAI server...")

        # Close service connections
        try:
            # Close LlamaIndex service connections
            from app.services.llama_index_service import llama_index_service
            llama_index_service.close_connections()

            # Close document processor connections
            from app.services.document_processor import document_processor
            document_processor.close_connections()

            # Close RAG service connections
            from app.services.rag_service import rag_service
            rag_service.close_connections()

            # Close embedder service connections
            from app.services.embedder import embedder_service
            embedder_service.close_connections()

            logger.info("Service connections closed successfully")
        except Exception as e:
            logger.error(f"Error closing service connections: {str(e)}")

        # Close connection manager connections
        try:
            from app.utils.connection_manager import connection_manager
            connection_manager.close_all_connections()
            logger.info("Connection manager cleanup completed")
        except Exception as e:
            logger.error(f"Error in connection manager cleanup: {str(e)}")

        # Final resource cleanup
        try:
            from app.utils.socket_cleanup import cleanup_all_resources
            cleanup_all_resources()
            logger.info("Final resource cleanup completed")
        except Exception as e:
            logger.error(f"Error in final resource cleanup: {str(e)}")

    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

# Initialize WebSocket manager
from app.services.websocket_manager import websocket_manager

# Create FastAPI app with lifespan handler
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# Mount SocketIO - Create the combined app
socket_app = socketio.ASGIApp(websocket_manager.sio, app)

# Add CORS middleware
# Define allowed origins based on environment
allowed_origins = [
    "http://localhost:3000",  # Next.js development server
    "http://127.0.0.1:3000",
    "http://localhost:8000",  # FastAPI development server
    "http://127.0.0.1:8000",
    "http://localhost:5500",  # Live Server port
    "http://127.0.0.1:5500",
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




