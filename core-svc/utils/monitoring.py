"""
Monitoring and Observability - Phase 1
Basic Prometheus metrics as recommended by expert analysis
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Request
import time
import structlog

logger = structlog.get_logger()

# Prometheus metrics
VIDEO_REQUESTS_TOTAL = Counter(
    'video_requests_total',
    'Total number of video processing requests',
    ['status', 'language']
)

VIDEO_PROCESSING_DURATION = Histogram(
    'video_processing_duration_seconds',
    'Time spent processing videos',
    ['language', 'num_clips']
)

ACTIVE_PROCESSING_JOBS = Gauge(
    'active_processing_jobs',
    'Number of currently processing video jobs'
)

API_REQUEST_DURATION = Histogram(
    'api_request_duration_seconds',
    'Time spent on API requests',
    ['method', 'endpoint', 'status']
)

CELERY_TASK_DURATION = Histogram(
    'celery_task_duration_seconds',
    'Time spent on Celery tasks',
    ['task_name', 'status']
)

FFMPEG_EXECUTIONS = Counter(
    'ffmpeg_executions_total',
    'Total number of ffmpeg executions',
    ['operation', 'status']
)

GPU_MEMORY_USAGE = Gauge(
    'gpu_memory_usage_bytes',
    'GPU memory usage in bytes'
)


class MetricsMiddleware:
    """FastAPI middleware for request metrics"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time.time()
        request = Request(scope, receive)
        
        # Wrapper to capture response
        status_code = 500
        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            # Record metrics
            duration = time.time() - start_time
            method = request.method
            path = request.url.path
            
            # Normalize endpoint paths to avoid high cardinality
            endpoint = self._normalize_endpoint(path)
            
            API_REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint,
                status=str(status_code)
            ).observe(duration)
    
    def _normalize_endpoint(self, path: str) -> str:
        """Normalize API paths to reduce cardinality"""
        # Replace UUIDs and IDs with placeholder
        import re
        normalized = re.sub(r'/[0-9a-f-]{36}', '/{id}', path)  # UUIDs
        normalized = re.sub(r'/\d+', '/{id}', normalized)      # Numeric IDs
        return normalized


def track_video_request(status: str, language: str):
    """Track video processing request"""
    VIDEO_REQUESTS_TOTAL.labels(status=status, language=language).inc()


def track_processing_duration(duration: float, language: str, num_clips: int):
    """Track video processing duration"""
    VIDEO_PROCESSING_DURATION.labels(
        language=language, 
        num_clips=str(num_clips)
    ).observe(duration)


def track_celery_task(task_name: str, duration: float, status: str):
    """Track Celery task execution"""
    CELERY_TASK_DURATION.labels(
        task_name=task_name,
        status=status
    ).observe(duration)


def track_ffmpeg_execution(operation: str, status: str):
    """Track ffmpeg execution"""
    FFMPEG_EXECUTIONS.labels(operation=operation, status=status).inc()


def set_active_jobs(count: int):
    """Set number of active processing jobs"""
    ACTIVE_PROCESSING_JOBS.set(count)


def update_gpu_memory_usage():
    """Update GPU memory usage metrics"""
    try:
        import torch
        if torch.cuda.is_available():
            memory_allocated = torch.cuda.memory_allocated()
            GPU_MEMORY_USAGE.set(memory_allocated)
            logger.debug("GPU memory updated", memory_bytes=memory_allocated)
    except Exception as e:
        logger.warning("Failed to update GPU memory metrics", error=str(e))


def get_metrics():
    """Get Prometheus metrics in text format"""
    return generate_latest()


# Health check functions
def check_redis_health() -> bool:
    """Check Redis connectivity"""
    try:
        import redis
        from ..config import REDIS_URL
        
        r = redis.from_url(REDIS_URL)
        r.ping()
        return True
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return False


def check_database_health() -> bool:
    """Check database connectivity"""
    try:
        from ..models.database import SessionLocal
        
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return True
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return False


def check_gpu_health() -> dict:
    """Check GPU availability and status"""
    try:
        import torch
        
        if torch.cuda.is_available():
            device_count = torch.cuda.device_count()
            current_device = torch.cuda.current_device()
            device_name = torch.cuda.get_device_name(current_device)
            memory_allocated = torch.cuda.memory_allocated()
            memory_total = torch.cuda.get_device_properties(current_device).total_memory
            
            return {
                "available": True,
                "device_count": device_count,
                "current_device": current_device,
                "device_name": device_name,
                "memory_allocated": memory_allocated,
                "memory_total": memory_total,
                "memory_usage_pct": (memory_allocated / memory_total) * 100
            }
        else:
            return {"available": False, "reason": "CUDA not available"}
            
    except Exception as e:
        logger.error("GPU health check failed", error=str(e))
        return {"available": False, "error": str(e)}


def get_health_status() -> dict:
    """Get comprehensive health status"""
    return {
        "redis": check_redis_health(),
        "database": check_database_health(),
        "gpu": check_gpu_health()
    }