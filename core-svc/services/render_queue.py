"""
Render Queue Management - Phase 5A
Distributed task queue for GPU rendering operations
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
import json

from celery import Celery
from celery.result import AsyncResult
from redis import Redis
from pydantic import BaseModel

from ..models.schemas import EDL, RenderingJob, JobStatus, RenderConfig
from .gpu_renderer import get_renderer, RenderConfig as GPURenderConfig


logger = logging.getLogger(__name__)


class JobPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class RenderJobRequest(BaseModel):
    """Request model for rendering jobs"""
    project_id: str
    edl: EDL
    source_video_url: str
    output_format: str = "mp4"
    priority: JobPriority = JobPriority.NORMAL
    callback_url: Optional[str] = None
    metadata: Dict[str, Any] = {}


class RenderQueueManager:
    """
    Advanced queue management for GPU rendering operations
    Handles job prioritization, resource allocation, and monitoring
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis = Redis.from_url(redis_url)
        self.celery_app = self._create_celery_app(redis_url)
        self.job_timeout = 3600  # 1 hour timeout
        self.max_retries = 3
        
        # Queue metrics
        self.queue_metrics = {
            "jobs_submitted": 0,
            "jobs_completed": 0,
            "jobs_failed": 0,
            "average_wait_time": 0.0,
            "average_processing_time": 0.0
        }
    
    def _create_celery_app(self, redis_url: str) -> Celery:
        """Create and configure Celery application"""
        app = Celery('render_queue')
        app.conf.update(
            broker_url=redis_url,
            result_backend=redis_url,
            task_serializer='json',
            accept_content=['json'],
            result_serializer='json',
            timezone='UTC',
            enable_utc=True,
            task_track_started=True,
            task_time_limit=self.job_timeout,
            worker_prefetch_multiplier=1,  # Important for GPU resource management
            task_acks_late=True,
            worker_disable_rate_limits=False,
            task_routes={
                'render_queue.render_edl': {'queue': 'gpu_render'},
                'render_queue.health_check': {'queue': 'monitoring'},
            }
        )
        return app
    
    async def submit_render_job(self, request: RenderJobRequest) -> str:
        """
        Submit a new rendering job to the queue
        
        Args:
            request: Rendering job request
            
        Returns:
            Job ID for tracking
        """
        job_id = str(uuid.uuid4())
        
        try:
            # Store job metadata
            job_data = {
                "id": job_id,
                "project_id": request.project_id,
                "status": JobStatus.PENDING.value,
                "priority": request.priority.value,
                "submitted_at": datetime.utcnow().isoformat(),
                "edl": request.edl.dict(),
                "source_video_url": request.source_video_url,
                "output_format": request.output_format,
                "callback_url": request.callback_url,
                "metadata": request.metadata,
                "attempts": 0,
                "max_retries": self.max_retries
            }
            
            # Store in Redis
            await self._store_job_data(job_id, job_data)
            
            # Submit to Celery queue
            celery_task = self.celery_app.send_task(
                'render_queue.render_edl',
                args=[job_id],
                kwargs=job_data,
                priority=self._get_priority_value(request.priority),
                queue='gpu_render'
            )
            
            # Update job with Celery task ID
            job_data["celery_task_id"] = celery_task.id
            await self._store_job_data(job_id, job_data)
            
            # Update metrics
            self.queue_metrics["jobs_submitted"] += 1
            await self._update_queue_metrics()
            
            logger.info(f"Submitted render job {job_id} for project {request.project_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to submit render job: {e}")
            raise Exception(f"Job submission failed: {str(e)}")
    
    async def get_job_status(self, job_id: str) -> Optional[RenderingJob]:
        """
        Get current status of a rendering job
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job status or None if not found
        """
        try:
            job_data = await self._get_job_data(job_id)
            if not job_data:
                return None
            
            # Check Celery task status if available
            if "celery_task_id" in job_data:
                celery_result = AsyncResult(job_data["celery_task_id"], app=self.celery_app)
                
                # Update status based on Celery state
                if celery_result.state == "PENDING":
                    job_data["status"] = JobStatus.PENDING.value
                elif celery_result.state == "STARTED":
                    job_data["status"] = JobStatus.PROCESSING.value
                elif celery_result.state == "SUCCESS":
                    job_data["status"] = JobStatus.COMPLETED.value
                    if celery_result.result:
                        job_data["result"] = celery_result.result
                elif celery_result.state == "FAILURE":
                    job_data["status"] = JobStatus.FAILED.value
                    job_data["error"] = str(celery_result.info)
                
                # Update stored data
                await self._store_job_data(job_id, job_data)
            
            return RenderingJob(**job_data)
            
        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {e}")
            return None
    
    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a rendering job
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if cancelled successfully
        """
        try:
            job_data = await self._get_job_data(job_id)
            if not job_data:
                return False
            
            # Cancel Celery task if it exists
            if "celery_task_id" in job_data:
                self.celery_app.control.revoke(job_data["celery_task_id"], terminate=True)
            
            # Update job status
            job_data["status"] = JobStatus.CANCELLED.value
            job_data["cancelled_at"] = datetime.utcnow().isoformat()
            await self._store_job_data(job_id, job_data)
            
            logger.info(f"Cancelled render job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get comprehensive queue statistics"""
        try:
            # Get active jobs count
            active_jobs = await self._count_jobs_by_status(JobStatus.PROCESSING)
            pending_jobs = await self._count_jobs_by_status(JobStatus.PENDING)
            
            # Get GPU renderer health
            renderer = get_renderer()
            gpu_health = await renderer.health_check()
            
            # Calculate queue depth and estimated wait time
            estimated_wait_time = await self._calculate_estimated_wait_time()
            
            stats = {
                "queue_depth": pending_jobs,
                "active_jobs": active_jobs,
                "estimated_wait_time": estimated_wait_time,
                "gpu_health": gpu_health,
                "metrics": self.queue_metrics,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {"error": str(e)}
    
    async def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """
        Clean up old completed/failed jobs
        
        Args:
            max_age_hours: Maximum age of jobs to keep
            
        Returns:
            Number of jobs cleaned up
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        try:
            # Get all job keys
            job_keys = self.redis.keys("job:*")
            
            for key in job_keys:
                job_data = json.loads(self.redis.get(key))
                
                # Check if job is old and completed/failed
                submitted_at = datetime.fromisoformat(job_data["submitted_at"])
                status = job_data["status"]
                
                if (submitted_at < cutoff_time and 
                    status in [JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELLED.value]):
                    
                    self.redis.delete(key)
                    cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} old jobs")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old jobs: {e}")
            return 0
    
    # Private helper methods
    
    async def _store_job_data(self, job_id: str, job_data: Dict[str, Any]):
        """Store job data in Redis"""
        key = f"job:{job_id}"
        self.redis.setex(key, 86400 * 7, json.dumps(job_data))  # 7 day TTL
    
    async def _get_job_data(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve job data from Redis"""
        key = f"job:{job_id}"
        data = self.redis.get(key)
        if data:
            return json.loads(data)
        return None
    
    async def _count_jobs_by_status(self, status: JobStatus) -> int:
        """Count jobs with specific status"""
        count = 0
        job_keys = self.redis.keys("job:*")
        
        for key in job_keys:
            job_data = json.loads(self.redis.get(key))
            if job_data["status"] == status.value:
                count += 1
        
        return count
    
    async def _calculate_estimated_wait_time(self) -> float:
        """Calculate estimated wait time for new jobs"""
        pending_jobs = await self._count_jobs_by_status(JobStatus.PENDING)
        active_jobs = await self._count_jobs_by_status(JobStatus.PROCESSING)
        
        if pending_jobs == 0:
            return 0.0
        
        # Estimate based on average processing time and current load
        avg_processing_time = self.queue_metrics.get("average_processing_time", 300.0)
        renderer = get_renderer()
        concurrent_capacity = renderer.max_concurrent_renders
        
        # Simple queue theory estimation
        if active_jobs < concurrent_capacity:
            # Some capacity available
            return (pending_jobs / (concurrent_capacity - active_jobs)) * avg_processing_time
        else:
            # Queue is full
            return pending_jobs * avg_processing_time
    
    def _get_priority_value(self, priority: JobPriority) -> int:
        """Convert priority enum to Celery priority value"""
        priority_map = {
            JobPriority.LOW: 1,
            JobPriority.NORMAL: 5,
            JobPriority.HIGH: 8,
            JobPriority.URGENT: 10
        }
        return priority_map.get(priority, 5)
    
    async def _update_queue_metrics(self):
        """Update queue performance metrics"""
        # Store metrics in Redis for persistence
        metrics_key = "queue:metrics"
        self.redis.setex(metrics_key, 3600, json.dumps(self.queue_metrics))


# Global queue manager instance
_queue_manager: Optional[RenderQueueManager] = None


def get_queue_manager() -> RenderQueueManager:
    """Get or create global queue manager instance"""
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = RenderQueueManager()
    return _queue_manager


# Celery task definitions
@get_queue_manager().celery_app.task(bind=True, name='render_queue.render_edl')
def render_edl_task(self, job_id: str, **job_data):
    """
    Celery task for rendering EDL
    
    Args:
        job_id: Unique job identifier
        **job_data: Job configuration data
    """
    import asyncio
    from ..services.gpu_renderer import render_video_from_edl, RenderConfig
    
    logger.info(f"Starting render job {job_id}")
    
    try:
        # Update job status to processing
        job_data["status"] = JobStatus.PROCESSING.value
        job_data["started_at"] = datetime.utcnow().isoformat()
        
        # Create EDL and config objects
        edl = EDL(**job_data["edl"])
        config = RenderConfig(
            target_format=job_data.get("output_format", "mp4"),
            preset="balanced"
        )
        
        # Run rendering (async function in sync context)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            rendered_videos = loop.run_until_complete(
                render_video_from_edl(
                    edl=edl,
                    source_video_path=job_data["source_video_url"],
                    output_directory=f"/tmp/render_output/{job_id}",
                    config=config
                )
            )
        finally:
            loop.close()
        
        # Prepare result
        result = {
            "job_id": job_id,
            "rendered_videos": [video.dict() for video in rendered_videos],
            "completed_at": datetime.utcnow().isoformat(),
            "success": True
        }
        
        logger.info(f"Completed render job {job_id}: {len(rendered_videos)} clips")
        return result
        
    except Exception as exc:
        logger.error(f"Render job {job_id} failed: {exc}")
        
        # Update job with error
        error_result = {
            "job_id": job_id,
            "error": str(exc),
            "failed_at": datetime.utcnow().isoformat(),
            "success": False
        }
        
        # Retry logic
        job_data["attempts"] = job_data.get("attempts", 0) + 1
        if job_data["attempts"] < job_data.get("max_retries", 3):
            logger.info(f"Retrying job {job_id} (attempt {job_data['attempts']})")
            raise self.retry(countdown=60 * job_data["attempts"])  # Exponential backoff
        
        return error_result


@get_queue_manager().celery_app.task(name='render_queue.health_check')
def health_check_task():
    """Periodic health check task"""
    try:
        renderer = get_renderer()
        health = asyncio.run(renderer.health_check())
        return {"status": "healthy", "details": health}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}