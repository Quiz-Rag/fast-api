"""
Job queue management using Redis.
Handles job creation, status tracking, and progress updates.
"""

import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
import redis

from app.config import settings
from app.models.job import Job, JobStatus, JobProgress, JobMetadata, BatchInfo, BatchFileInfo


class QueueManager:
    """Manages job queue and status using Redis."""

    def __init__(self):
        """Initialize Redis connection."""
        self.redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True
        )

    def _get_job_key(self, job_id: str) -> str:
        """Generate Redis key for job."""
        return f"job:{job_id}"

    def create_job(
        self,
        file_name: str,
        file_type: str,
        file_path: str,
        collection_name: str
    ) -> str:
        """
        Create a new job and store in Redis.

        Args:
            file_name: Original filename
            file_type: File extension (pdf/pptx)
            file_path: Path to uploaded file
            collection_name: ChromaDB collection name

        Returns:
            job_id: UUID of created job
        """
        job_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()

        job_data = {
            "job_id": job_id,
            "status": JobStatus.QUEUED.value,
            "file_name": file_name,
            "file_type": file_type,
            "file_path": file_path,
            "collection_name": collection_name,
            "created_at": created_at,
            "started_at": None,
            "completed_at": None,
            "progress": None,
            "metadata": None,
            "error": None,
        }

        # Store in Redis with TTL
        key = self._get_job_key(job_id)
        self.redis_client.setex(
            key,
            settings.job_ttl,
            json.dumps(job_data)
        )

        return job_id

    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Retrieve job from Redis.

        Args:
            job_id: Job UUID

        Returns:
            Job object or None if not found
        """
        key = self._get_job_key(job_id)
        data = self.redis_client.get(key)

        if not data:
            return None

        job_dict = json.loads(data)

        # Convert ISO strings back to datetime
        if job_dict.get("created_at"):
            job_dict["created_at"] = datetime.fromisoformat(job_dict["created_at"])
        if job_dict.get("started_at"):
            job_dict["started_at"] = datetime.fromisoformat(job_dict["started_at"])
        if job_dict.get("completed_at"):
            job_dict["completed_at"] = datetime.fromisoformat(job_dict["completed_at"])

        # Convert progress dict to JobProgress model
        if job_dict.get("progress"):
            job_dict["progress"] = JobProgress(**job_dict["progress"])

        # Convert metadata dict to JobMetadata model
        if job_dict.get("metadata"):
            job_dict["metadata"] = JobMetadata(**job_dict["metadata"])

        # Convert batch dict to BatchInfo model
        if job_dict.get("is_batch") and job_dict.get("batch"):
            batch_data = job_dict["batch"]
            batch_data["files"] = [BatchFileInfo(**f) for f in batch_data.get("files", [])]
            job_dict["batch"] = BatchInfo(**batch_data)

        # Remove file_path from response (internal only)
        job_dict.pop("file_path", None)
        job_dict.pop("file_paths", None)

        return Job(**job_dict)

    def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update job status in Redis.

        Args:
            job_id: Job UUID
            status: New job status
            started_at: Processing start time (optional)
            completed_at: Processing completion time (optional)
            error: Error message if failed (optional)
            metadata: Job metadata when completed (optional)

        Returns:
            True if updated successfully, False otherwise
        """
        key = self._get_job_key(job_id)
        data = self.redis_client.get(key)

        if not data:
            return False

        job_data = json.loads(data)
        job_data["status"] = status.value

        if started_at:
            job_data["started_at"] = started_at.isoformat()
        if completed_at:
            job_data["completed_at"] = completed_at.isoformat()
        if error:
            job_data["error"] = error
        if metadata:
            job_data["metadata"] = metadata

        # Update in Redis with same TTL
        self.redis_client.setex(
            key,
            settings.job_ttl,
            json.dumps(job_data)
        )

        return True

    def update_job_progress(
        self,
        job_id: str,
        current_step: str,
        percentage: float,
        chunks_processed: int = 0,
        total_chunks: int = 0
    ) -> bool:
        """
        Update job progress in Redis.

        Args:
            job_id: Job UUID
            current_step: Current processing step
            percentage: Completion percentage (0-100)
            chunks_processed: Number of chunks processed
            total_chunks: Total number of chunks

        Returns:
            True if updated successfully, False otherwise
        """
        key = self._get_job_key(job_id)
        data = self.redis_client.get(key)

        if not data:
            return False

        job_data = json.loads(data)
        job_data["progress"] = {
            "current_step": current_step,
            "percentage": percentage,
            "chunks_processed": chunks_processed,
            "total_chunks": total_chunks,
        }

        # Update in Redis with same TTL
        self.redis_client.setex(
            key,
            settings.job_ttl,
            json.dumps(job_data)
        )

        return True

    def get_job_file_path(self, job_id: str) -> Optional[str]:
        """
        Get file path for a job (internal use).

        Args:
            job_id: Job UUID

        Returns:
            File path or None if not found
        """
        key = self._get_job_key(job_id)
        data = self.redis_client.get(key)

        if not data:
            return None

        job_data = json.loads(data)
        return job_data.get("file_path")

    def create_batch_job(
        self,
        files: List[Dict[str, str]],
        collection_name: str
    ) -> str:
        """
        Create a new batch job and store in Redis.

        Args:
            files: List of file dicts with 'path', 'name', 'type'
            collection_name: ChromaDB collection name

        Returns:
            job_id: UUID of created batch job
        """
        job_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()

        # Create file info list
        batch_files = [
            {
                "name": f["name"],
                "status": "pending",
                "chunks": 0,
                "error": None
            }
            for f in files
        ]

        job_data = {
            "job_id": job_id,
            "status": JobStatus.QUEUED.value,
            "file_name": f"batch_{len(files)}_files",
            "file_type": "batch",
            "file_paths": [f["path"] for f in files],  # Store all file paths
            "collection_name": collection_name,
            "created_at": created_at,
            "started_at": None,
            "completed_at": None,
            "progress": None,
            "metadata": None,
            "error": None,
            "is_batch": True,
            "batch": {
                "total_files": len(files),
                "processed_files": 0,
                "current_file": None,
                "overall_progress": 0.0,
                "files": batch_files
            }
        }

        # Store in Redis with TTL
        key = self._get_job_key(job_id)
        self.redis_client.setex(
            key,
            settings.job_ttl,
            json.dumps(job_data)
        )

        return job_id

    def update_batch_file_status(
        self,
        job_id: str,
        file_name: str,
        status: str,
        chunks: int = 0,
        error: Optional[str] = None
    ) -> bool:
        """
        Update status of a specific file in batch job.

        Args:
            job_id: Job UUID
            file_name: Name of the file to update
            status: File status (pending, processing, completed, failed)
            chunks: Number of chunks created (if completed)
            error: Error message (if failed)

        Returns:
            True if updated successfully, False otherwise
        """
        key = self._get_job_key(job_id)
        data = self.redis_client.get(key)

        if not data:
            return False

        job_data = json.loads(data)
        
        if not job_data.get("is_batch"):
            return False

        # Update specific file
        for file_info in job_data["batch"]["files"]:
            if file_info["name"] == file_name:
                file_info["status"] = status
                file_info["chunks"] = chunks
                if error:
                    file_info["error"] = error
                break

        # Update current file
        if status == "processing":
            job_data["batch"]["current_file"] = file_name

        # Update in Redis
        self.redis_client.setex(
            key,
            settings.job_ttl,
            json.dumps(job_data)
        )

        return True

    def update_batch_progress(
        self,
        job_id: str,
        processed_files: int
    ) -> bool:
        """
        Update batch processing progress.

        Args:
            job_id: Job UUID
            processed_files: Number of files completed

        Returns:
            True if updated successfully, False otherwise
        """
        key = self._get_job_key(job_id)
        data = self.redis_client.get(key)

        if not data:
            return False

        job_data = json.loads(data)
        
        if not job_data.get("is_batch"):
            return False

        total_files = job_data["batch"]["total_files"]
        job_data["batch"]["processed_files"] = processed_files
        job_data["batch"]["overall_progress"] = (processed_files / total_files) * 100

        # Update in Redis
        self.redis_client.setex(
            key,
            settings.job_ttl,
            json.dumps(job_data)
        )

        return True

    def get_batch_file_paths(self, job_id: str) -> Optional[List[str]]:
        """
        Get file paths for a batch job (internal use).

        Args:
            job_id: Job UUID

        Returns:
            List of file paths or None if not found
        """
        key = self._get_job_key(job_id)
        data = self.redis_client.get(key)

        if not data:
            return None

        job_data = json.loads(data)
        return job_data.get("file_paths")

    def delete_job(self, job_id: str) -> bool:
        """
        Delete job from Redis.

        Args:
            job_id: Job UUID

        Returns:
            True if deleted successfully, False otherwise
        """
        key = self._get_job_key(job_id)
        return self.redis_client.delete(key) > 0


# Global queue manager instance
queue_manager = QueueManager()
