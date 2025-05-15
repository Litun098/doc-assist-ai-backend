import os
import logging
import warnings
import tracemalloc
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.documents import router as documents_router
from app.api.agent_routes import router as agent_router
from app.api.llama_index_routes import router as llama_index_router
from app.api.standalone_agent_routes import router as standalone_agent_router
from app.api.simple_combined_routes import router as simple_combined_router
from config.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Start tracemalloc to track memory allocations
tracemalloc.start()

# Suppress ResourceWarnings during development
warnings.filterwarnings("ignore", category=ResourceWarning)

# Import socket cleanup utility and connection pool
from app.utils.socket_cleanup import cleanup_all_resources
from app.utils.connection_pool import connection_pool

# Create uploads directory if it doesn't exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Define lifespan handler
@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Lifespan event handler for FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup: Initialize services safely
    try:
        logger.info("Starting up AnyDocAI server...")

        # Import connection manager first
        from app.utils.connection_manager import connection_manager
        logger.info("Connection manager initialized")

        # Import services here to avoid circular imports
        # We don't need to do anything with them, just importing will initialize them
        from app.services.llama_index_service import llama_index_service
        logger.info("Services initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing services: {str(e)}")
        # Continue even if there's an error - we'll handle it in the routes

    yield

    # Shutdown: Clean up resources
    try:
        logger.info("Shutting down AnyDocAI server...")

        # Close all connections using the connection manager
        from app.utils.connection_manager import connection_manager
        connection_manager.close_all_connections()
        logger.info("All connections closed successfully")

        # Close any remaining service connections
        try:
            from app.services.llama_index_service import llama_index_service
            logger.info("Service connections closed successfully")
        except Exception as e:
            logger.error(f"Error closing service connections: {str(e)}")

        # Final cleanup to prevent ResourceWarnings
        try:
            # Clean up connection pool
            connection_pool.cleanup_all()
            logger.info("Connection pool cleanup completed")

            # Use our comprehensive cleanup utility
            cleanup_all_resources()
            logger.info("Socket cleanup completed")

            # Take a snapshot to check for leaks
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')
            logger.debug("Top 10 memory allocations after cleanup:")
            for stat in top_stats[:10]:
                logger.debug(f"{stat}")

            # Stop tracemalloc
            tracemalloc.stop()
        except Exception as cleanup_error:
            logger.error(f"Error during final cleanup: {str(cleanup_error)}")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered document assistant that lets you chat with all your files",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000","http://192.168.226.219:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(chat_router, prefix=settings.API_PREFIX)
app.include_router(documents_router, prefix=settings.API_PREFIX)
app.include_router(agent_router, prefix=settings.API_PREFIX)
app.include_router(llama_index_router, prefix=settings.API_PREFIX)

# Mount Standalone Agent routes
app.include_router(standalone_agent_router, prefix=settings.API_PREFIX)

# Mount Simple Combined Agent routes
app.include_router(simple_combined_router, prefix=settings.API_PREFIX)

# Mount static files for uploads (for development only)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "AI-powered document assistant that lets you chat with all your files",
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
