"""
Celery background tasks for document processing.
"""

import os
import time
import logging
from datetime import datetime

from app.workers.celery_app import celery_app
from app.services.queue_manager import queue_manager
from app.services.embed_utils import (
    extract_text_from_pdf,
    extract_text_from_pptx,
    chunk_text,
    chunk_by_page_or_slide,
    store_in_chroma
)
from app.models.job import JobStatus

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def process_document_task(self, job_id: str):
    """
    Background task to process document: extract, chunk, embed, and store.

    Args:
        job_id: UUID of the job to process

    Returns:
        Dictionary with processing results
    """
    start_time = time.time()

    try:
        # Get job file path from Redis
        file_path = queue_manager.get_job_file_path(job_id)
        if not file_path:
            raise ValueError(f"Job {job_id} not found")

        job = queue_manager.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        # Update status to processing
        queue_manager.update_job_status(
            job_id,
            JobStatus.PROCESSING,
            started_at=datetime.utcnow()
        )
        queue_manager.update_job_progress(
            job_id,
            current_step="text_extraction",
            percentage=0.0
        )

        # Step 1: Extract text from document with page/slide tracking
        # Use original filename (job.file_name) instead of timestamped path for better citations
        source_file = job.file_name
        if job.file_type == "pdf":
            pages = extract_text_from_pdf(file_path)
            if not pages:
                raise ValueError("No text could be extracted from the document")
            total_text_length = sum(len(text) for _, text in pages)
        elif job.file_type == "pptx":
            slides = extract_text_from_pptx(file_path)
            if not slides:
                raise ValueError("No text could be extracted from the document")
            total_text_length = sum(len(text) for _, text in slides)
        else:
            raise ValueError(f"Unsupported file type: {job.file_type}")

        # Update progress
        queue_manager.update_job_progress(
            job_id,
            current_step="text_extraction",
            percentage=25.0
        )

        # Step 2: Chunk by page/slide (one chunk per page/slide)
        if job.file_type == "pdf":
            docs = chunk_by_page_or_slide(
                pages, "pdf", source_file, job.collection_name
            )
        else:  # pptx
            docs = chunk_by_page_or_slide(
                slides, "pptx", source_file, job.collection_name
            )
        total_chunks = len(docs)

        # Update progress
        queue_manager.update_job_progress(
            job_id,
            current_step="chunking",
            percentage=50.0,
            chunks_processed=0,
            total_chunks=total_chunks
        )

        # Step 3: Generate embeddings and store in ChromaDB
        queue_manager.update_job_progress(
            job_id,
            current_step="generating_embeddings",
            percentage=75.0,
            chunks_processed=0,
            total_chunks=total_chunks
        )

        # Store in ChromaDB (this also generates embeddings)
        vector_store = store_in_chroma(docs, job.collection_name)

        # Update progress
        queue_manager.update_job_progress(
            job_id,
            current_step="storing",
            percentage=90.0,
            chunks_processed=total_chunks,
            total_chunks=total_chunks
        )

        # Calculate processing time
        processing_time = time.time() - start_time

        # Step 4: Mark as completed with metadata
        metadata = {
            "chunks_count": total_chunks,
            "text_length": total_text_length,
            "processing_time_seconds": round(processing_time, 2)
        }

        queue_manager.update_job_status(
            job_id,
            JobStatus.COMPLETED,
            completed_at=datetime.utcnow(),
            metadata=metadata
        )

        queue_manager.update_job_progress(
            job_id,
            current_step="completed",
            percentage=100.0,
            chunks_processed=total_chunks,
            total_chunks=total_chunks
        )

        return {
            "job_id": job_id,
            "status": "completed",
            "chunks_count": total_chunks,
            "processing_time": processing_time
        }

    except Exception as e:
        # Handle errors
        error_message = str(e)

        queue_manager.update_job_status(
            job_id,
            JobStatus.FAILED,
            completed_at=datetime.utcnow(),
            error=error_message
        )

        # Log error
        print(f"Error processing job {job_id}: {error_message}")

        # Retry logic for transient errors
        if "OpenAI" in error_message or "timeout" in error_message.lower():
            raise self.retry(exc=e, countdown=60)  # Retry after 60 seconds

        raise

    finally:
        # Clean up uploaded file
        file_path = queue_manager.get_job_file_path(job_id)
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Cleaned up file: {file_path}")
            except Exception as cleanup_error:
                print(f"Error cleaning up file {file_path}: {cleanup_error}")


@celery_app.task(bind=True, max_retries=3)
def process_batch_embedding_task(self, job_id: str, files: list, collection_name: str):
    """
    Background task to process multiple documents in batch.

    Args:
        job_id: UUID of the batch job
        files: List of file dicts with 'path', 'name', 'type'
        collection_name: ChromaDB collection name for all files

    Returns:
        Dictionary with batch processing results
    """
    start_time = time.time()
    total_files = len(files)
    successful_files = 0
    failed_files = 0
    results = []

    try:
        logger.info("=" * 80)
        logger.info(f"🚀 STARTING BATCH EMBEDDING TASK")
        logger.info(f"   Job ID: {job_id}")
        logger.info(f"   Total files: {total_files}")
        logger.info(f"   Collection: {collection_name}")
        logger.info("=" * 80)
        
        # Update status to processing
        queue_manager.update_job_status(
            job_id,
            JobStatus.PROCESSING,
            started_at=datetime.utcnow()
        )

        # Process each file
        for idx, file_info in enumerate(files, 1):
            file_name = file_info["name"]
            file_path = file_info["path"]
            file_type = file_info["type"]

            try:
                logger.info("=" * 80)
                logger.info(f"🔄 PROCESSING FILE {idx}/{total_files}: {file_name}")
                logger.info(f"   Path: {file_path}")
                logger.info(f"   Type: {file_type}")
                logger.info("=" * 80)
                
                # Update current file status to processing
                queue_manager.update_batch_file_status(
                    job_id=job_id,
                    file_name=file_name,
                    status="processing"
                )

                print(f"Processing file {idx}/{total_files}: {file_name}")

                # Step 1: Extract text with page/slide tracking
                logger.info(f"📄 Step 1: Extracting text from {file_name}...")
                # Use original filename (file_name) instead of timestamped path for better citations
                source_file = file_name
                
                if file_type == "pdf":
                    pages = extract_text_from_pdf(file_path)
                    if not pages:
                        raise ValueError("No text could be extracted from the document")
                    logger.info(f"   ✓ Extracted {len(pages)} pages")
                    docs = chunk_by_page_or_slide(
                        pages, "pdf", source_file, collection_name
                    )
                elif file_type == "pptx":
                    slides = extract_text_from_pptx(file_path)
                    if not slides:
                        raise ValueError("No text could be extracted from the document")
                    logger.info(f"   ✓ Extracted {len(slides)} slides")
                    docs = chunk_by_page_or_slide(
                        slides, "pptx", source_file, collection_name
                    )
                else:
                    raise ValueError(f"Unsupported file type: {file_type}")

                total_chunks = len(docs)
                # Calculate total text length from all chunks
                try:
                    total_text_length = sum(len(doc.page_content) for doc in docs if hasattr(doc, 'page_content') and doc.page_content)
                except Exception as e:
                    logger.warning(f"   ⚠ Could not calculate text length: {e}")
                    total_text_length = 0
                logger.info(f"📦 Step 2: Created {total_chunks} chunks from {file_name} (total text: {total_text_length} chars)")

                # Step 3: Store in ChromaDB
                logger.info(f"💾 Step 3: Storing {total_chunks} chunks in ChromaDB (collection: {collection_name})...")
                logger.info(f"   This will generate embeddings using OpenAI text-embedding-3-small...")
                store_in_chroma(docs, collection_name)
                logger.info(f"   ✓ Successfully stored {total_chunks} chunks in ChromaDB")

                # Mark file as completed
                queue_manager.update_batch_file_status(
                    job_id=job_id,
                    file_name=file_name,
                    status="completed",
                    chunks=total_chunks
                )

                successful_files += 1
                results.append({
                    "file": file_name,
                    "status": "completed",
                    "chunks": total_chunks,
                    "text_length": total_text_length
                })

                logger.info(f"✅ SUCCESS: {file_name} - {total_chunks} chunks stored")
                print(f"Successfully processed {file_name}: {total_chunks} chunks")

            except Exception as file_error:
                # Mark file as failed but continue with next file
                error_message = str(file_error)
                import traceback
                error_traceback = traceback.format_exc()
                
                logger.error("=" * 80)
                logger.error(f"❌ FAILED TO PROCESS: {file_name}")
                logger.error(f"   Error: {error_message}")
                logger.error(f"   Traceback:\n{error_traceback}")
                logger.error("=" * 80)
                
                queue_manager.update_batch_file_status(
                    job_id=job_id,
                    file_name=file_name,
                    status="failed",
                    error=error_message
                )

                failed_files += 1
                results.append({
                    "file": file_name,
                    "status": "failed",
                    "error": error_message
                })

                print(f"Failed to process {file_name}: {error_message}")

            finally:
                # Clean up individual file
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"Cleaned up file: {file_path}")
                    except Exception as cleanup_error:
                        print(f"Error cleaning up file {file_path}: {cleanup_error}")

            # Update batch progress
            queue_manager.update_batch_progress(
                job_id=job_id,
                processed_files=idx
            )

        # Calculate processing time
        processing_time = time.time() - start_time

        # Determine final status
        if failed_files == 0:
            final_status = JobStatus.COMPLETED
            status_message = f"All {total_files} files processed successfully"
        elif successful_files == 0:
            final_status = JobStatus.FAILED
            status_message = f"All {total_files} files failed to process"
        else:
            final_status = JobStatus.PARTIALLY_COMPLETED
            status_message = f"{successful_files}/{total_files} files processed successfully"

        # Calculate total chunks and text length
        total_chunks = sum(r.get("chunks", 0) for r in results if r["status"] == "completed")
        total_text_length = sum(r.get("text_length", 0) for r in results if r["status"] == "completed")

        # Mark batch as completed
        metadata = {
            "chunks_count": total_chunks,
            "text_length": total_text_length,
            "processing_time_seconds": round(processing_time, 2),
            "successful_files": successful_files,
            "failed_files": failed_files,
            "total_files": total_files
        }

        queue_manager.update_job_status(
            job_id,
            final_status,
            completed_at=datetime.utcnow(),
            metadata=metadata,
            error=None if failed_files == 0 else f"{failed_files} files failed"
        )

        logger.info("=" * 80)
        logger.info(f"🏁 BATCH JOB COMPLETED: {job_id}")
        logger.info(f"   Status: {status_message}")
        logger.info(f"   Successful: {successful_files}/{total_files}")
        logger.info(f"   Failed: {failed_files}/{total_files}")
        logger.info(f"   Total chunks: {total_chunks}")
        logger.info(f"   Processing time: {round(processing_time, 2)}s")
        logger.info("=" * 80)
        
        print(f"Batch job {job_id} completed: {status_message}")

        return {
            "job_id": job_id,
            "status": final_status.value,
            "total_files": total_files,
            "successful_files": successful_files,
            "failed_files": failed_files,
            "total_chunks": total_chunks,
            "processing_time": processing_time,
            "results": results
        }

    except Exception as e:
        # Handle catastrophic batch errors
        error_message = str(e)
        
        queue_manager.update_job_status(
            job_id,
            JobStatus.FAILED,
            completed_at=datetime.utcnow(),
            error=error_message
        )

        print(f"Catastrophic error in batch job {job_id}: {error_message}")

        # Clean up any remaining files
        for file_info in files:
            file_path = file_info["path"]
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass

        raise
