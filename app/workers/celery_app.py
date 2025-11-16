"""
Celery application configuration for background task processing.
"""

import logging
from celery import Celery
from celery.signals import setup_logging
from app.config import settings

# Initialize Celery app
celery_app = Celery(
    "document_processor",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max per task
    task_soft_time_limit=540,  # 9 minutes soft limit
    worker_prefetch_multiplier=1,  # Process one task at a time
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
)

# Configure logging for Celery workers
@setup_logging.connect
def config_loggers(*args, **kwargs):
    """Configure logging for Celery workers."""
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Set specific loggers to INFO level
    logging.getLogger('app.workers.tasks').setLevel(logging.INFO)
    logging.getLogger('app.services.embed_utils').setLevel(logging.INFO)
