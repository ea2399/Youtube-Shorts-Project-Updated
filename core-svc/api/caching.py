"""
Caching API Endpoints - Phase 5E
REST API for cache management and monitoring
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional, List
import logging

from ..services.caching.cache_manager import (
    get_cache_manager, 
    CacheType, 
    CacheLayer,
    CacheKey
)
from ..models.schemas import BaseResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cache", tags=["Caching"])


@router.get("/stats", response_model=Dict[str, Any])
async def get_cache_stats():
    """Get comprehensive cache statistics for all layers"""
    try:
        cache_manager = await get_cache_manager()
        stats = await cache_manager.get_cache_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=Dict[str, Any])
async def get_cache_health():
    """Get cache system health information"""
    try:
        cache_manager = await get_cache_manager()
        stats = await cache_manager.get_cache_stats()
        
        # Calculate health metrics
        total_hit_rate = 0
        layer_count = 0
        for layer_stats in stats.values():
            if layer_stats.hits + layer_stats.misses > 0:
                total_hit_rate += layer_stats.hit_rate
                layer_count += 1
        
        avg_hit_rate = total_hit_rate / layer_count if layer_count > 0 else 0
        
        health_status = "healthy"
        if avg_hit_rate < 0.5:
            health_status = "degraded"
        if avg_hit_rate < 0.2:
            health_status = "unhealthy"
        
        return {
            "status": health_status,
            "average_hit_rate": avg_hit_rate,
            "total_memory_usage": stats.get("l1_memory", {}).get("size", 0),
            "total_disk_usage": stats.get("l3_disk", {}).get("size", 0),
            "layer_count": layer_count,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get cache health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear/{cache_type}", response_model=BaseResponse)
async def clear_cache_type(cache_type: CacheType):
    """Clear all entries of a specific cache type"""
    try:
        cache_manager = await get_cache_manager()
        cleared_count = await cache_manager.clear_cache_type(cache_type)
        
        return BaseResponse(
            success=True,
            message=f"Cleared {cleared_count} entries of type {cache_type.value}"
        )
        
    except Exception as e:
        logger.error(f"Failed to clear cache type {cache_type}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/invalidate", response_model=BaseResponse)
async def invalidate_cache_key(
    cache_type: CacheType,
    content_id: str,
    parameters: Optional[str] = Query(None, description="JSON string of parameters")
):
    """Invalidate a specific cache key"""
    try:
        import json
        
        # Parse parameters if provided
        params = json.loads(parameters) if parameters else {}
        
        cache_key = CacheKey(
            cache_type=cache_type,
            content_id=content_id,
            parameters=params
        )
        
        cache_manager = await get_cache_manager()
        success = await cache_manager.invalidate(cache_key)
        
        if success:
            return BaseResponse(
                success=True,
                message=f"Cache key invalidated: {cache_key.to_string()}"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to invalidate cache key")
        
    except Exception as e:
        logger.error(f"Failed to invalidate cache key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup", response_model=BaseResponse)
async def cleanup_expired_entries():
    """Clean up expired cache entries across all layers"""
    try:
        cache_manager = await get_cache_manager()
        cleaned_count = await cache_manager.cleanup_expired()
        
        return BaseResponse(
            success=True,
            message=f"Cleaned up {cleaned_count} expired cache entries"
        )
        
    except Exception as e:
        logger.error(f"Failed to cleanup cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/layers", response_model=List[str])
async def get_cache_layers():
    """Get list of available cache layers"""
    return [layer.value for layer in CacheLayer]


@router.get("/types", response_model=List[str])
async def get_cache_types():
    """Get list of available cache types"""
    return [cache_type.value for cache_type in CacheType]


@router.get("/size", response_model=Dict[str, Any])
async def get_cache_size_info():
    """Get detailed cache size information"""
    try:
        cache_manager = await get_cache_manager()
        stats = await cache_manager.get_cache_stats()
        
        size_info = {
            "memory": {
                "current": stats.get("l1_memory", {}).get("size", 0),
                "max": cache_manager.max_memory_size,
                "usage_percent": (stats.get("l1_memory", {}).get("size", 0) / cache_manager.max_memory_size) * 100
            },
            "disk": {
                "current": stats.get("l3_disk", {}).get("size", 0),
                "max": cache_manager.max_disk_size,
                "usage_percent": (stats.get("l3_disk", {}).get("size", 0) / cache_manager.max_disk_size) * 100
            },
            "counts": {
                "memory_entries": stats.get("l1_memory", {}).get("count", 0),
                "disk_entries": stats.get("l3_disk", {}).get("count", 0)
            }
        }
        
        return size_info
        
    except Exception as e:
        logger.error(f"Failed to get cache size info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance", response_model=Dict[str, Any])
async def get_cache_performance():
    """Get cache performance metrics"""
    try:
        cache_manager = await get_cache_manager()
        stats = await cache_manager.get_cache_stats()
        
        performance = {}
        for layer, layer_stats in stats.items():
            performance[layer] = {
                "hit_rate": layer_stats.hit_rate,
                "hits": layer_stats.hits,
                "misses": layer_stats.misses,
                "evictions": layer_stats.evictions,
                "efficiency": layer_stats.hits / (layer_stats.hits + layer_stats.misses + layer_stats.evictions) if (layer_stats.hits + layer_stats.misses + layer_stats.evictions) > 0 else 0
            }
        
        return performance
        
    except Exception as e:
        logger.error(f"Failed to get cache performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/warmup", response_model=BaseResponse)
async def warmup_cache(
    cache_type: Optional[CacheType] = None,
    preload_models: bool = True
):
    """Warmup cache by preloading frequently used items"""
    try:
        cache_manager = await get_cache_manager()
        
        # This is a placeholder for cache warmup logic
        # In a real implementation, you would:
        # 1. Load frequently used ML models
        # 2. Preprocess common video segments
        # 3. Generate proxy videos for recent uploads
        
        warmup_count = 0
        
        if preload_models:
            # Placeholder: Load common ML models
            logger.info("Warming up ML model cache")
            warmup_count += 1
        
        if cache_type == CacheType.VIDEO_SEGMENT:
            # Placeholder: Preload recent video segments
            logger.info("Warming up video segment cache")
            warmup_count += 1
        
        return BaseResponse(
            success=True,
            message=f"Cache warmup completed for {warmup_count} categories"
        )
        
    except Exception as e:
        logger.error(f"Failed to warmup cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))