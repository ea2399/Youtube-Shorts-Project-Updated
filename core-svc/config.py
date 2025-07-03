"""
Configuration Settings - Phase 1
Combines existing config with new service requirements
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database Configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/shorts_editor"
)

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Celery Configuration
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = DATABASE_URL.replace("postgresql://", "db+postgresql://")

# OpenAI Configuration (from existing config)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4.1"  # Using gpt-4.1 for larger context window

# FFmpeg Configuration (from existing config)
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")

# Video Processing Settings (from existing config)
DEFAULT_LANGUAGE = "he"  # Hebrew
TARGET_LUFS = -23  # Target loudness level for normalization
MIN_CLIP_DURATION = 30  # seconds
MAX_CLIP_DURATION = 60  # seconds

# Output Settings (from existing config)
VERTICAL_WIDTH = 720
VERTICAL_HEIGHT = 1280

# File Storage Configuration
STORAGE_PATH = Path(os.getenv("STORAGE_PATH", "/tmp/shorts_editor"))
STORAGE_PATH.mkdir(parents=True, exist_ok=True)

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_WORKERS = int(os.getenv("API_WORKERS", "1"))

# Security Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Task Queue Configuration
CELERY_TASK_ROUTES = {
    'core_svc.tasks.process_video': {'queue': 'video_processing'},
    'core_svc.tasks.health_check': {'queue': 'health'},
    # Phase 2 Intelligence Engine routing
    'intelligence_tasks.process_audio_task': {'queue': 'cpu_queue'},
    'intelligence_tasks.process_visual_task': {'queue': 'gpu_queue'},
    'intelligence_tasks.generate_proxy_task': {'queue': 'cpu_queue'},
    'intelligence_tasks.calculate_quality_metrics_task': {'queue': 'cpu_queue'},
    'intelligence_tasks.coordination_callback': {'queue': 'cpu_queue'},
    # Phase 3 EDL Generation routing
    'generate_edl_task': {'queue': 'gpu_queue'},           # Multi-modal fusion requires GPU
    'validate_edl_quality_task': {'queue': 'cpu_queue'},   # Quality validation is CPU-intensive
    'regenerate_edl_task': {'queue': 'gpu_queue'},         # Regeneration uses same pipeline
}

# Processing Limits
MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", "2"))
TASK_TIME_LIMIT = 3600  # 1 hour max per task
TASK_SOFT_TIME_LIMIT = 3300  # 55 minutes soft limit

# Validation Settings
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm"}
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
ALLOWED_DOMAINS = {
    "youtube.com", 
    "youtu.be", 
    "storage.googleapis.com",
    "s3.amazonaws.com"
}