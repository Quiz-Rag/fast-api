from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    """Job processing status."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"


class JobProgress(BaseModel):
    """Progress information for a job."""
    current_step: str
    percentage: float = Field(ge=0, le=100)
    chunks_processed: int = 0
    total_chunks: int = 0


class BatchFileInfo(BaseModel):
    """Information about a single file in a batch."""
    name: str
    status: str  # pending, processing, completed, failed
    chunks: int = 0
    error: Optional[str] = None


class BatchInfo(BaseModel):
    """Batch processing information."""
    total_files: int
    processed_files: int
    current_file: Optional[str] = None
    overall_progress: float = Field(ge=0, le=100)
    files: List[BatchFileInfo] = []
    
    @property
    def successful_files(self) -> int:
        """Calculate number of successfully processed files."""
        return sum(1 for f in self.files if f.status == "completed")
    
    @property
    def failed_files(self) -> int:
        """Calculate number of failed files."""
        return sum(1 for f in self.files if f.status == "failed")
    
    @property
    def total_chunks(self) -> int:
        """Calculate total chunks from all completed files."""
        return sum(f.chunks for f in self.files if f.status == "completed")


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
    is_batch: bool = False
    batch: Optional[BatchInfo] = None

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
