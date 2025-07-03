"""
GPU Rendering API Endpoints - Phase 5A
REST API for managing rendering jobs and monitoring GPU performance
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse

from ..models.schemas import (
    EDL, RenderingJob, GPUMetrics, JobStatus,
    HealthCheck, ErrorResponse
)
from ..services.render_queue import (
    get_queue_manager, RenderJobRequest, JobPriority
)
from ..services.gpu_renderer import get_renderer, RenderConfig


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/render", tags=["rendering"])


@router.post("/jobs", response_model=Dict[str, str])
async def submit_render_job(
    request: RenderJobRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, str]:
    """
    Submit a new rendering job to the GPU queue
    
    Args:
        request: Rendering job configuration
        background_tasks: FastAPI background tasks
        
    Returns:
        Job ID and submission confirmation
    """
    try:
        queue_manager = get_queue_manager()
        job_id = await queue_manager.submit_render_job(request)
        
        # Add cleanup background task
        background_tasks.add_task(
            _cleanup_old_jobs_background,
            queue_manager
        )
        
        return {
            "job_id": job_id,
            "status": "submitted",
            "message": f"Rendering job submitted successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to submit render job: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Job submission failed: {str(e)}"
        )


@router.get("/jobs/{job_id}", response_model=RenderingJob)
async def get_job_status(job_id: str) -> RenderingJob:
    """
    Get the current status of a rendering job
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        Complete job information and status
    """
    try:
        queue_manager = get_queue_manager()
        job = await queue_manager.get_job_status(job_id)
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        return job
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status for {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve job status: {str(e)}"
        )


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str) -> Dict[str, str]:
    """
    Cancel a pending or running rendering job
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        Cancellation confirmation
    """
    try:
        queue_manager = get_queue_manager()
        success = await queue_manager.cancel_job(job_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found or cannot be cancelled"
            )
        
        return {
            "job_id": job_id,
            "status": "cancelled",
            "message": "Job cancelled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel job: {str(e)}"
        )


@router.get("/queue/stats")
async def get_queue_statistics() -> Dict[str, Any]:
    """
    Get comprehensive queue and rendering statistics
    
    Returns:
        Queue depth, processing times, GPU metrics, and system health
    """
    try:
        queue_manager = get_queue_manager()
        stats = await queue_manager.get_queue_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get queue stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve queue statistics: {str(e)}"
        )


@router.get("/gpu/metrics", response_model=GPUMetrics)
async def get_gpu_metrics() -> GPUMetrics:
    """
    Get current GPU utilization and performance metrics
    
    Returns:
        GPU utilization, memory usage, and temperature
    """
    try:
        renderer = get_renderer()
        metrics = renderer.get_gpu_metrics()
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to get GPU metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve GPU metrics: {str(e)}"
        )


@router.get("/health", response_model=HealthCheck)
async def health_check() -> HealthCheck:
    """
    Comprehensive health check for rendering service
    
    Returns:
        Service health status and detailed metrics
    """
    try:
        renderer = get_renderer()
        health_data = await renderer.health_check()
        
        # Determine overall service status
        status = "healthy"
        if health_data.get("status") != "healthy":
            status = health_data["status"]
        
        return HealthCheck(
            status=status,
            service="gpu_rendering",
            version="5.0.0"
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheck(
            status="unhealthy",
            service="gpu_rendering", 
            version="5.0.0"
        )


@router.post("/estimate")
async def estimate_render_time(edl: EDL) -> Dict[str, Any]:
    """
    Estimate rendering time for an EDL
    
    Args:
        edl: Edit Decision List to analyze
        
    Returns:
        Estimated processing time and resource requirements
    """
    try:
        renderer = get_renderer()
        estimated_time = await renderer.estimate_render_time(edl)
        
        # Calculate additional estimates
        num_clips = len([c for c in edl.timeline if c.type == "clip"])
        total_duration = sum(c.duration for c in edl.timeline if c.type == "clip")
        
        gpu_metrics = renderer.get_gpu_metrics()
        queue_manager = get_queue_manager()
        queue_stats = await queue_manager.get_queue_stats()
        
        return {
            "estimated_render_time": estimated_time,
            "estimated_wait_time": queue_stats.get("estimated_wait_time", 0),
            "total_estimated_time": estimated_time + queue_stats.get("estimated_wait_time", 0),
            "clip_count": num_clips,
            "total_duration": total_duration,
            "gpu_available": gpu_metrics.available,
            "queue_depth": queue_stats.get("queue_depth", 0)
        }
        
    except Exception as e:
        logger.error(f"Failed to estimate render time: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to estimate render time: {str(e)}"
        )


@router.post("/test")
async def test_gpu_rendering() -> Dict[str, Any]:
    """
    Test GPU rendering functionality with a simple operation
    
    Returns:
        Test results and performance metrics
    """
    try:
        renderer = get_renderer()
        
        # Simple GPU availability test
        gpu_metrics = renderer.get_gpu_metrics()
        health = await renderer.health_check()
        
        test_results = {
            "gpu_available": gpu_metrics.available,
            "gpu_utilization": gpu_metrics.utilization,
            "memory_available": gpu_metrics.memory_total - gpu_metrics.memory_used,
            "service_health": health["status"],
            "test_passed": gpu_metrics.available and health["status"] in ["healthy", "degraded"]
        }
        
        if test_results["test_passed"]:
            test_results["message"] = "GPU rendering service operational"
        else:
            test_results["message"] = "GPU rendering service issues detected"
            
        return test_results
        
    except Exception as e:
        logger.error(f"GPU rendering test failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Rendering test failed: {str(e)}"
        )


@router.get("/presets")
async def get_render_presets() -> Dict[str, Any]:
    """
    Get available rendering presets and configurations
    
    Returns:
        Available presets with their specifications
    """
    presets = {
        "fast": {
            "description": "Fast rendering with basic quality",
            "nvenc_preset": "p1",
            "bitrate": "1.5M",
            "target_processing_speed": "3-4x realtime"
        },
        "balanced": {
            "description": "Balanced quality and speed", 
            "nvenc_preset": "p4",
            "bitrate": "2M",
            "target_processing_speed": "2-3x realtime"
        },
        "quality": {
            "description": "High quality output",
            "nvenc_preset": "p7", 
            "bitrate": "3M",
            "target_processing_speed": "1-2x realtime"
        }
    }
    
    return {
        "presets": presets,
        "default": "balanced",
        "supported_formats": ["mp4", "webm"],
        "supported_resolutions": [
            {"name": "720p Vertical", "width": 720, "height": 1280},
            {"name": "1080p Vertical", "width": 1080, "height": 1920},
            {"name": "720p Horizontal", "width": 1280, "height": 720},
            {"name": "1080p Horizontal", "width": 1920, "height": 1080}
        ]
    }


# Background task functions

async def _cleanup_old_jobs_background(queue_manager):
    """Background task to cleanup old completed jobs"""
    try:
        cleaned = await queue_manager.cleanup_old_jobs(max_age_hours=24)
        if cleaned > 0:
            logger.info(f"Background cleanup: removed {cleaned} old jobs")
    except Exception as e:
        logger.error(f"Background job cleanup failed: {e}")


# Exception handlers

@router.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with proper error response"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            detail=f"Endpoint: {request.url.path}"
        ).dict()
    )


@router.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions with error response"""
    logger.error(f"Unhandled exception in {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc)
        ).dict()
    )