import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from config.config import settings

# Create uploads directory if it doesn't exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered document assistant that lets you chat with all your files",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router, prefix=settings.API_PREFIX)

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
