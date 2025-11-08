from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    """Job processing status."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobProgress(BaseModel):
    """Progress information for a job."""
    current_step: str
    percentage: float = Field(ge=0, le=100)
    chunks_processed: int = 0
    total_chunks: int = 0


class JobBase(BaseModel):
    """Base job information."""
    file_name: str
    file_type: str
    collection_name: str


class JobCreate(JobBase):
    """Schema for creating a new job."""
    pass


class JobMetadata(BaseModel):
    """Metadata for completed job."""
    chunks_count: int
    text_length: int
    processing_time_seconds: float


class Job(JobBase):
    """Complete job information."""
    job_id: str
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: Optional[JobProgress] = None
    metadata: Optional[JobMetadata] = None
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "file_name": "document.pdf",
                "file_type": "pdf",
                "collection_name": "my_collection",
                "status": "processing",
                "created_at": "2025-11-04T10:30:00Z",
                "started_at": "2025-11-04T10:30:05Z",
                "progress": {
                    "current_step": "generating_embeddings",
                    "percentage": 50.0,
                    "chunks_processed": 10,
                    "total_chunks": 20
                }
            }
        }


class JobResponse(BaseModel):
    """Response schema for job operations."""
    job_id: str
    status: str
    message: str


class ProcessResponse(BaseModel):
    """Response schema for successful processing."""
    job_id: str
    status: str
    chunks_count: int
    collection_name: str
    message: str
