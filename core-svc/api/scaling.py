"""
Auto-scaling API Endpoints - Phase 5D
REST API for monitoring and controlling auto-scaling system
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, Optional
import logging

from ..services.scaling.auto_scaler import get_auto_scaler, ScalingDecision
from ..models.schemas import BaseResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scaling", tags=["Auto-scaling"])


@router.get("/status", response_model=Dict[str, Any])
async def get_scaling_status():
    """Get current auto-scaling status and metrics"""
    try:
        scaler = await get_auto_scaler()
        status = await scaler.get_scaling_status()
        return status
        
    except Exception as e:
        logger.error(f"Failed to get scaling status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics", response_model=Dict[str, Any])
async def get_scaling_metrics():
    """Get current system metrics used for scaling decisions"""
    try:
        scaler = await get_auto_scaler()
        metrics = await scaler.get_current_metrics()
        return metrics.__dict__
        
    except Exception as e:
        logger.error(f"Failed to get scaling metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/decision", response_model=ScalingDecision)
async def get_scaling_decision():
    """Get the current scaling decision without executing it"""
    try:
        scaler = await get_auto_scaler()
        metrics = await scaler.get_current_metrics()
        decision = await scaler.make_scaling_decision(metrics)
        return decision
        
    except Exception as e:
        logger.error(f"Failed to get scaling decision: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute", response_model=BaseResponse)
async def execute_scaling_decision():
    """Manually trigger a scaling decision execution"""
    try:
        scaler = await get_auto_scaler()
        metrics = await scaler.get_current_metrics()
        decision = await scaler.make_scaling_decision(metrics)
        
        success = await scaler.execute_scaling_decision(decision)
        
        if success:
            return BaseResponse(
                success=True, 
                message=f"Scaling decision executed: {decision.action.value}"
            )
        else:
            raise HTTPException(
                status_code=500, 
                detail="Failed to execute scaling decision"
            )
        
    except Exception as e:
        logger.error(f"Failed to execute scaling: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/thresholds", response_model=BaseResponse)
async def update_scaling_thresholds(
    scale_up_queue_threshold: Optional[int] = None,
    scale_down_queue_threshold: Optional[int] = None,
    scale_up_wait_time_threshold: Optional[int] = None,
    max_replicas: Optional[int] = None,
    min_replicas: Optional[int] = None
):
    """Update auto-scaling thresholds"""
    try:
        scaler = await get_auto_scaler()
        
        # Update thresholds if provided
        if scale_up_queue_threshold is not None:
            scaler.scale_up_queue_threshold = scale_up_queue_threshold
        if scale_down_queue_threshold is not None:
            scaler.scale_down_queue_threshold = scale_down_queue_threshold
        if scale_up_wait_time_threshold is not None:
            scaler.scale_up_wait_time_threshold = scale_up_wait_time_threshold
        if max_replicas is not None:
            scaler.max_replicas = max_replicas
        if min_replicas is not None:
            scaler.min_replicas = min_replicas
        
        logger.info("Auto-scaling thresholds updated")
        
        return BaseResponse(
            success=True,
            message="Scaling thresholds updated successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to update thresholds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=Dict[str, Any])
async def get_scaling_history(limit: int = 50):
    """Get recent scaling events history"""
    try:
        scaler = await get_auto_scaler()
        
        # Get recent events from scaler history
        recent_events = scaler.scaling_history[-limit:] if scaler.scaling_history else []
        
        return {
            "events": recent_events,
            "total_events": len(scaler.scaling_history),
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Failed to get scaling history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start", response_model=BaseResponse)
async def start_auto_scaling(background_tasks: BackgroundTasks):
    """Start the auto-scaling background service"""
    try:
        from ..services.scaling.auto_scaler import start_auto_scaling
        
        # Add auto-scaling to background tasks
        background_tasks.add_task(start_auto_scaling)
        
        return BaseResponse(
            success=True,
            message="Auto-scaling service started"
        )
        
    except Exception as e:
        logger.error(f"Failed to start auto-scaling: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop", response_model=BaseResponse)
async def stop_auto_scaling():
    """Stop the auto-scaling service (placeholder for future implementation)"""
    return BaseResponse(
        success=True,
        message="Auto-scaling service stop requested (not implemented)"
    )