"""
FastAPI application entry point for document processing API.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.api.routes import router
from app.api.quiz_routes import router as quiz_router
from app.db.database import init_db
from app.config import settings

# Create FastAPI application
app = FastAPI(
    title="Document Processing API",
    description="API for processing PDF and PPTX documents with embeddings and vector storage",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api", tags=["documents"])
app.include_router(quiz_router, prefix="/api", tags=["quiz"])


@app.on_event("startup")
async def startup_event():
    """
    Run on application startup.
    Creates necessary directories and validates configuration.
    """
    # Create upload directory if it doesn't exist
    os.makedirs(settings.upload_dir, exist_ok=True)

    # Create ChromaDB directory if it doesn't exist
    os.makedirs(settings.chroma_db_path, exist_ok=True)
    
    # Create data directory for SQLite database
    os.makedirs("app/data", exist_ok=True)
    
    # Initialize database
    init_db()

    print(f"✓ Upload directory: {settings.upload_dir}")
    print(f"✓ ChromaDB path: {settings.chroma_db_path}")
    print(f"✓ Database path: {settings.db_path}")
    print(f"✓ Allowed file types: {', '.join(settings.allowed_extensions)}")
    print(f"✓ Max file size: {settings.max_file_size / (1024 * 1024):.2f} MB")
    print("✓ Application started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Run on application shutdown.
    Cleanup and resource release.
    """
    print("✓ Application shutdown complete")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Document Processing & Quiz Generation API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
        "features": {
            "document_processing": "/api/start-embedding",
            "document_search": "/api/search",
            "collections": "/api/collections",
            "quiz_generation": "/api/quiz/generate",
            "quiz_submission": "/api/quiz/submit",
            "quiz_list": "/api/quiz/list/all"
        }
    }
