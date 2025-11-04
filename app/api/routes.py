"""
API routes for document processing with queue system.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Query
from typing import Optional, List, Dict, Any
import os
import shutil
from datetime import datetime
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.models.job import Job, JobResponse
from app.services.queue_manager import queue_manager
from app.workers.tasks import process_document_task
from app.config import settings

router = APIRouter()


def get_file_extension(filename: str) -> str:
    """Extract file extension from filename."""
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def validate_file(file: UploadFile) -> str:
    """
    Validate uploaded file type and size.

    Returns:
        File extension if valid

    Raises:
        HTTPException if validation fails
    """
    # Check file extension
    file_ext = get_file_extension(file.filename)
    if file_ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(settings.allowed_extensions)}"
        )

    return file_ext


async def save_upload_file(upload_file: UploadFile, destination: str) -> None:
    """Save uploaded file to destination path."""
    os.makedirs(os.path.dirname(destination), exist_ok=True)

    with open(destination, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)


@router.post("/start-embedding", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_embedding(
    file: UploadFile = File(..., description="PDF or PPTX file to process"),
    collection_name: Optional[str] = Form(None, description="ChromaDB collection name")
):
    """
    Upload a document and start embedding process asynchronously.

    Returns immediately with a job_id. Use the job-status endpoint to check progress.

    - **file**: The document file to process (PDF or PPTX)
    - **collection_name**: Optional name for the ChromaDB collection (defaults to filename)

    Returns:
        Job ID and status for tracking the processing
    """
    # Validate file
    file_ext = validate_file(file)

    # Set collection name (default to filename without extension)
    if not collection_name:
        collection_name = file.filename.rsplit(".", 1)[0].replace(" ", "_").lower()

    # Generate unique filename for storage
    temp_filename = f"{datetime.utcnow().timestamp()}_{file.filename}"
    file_path = os.path.join(settings.upload_dir, temp_filename)

    try:
        # Save uploaded file
        await save_upload_file(file, file_path)

        # Create job in Redis
        job_id = queue_manager.create_job(
            file_name=file.filename,
            file_type=file_ext,
            file_path=file_path,
            collection_name=collection_name
        )

        # Queue the processing task (Celery)
        process_document_task.delay(job_id)

        return JobResponse(
            job_id=job_id,
            status="queued",
            message="Job created successfully. Use job_id to check status."
        )

    except Exception as e:
        # Clean up file if job creation fails
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating job: {str(e)}"
        )


@router.get("/job-status/{job_id}", response_model=Job)
async def get_job_status(job_id: str):
    """
    Get the status and progress of a processing job.

    - **job_id**: UUID of the job to check

    Returns:
        Complete job information including status, progress, and metadata
    """
    job = queue_manager.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    return job


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns the API status and configuration info.
    """
    try:
        # Test Redis connection
        queue_manager.redis_client.ping()
        redis_status = "connected"
    except Exception as e:
        redis_status = f"disconnected: {str(e)}"

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "redis": redis_status,
        "chroma_db_path": settings.chroma_db_path,
        "allowed_file_types": settings.allowed_extensions,
        "max_file_size_mb": settings.max_file_size / (1024 * 1024)
    }


@router.get("/search", response_model=Dict[str, Any])
async def search_documents(
    query: str = Query(..., description="Search query to find relevant documents"),
    collection_name: str = Query("default_collection", description="ChromaDB collection name to search in"),
    top_k: int = Query(3, ge=1, le=10, description="Number of top relevant documents to return (1-10)")
):
    """
    Search for relevant documents in ChromaDB based on a query.
    
    Returns the top K most similar documents from the specified collection.
    
    - **query**: The search query text
    - **collection_name**: Name of the ChromaDB collection to search (defaults to 'default_collection')
    - **top_k**: Number of top results to return (defaults to 3, max 10)
    
    Returns:
        Dictionary containing search results with documents, distances, and metadata
    """
    if not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty"
        )
    
    try:
        # Ensure ChromaDB directory exists
        if not os.path.exists(settings.chroma_db_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ChromaDB not found. Please upload and process documents first."
            )
        
        # Create ChromaDB client
        client = chromadb.PersistentClient(
            path=settings.chroma_db_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get the collection
        try:
            from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
            embedding_function = DefaultEmbeddingFunction()
            
            collection = client.get_collection(
                name=collection_name,
                embedding_function=embedding_function
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_name}' not found. Available collections can be checked via /api/collections endpoint."
            )
        
        # Perform similarity search
        results = collection.query(
            query_texts=[query],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results
        documents = []
        for i in range(len(results["documents"][0])):
            documents.append({
                "id": results["ids"][0][i] if "ids" in results else f"doc_{i}",
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results["metadatas"] and results["metadatas"][0] else {},
                "similarity_score": 1 - results["distances"][0][i] if results["distances"] else None,  # Convert distance to similarity
                "distance": results["distances"][0][i] if results["distances"] else None
            })
        
        return {
            "query": query,
            "collection_name": collection_name,
            "total_results": len(documents),
            "documents": documents,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching documents: {str(e)}"
        )


@router.get("/collections", response_model=Dict[str, Any])
async def list_collections():
    """
    List all available ChromaDB collections.
    
    Returns:
        Dictionary containing list of available collections with their metadata
    """
    try:
        # Ensure ChromaDB directory exists
        if not os.path.exists(settings.chroma_db_path):
            return {
                "collections": [],
                "message": "ChromaDB not found. Please upload and process documents first.",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Create ChromaDB client
        client = chromadb.PersistentClient(
            path=settings.chroma_db_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # List all collections
        collections = client.list_collections()
        
        collection_info = []
        for collection in collections:
            try:
                # Get collection details
                col = client.get_collection(collection.name)
                count = col.count()
                
                collection_info.append({
                    "name": collection.name,
                    "id": collection.id,
                    "document_count": count,
                    "metadata": collection.metadata if hasattr(collection, 'metadata') else {}
                })
            except Exception as e:
                collection_info.append({
                    "name": collection.name,
                    "id": collection.id,
                    "document_count": "unknown",
                    "error": str(e)
                })
        
        return {
            "collections": collection_info,
            "total_collections": len(collection_info),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing collections: {str(e)}"
        )
