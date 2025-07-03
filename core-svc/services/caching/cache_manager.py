"""
Multi-layer Cache Manager - Phase 5E
Advanced caching system for video segments, ML models, and proxy content
"""

import asyncio
import hashlib
import json
import logging
import pickle
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import aiofiles
import aioredis
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CacheLayer(str, Enum):
    """Cache layer types"""
    L1_MEMORY = "l1_memory"      # In-memory cache (fastest)
    L2_REDIS = "l2_redis"        # Redis cache (fast)
    L3_DISK = "l3_disk"          # Local disk cache (medium)
    L4_CDN = "l4_cdn"            # CDN cache (global)


class CacheType(str, Enum):
    """Types of cached content"""
    VIDEO_SEGMENT = "video_segment"
    ML_MODEL = "ml_model"
    PROXY_VIDEO = "proxy_video"
    THUMBNAIL = "thumbnail"
    TRANSCRIPTION = "transcription"
    EDL_RESULT = "edl_result"
    RENDER_OUTPUT = "render_output"


@dataclass
class CacheKey:
    """Structured cache key with metadata"""
    cache_type: CacheType
    content_id: str
    parameters: Dict[str, Any]
    version: str = "v1"
    
    def to_string(self) -> str:
        """Generate cache key string"""
        # Create deterministic parameter string
        param_str = json.dumps(self.parameters, sort_keys=True, separators=(',', ':'))
        param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
        
        return f"{self.cache_type.value}:{self.version}:{self.content_id}:{param_hash}"


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    data: Any
    size: int
    created_at: float
    last_accessed: float
    access_count: int
    ttl: Optional[int] = None
    layer: CacheLayer = CacheLayer.L1_MEMORY


class CacheStats(BaseModel):
    """Cache performance statistics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    count: int = 0
    hit_rate: float = 0.0


class MultiLayerCacheManager:
    """
    Advanced multi-layer caching system optimized for video processing
    
    L1: In-memory cache for frequently accessed small items
    L2: Redis cache for shared data across workers
    L3: Local disk cache for large files (video segments, models)
    L4: CDN cache for global distribution (future implementation)
    """
    
    def __init__(self, 
                 redis_url: str = "redis://localhost:6379/0",
                 disk_cache_dir: str = "/tmp/video_cache",
                 max_memory_size: int = 512 * 1024 * 1024,  # 512MB
                 max_disk_size: int = 10 * 1024 * 1024 * 1024):  # 10GB
        
        self.redis_url = redis_url
        self.disk_cache_dir = Path(disk_cache_dir)
        self.max_memory_size = max_memory_size
        self.max_disk_size = max_disk_size
        
        # Initialize cache layers
        self.l1_memory: Dict[str, CacheEntry] = {}
        self.l2_redis: Optional[aioredis.Redis] = None
        
        # Cache statistics
        self.stats = {layer: CacheStats() for layer in CacheLayer}
        
        # Size tracking
        self.current_memory_size = 0
        self.current_disk_size = 0
        
        # TTL configurations by cache type (seconds)
        self.default_ttls = {
            CacheType.VIDEO_SEGMENT: 3600,      # 1 hour
            CacheType.ML_MODEL: 86400,          # 24 hours
            CacheType.PROXY_VIDEO: 7200,        # 2 hours
            CacheType.THUMBNAIL: 86400,         # 24 hours
            CacheType.TRANSCRIPTION: 86400,     # 24 hours
            CacheType.EDL_RESULT: 3600,         # 1 hour
            CacheType.RENDER_OUTPUT: 1800,      # 30 minutes
        }
        
        # Size thresholds for layer selection
        self.size_thresholds = {
            CacheLayer.L1_MEMORY: 1024 * 1024,      # 1MB
            CacheLayer.L2_REDIS: 10 * 1024 * 1024,  # 10MB
            CacheLayer.L3_DISK: float('inf')        # No limit
        }
    
    async def initialize(self):
        """Initialize cache layers"""
        try:
            # Initialize Redis connection
            self.l2_redis = await aioredis.from_url(self.redis_url)
            await self.l2_redis.ping()
            
            # Create disk cache directory
            self.disk_cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize disk cache size tracking
            await self._calculate_disk_cache_size()
            
            logger.info(f"Multi-layer cache initialized: Memory={self.max_memory_size//1024//1024}MB, Disk={self.max_disk_size//1024//1024//1024}GB")
            
        except Exception as e:
            logger.error(f"Failed to initialize cache: {e}")
            raise
    
    async def get(self, cache_key: Union[CacheKey, str]) -> Optional[Any]:
        """Get item from cache with multi-layer fallback"""
        key_str = cache_key.to_string() if isinstance(cache_key, CacheKey) else cache_key
        
        # Try L1 memory cache first
        entry = await self._get_from_memory(key_str)
        if entry is not None:
            self.stats[CacheLayer.L1_MEMORY].hits += 1
            return entry.data
        
        # Try L2 Redis cache
        entry = await self._get_from_redis(key_str)
        if entry is not None:
            self.stats[CacheLayer.L2_REDIS].hits += 1
            # Promote to L1 if small enough
            if entry.size <= self.size_thresholds[CacheLayer.L1_MEMORY]:
                await self._put_in_memory(key_str, entry.data, entry.size, entry.ttl)
            return entry.data
        
        # Try L3 disk cache
        entry = await self._get_from_disk(key_str)
        if entry is not None:
            self.stats[CacheLayer.L3_DISK].hits += 1
            # Promote to higher layers if appropriate
            if entry.size <= self.size_thresholds[CacheLayer.L2_REDIS]:
                await self._put_in_redis(key_str, entry.data, entry.ttl)
            if entry.size <= self.size_thresholds[CacheLayer.L1_MEMORY]:
                await self._put_in_memory(key_str, entry.data, entry.size, entry.ttl)
            return entry.data
        
        # Cache miss on all layers
        for layer in CacheLayer:
            self.stats[layer].misses += 1
        
        return None
    
    async def put(self, 
                  cache_key: Union[CacheKey, str], 
                  data: Any, 
                  ttl: Optional[int] = None,
                  cache_type: Optional[CacheType] = None) -> bool:
        """Put item in appropriate cache layer based on size and type"""
        key_str = cache_key.to_string() if isinstance(cache_key, CacheKey) else cache_key
        
        # Determine TTL
        if ttl is None and cache_type:
            ttl = self.default_ttls.get(cache_type, 3600)
        
        # Estimate data size
        data_size = await self._estimate_size(data)
        
        # Determine appropriate cache layer(s)
        layers_to_cache = await self._select_cache_layers(data_size, cache_type)
        
        success = False
        for layer in layers_to_cache:
            try:
                if layer == CacheLayer.L1_MEMORY:
                    success |= await self._put_in_memory(key_str, data, data_size, ttl)
                elif layer == CacheLayer.L2_REDIS:
                    success |= await self._put_in_redis(key_str, data, ttl)
                elif layer == CacheLayer.L3_DISK:
                    success |= await self._put_in_disk(key_str, data, ttl)
                    
            except Exception as e:
                logger.warning(f"Failed to cache in layer {layer}: {e}")
        
        return success
    
    async def invalidate(self, cache_key: Union[CacheKey, str]) -> bool:
        """Remove item from all cache layers"""
        key_str = cache_key.to_string() if isinstance(cache_key, CacheKey) else cache_key
        
        success = True
        
        # Remove from L1 memory
        if key_str in self.l1_memory:
            entry = self.l1_memory.pop(key_str)
            self.current_memory_size -= entry.size
            self.stats[CacheLayer.L1_MEMORY].count -= 1
        
        # Remove from L2 Redis
        try:
            if self.l2_redis:
                await self.l2_redis.delete(f"cache:{key_str}")
        except Exception as e:
            logger.warning(f"Failed to invalidate Redis cache: {e}")
            success = False
        
        # Remove from L3 disk
        try:
            disk_path = self._get_disk_path(key_str)
            if disk_path.exists():
                file_size = disk_path.stat().st_size
                disk_path.unlink()
                self.current_disk_size -= file_size
                self.stats[CacheLayer.L3_DISK].count -= 1
        except Exception as e:
            logger.warning(f"Failed to invalidate disk cache: {e}")
            success = False
        
        return success
    
    async def clear_cache_type(self, cache_type: CacheType) -> int:
        """Clear all entries of a specific cache type"""
        prefix = f"{cache_type.value}:"
        cleared_count = 0
        
        # Clear from L1 memory
        keys_to_remove = [k for k in self.l1_memory.keys() if k.startswith(prefix)]
        for key in keys_to_remove:
            await self.invalidate(key)
            cleared_count += 1
        
        # Clear from L2 Redis
        try:
            if self.l2_redis:
                pattern = f"cache:{prefix}*"
                keys = await self.l2_redis.keys(pattern)
                if keys:
                    await self.l2_redis.delete(*keys)
                    cleared_count += len(keys)
        except Exception as e:
            logger.warning(f"Failed to clear Redis cache: {e}")
        
        # Clear from L3 disk
        try:
            for file_path in self.disk_cache_dir.glob(f"{prefix}*"):
                if file_path.is_file():
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    self.current_disk_size -= file_size
                    cleared_count += 1
        except Exception as e:
            logger.warning(f"Failed to clear disk cache: {e}")
        
        logger.info(f"Cleared {cleared_count} entries of type {cache_type.value}")
        return cleared_count
    
    async def get_cache_stats(self) -> Dict[str, CacheStats]:
        """Get comprehensive cache statistics"""
        # Update hit rates
        for layer_stats in self.stats.values():
            total_requests = layer_stats.hits + layer_stats.misses
            layer_stats.hit_rate = layer_stats.hits / total_requests if total_requests > 0 else 0.0
        
        # Update counts and sizes
        self.stats[CacheLayer.L1_MEMORY].count = len(self.l1_memory)
        self.stats[CacheLayer.L1_MEMORY].size = self.current_memory_size
        self.stats[CacheLayer.L3_DISK].size = self.current_disk_size
        
        return {layer.value: stats for layer, stats in self.stats.items()}
    
    async def cleanup_expired(self) -> int:
        """Clean up expired cache entries"""
        current_time = time.time()
        cleaned_count = 0
        
        # Clean L1 memory cache
        expired_keys = []
        for key, entry in self.l1_memory.items():
            if entry.ttl and (current_time - entry.created_at) > entry.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            await self.invalidate(key)
            cleaned_count += 1
        
        # Redis TTL is handled automatically
        
        # Clean L3 disk cache (basic TTL check)
        try:
            for file_path in self.disk_cache_dir.glob("*"):
                if file_path.is_file():
                    # Simple age-based cleanup (could be enhanced with metadata)
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > 86400:  # 24 hours default
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        self.current_disk_size -= file_size
                        cleaned_count += 1
        except Exception as e:
            logger.warning(f"Failed to cleanup disk cache: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired cache entries")
        
        return cleaned_count
    
    # Private helper methods
    
    async def _get_from_memory(self, key: str) -> Optional[CacheEntry]:
        """Get entry from L1 memory cache"""
        if key in self.l1_memory:
            entry = self.l1_memory[key]
            entry.last_accessed = time.time()
            entry.access_count += 1
            return entry
        return None
    
    async def _get_from_redis(self, key: str) -> Optional[CacheEntry]:
        """Get entry from L2 Redis cache"""
        try:
            if self.l2_redis:
                data = await self.l2_redis.get(f"cache:{key}")
                if data:
                    deserialized = pickle.loads(data)
                    return CacheEntry(
                        key=key,
                        data=deserialized,
                        size=len(data),
                        created_at=time.time(),
                        last_accessed=time.time(),
                        access_count=1,
                        layer=CacheLayer.L2_REDIS
                    )
        except Exception as e:
            logger.warning(f"Failed to get from Redis: {e}")
        return None
    
    async def _get_from_disk(self, key: str) -> Optional[CacheEntry]:
        """Get entry from L3 disk cache"""
        try:
            file_path = self._get_disk_path(key)
            if file_path.exists():
                async with aiofiles.open(file_path, 'rb') as f:
                    data = await f.read()
                    deserialized = pickle.loads(data)
                    return CacheEntry(
                        key=key,
                        data=deserialized,
                        size=len(data),
                        created_at=file_path.stat().st_ctime,
                        last_accessed=time.time(),
                        access_count=1,
                        layer=CacheLayer.L3_DISK
                    )
        except Exception as e:
            logger.warning(f"Failed to get from disk: {e}")
        return None
    
    async def _put_in_memory(self, key: str, data: Any, size: int, ttl: Optional[int]) -> bool:
        """Put entry in L1 memory cache"""
        try:
            # Check if we need to evict
            while self.current_memory_size + size > self.max_memory_size and self.l1_memory:
                await self._evict_from_memory()
            
            # Add new entry
            entry = CacheEntry(
                key=key,
                data=data,
                size=size,
                created_at=time.time(),
                last_accessed=time.time(),
                access_count=0,
                ttl=ttl,
                layer=CacheLayer.L1_MEMORY
            )
            
            self.l1_memory[key] = entry
            self.current_memory_size += size
            self.stats[CacheLayer.L1_MEMORY].count += 1
            
            return True
            
        except Exception as e:
            logger.warning(f"Failed to put in memory: {e}")
            return False
    
    async def _put_in_redis(self, key: str, data: Any, ttl: Optional[int]) -> bool:
        """Put entry in L2 Redis cache"""
        try:
            if self.l2_redis:
                serialized = pickle.dumps(data)
                await self.l2_redis.setex(f"cache:{key}", ttl or 3600, serialized)
                return True
        except Exception as e:
            logger.warning(f"Failed to put in Redis: {e}")
        return False
    
    async def _put_in_disk(self, key: str, data: Any, ttl: Optional[int]) -> bool:
        """Put entry in L3 disk cache"""
        try:
            file_path = self._get_disk_path(key)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            serialized = pickle.dumps(data)
            
            # Check disk space
            while self.current_disk_size + len(serialized) > self.max_disk_size:
                await self._evict_from_disk()
            
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(serialized)
            
            self.current_disk_size += len(serialized)
            self.stats[CacheLayer.L3_DISK].count += 1
            
            return True
            
        except Exception as e:
            logger.warning(f"Failed to put in disk: {e}")
            return False
    
    async def _evict_from_memory(self):
        """Evict least recently used item from memory cache"""
        if not self.l1_memory:
            return
        
        # Find LRU entry
        lru_key = min(self.l1_memory.keys(), 
                     key=lambda k: self.l1_memory[k].last_accessed)
        
        entry = self.l1_memory.pop(lru_key)
        self.current_memory_size -= entry.size
        self.stats[CacheLayer.L1_MEMORY].evictions += 1
        self.stats[CacheLayer.L1_MEMORY].count -= 1
    
    async def _evict_from_disk(self):
        """Evict oldest file from disk cache"""
        try:
            oldest_file = None
            oldest_time = float('inf')
            
            for file_path in self.disk_cache_dir.glob("*"):
                if file_path.is_file():
                    mtime = file_path.stat().st_mtime
                    if mtime < oldest_time:
                        oldest_time = mtime
                        oldest_file = file_path
            
            if oldest_file:
                file_size = oldest_file.stat().st_size
                oldest_file.unlink()
                self.current_disk_size -= file_size
                self.stats[CacheLayer.L3_DISK].evictions += 1
                self.stats[CacheLayer.L3_DISK].count -= 1
                
        except Exception as e:
            logger.warning(f"Failed to evict from disk: {e}")
    
    def _get_disk_path(self, key: str) -> Path:
        """Get disk file path for cache key"""
        # Create safe filename from key
        safe_key = key.replace('/', '_').replace(':', '_')
        return self.disk_cache_dir / f"{safe_key}.cache"
    
    async def _estimate_size(self, data: Any) -> int:
        """Estimate size of data in bytes"""
        try:
            if isinstance(data, (str, bytes)):
                return len(data)
            elif isinstance(data, (dict, list)):
                return len(json.dumps(data).encode())
            else:
                return len(pickle.dumps(data))
        except Exception:
            return 1024  # Default size estimate
    
    async def _select_cache_layers(self, size: int, cache_type: Optional[CacheType]) -> List[CacheLayer]:
        """Select appropriate cache layers based on size and type"""
        layers = []
        
        # Always try to cache in appropriate layers based on size
        if size <= self.size_thresholds[CacheLayer.L1_MEMORY]:
            layers.append(CacheLayer.L1_MEMORY)
        
        if size <= self.size_thresholds[CacheLayer.L2_REDIS]:
            layers.append(CacheLayer.L2_REDIS)
        
        # Always cache to disk for persistence
        layers.append(CacheLayer.L3_DISK)
        
        return layers
    
    async def _calculate_disk_cache_size(self):
        """Calculate current disk cache size"""
        try:
            total_size = 0
            count = 0
            for file_path in self.disk_cache_dir.glob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    count += 1
            
            self.current_disk_size = total_size
            self.stats[CacheLayer.L3_DISK].count = count
            
        except Exception as e:
            logger.warning(f"Failed to calculate disk cache size: {e}")


# Global cache manager instance
_cache_manager: Optional[MultiLayerCacheManager] = None


async def get_cache_manager() -> MultiLayerCacheManager:
    """Get or create global cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = MultiLayerCacheManager()
        await _cache_manager.initialize()
    return _cache_manager


# Convenience functions for common cache operations

async def cache_video_segment(video_id: str, start_time: float, duration: float, data: bytes) -> bool:
    """Cache a video segment"""
    cache_key = CacheKey(
        cache_type=CacheType.VIDEO_SEGMENT,
        content_id=video_id,
        parameters={"start": start_time, "duration": duration}
    )
    cache_manager = await get_cache_manager()
    return await cache_manager.put(cache_key, data, cache_type=CacheType.VIDEO_SEGMENT)


async def get_cached_video_segment(video_id: str, start_time: float, duration: float) -> Optional[bytes]:
    """Get cached video segment"""
    cache_key = CacheKey(
        cache_type=CacheType.VIDEO_SEGMENT,
        content_id=video_id,
        parameters={"start": start_time, "duration": duration}
    )
    cache_manager = await get_cache_manager()
    return await cache_manager.get(cache_key)


async def cache_ml_model(model_name: str, model_data: Any) -> bool:
    """Cache ML model data"""
    cache_key = CacheKey(
        cache_type=CacheType.ML_MODEL,
        content_id=model_name,
        parameters={}
    )
    cache_manager = await get_cache_manager()
    return await cache_manager.put(cache_key, model_data, cache_type=CacheType.ML_MODEL)


async def get_cached_ml_model(model_name: str) -> Optional[Any]:
    """Get cached ML model"""
    cache_key = CacheKey(
        cache_type=CacheType.ML_MODEL,
        content_id=model_name,
        parameters={}
    )
    cache_manager = await get_cache_manager()
    return await cache_manager.get(cache_key)