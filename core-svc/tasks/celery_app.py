"""
Celery Application Configuration - Phase 1
Single process_video task as recommended by expert analysis
"""

from celery import Celery
from ..config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND, CELERY_TASK_ROUTES

# Create Celery app
celery_app = Celery("shorts_editor")

# Configure Celery
celery_app.conf.update(
    broker_url=CELERY_BROKER_URL,
    result_backend=CELERY_RESULT_BACKEND,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes=CELERY_TASK_ROUTES,
    worker_max_tasks_per_child=1,  # Prevent memory leaks from ffmpeg
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # One task at a time per worker
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 minutes soft limit
)

# Import tasks to register them
from . import video_processor  # noqa
from . import edl_tasks  # noqa