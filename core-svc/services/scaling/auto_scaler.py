"""
Auto-scaling Controller - Phase 5D
Dynamic GPU worker scaling based on queue depth and performance metrics
"""

import asyncio
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

import docker
import aioredis
from pydantic import BaseModel

from ..render_queue import get_queue_manager
from ..gpu_renderer import get_renderer


logger = logging.getLogger(__name__)


class ScalingAction(str, Enum):
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down" 
    NO_ACTION = "no_action"


@dataclass
class ScalingMetrics:
    """Current system metrics for scaling decisions"""
    queue_depth: int
    active_jobs: int
    estimated_wait_time: float
    gpu_utilization: float
    gpu_memory_usage: float
    gpu_temperature: float
    current_replicas: int
    processing_speed: float
    timestamp: datetime


class ScalingDecision(BaseModel):
    """Scaling decision with reasoning"""
    action: ScalingAction
    target_replicas: int
    current_replicas: int
    reasoning: str
    confidence: float
    metrics: Dict[str, Any]


class AutoScalingController:
    """
    Intelligent auto-scaling controller for GPU rendering infrastructure
    Uses queue depth, performance metrics, and health indicators for scaling decisions
    """
    
    def __init__(self, 
                 service_name: str = "gpu-worker",
                 redis_url: str = "redis://localhost:6379/0",
                 scaling_interval: int = 30):
        self.service_name = service_name
        self.redis_url = redis_url
        self.scaling_interval = scaling_interval
        
        # Scaling thresholds
        self.scale_up_queue_threshold = 10
        self.scale_down_queue_threshold = 3
        self.scale_up_wait_time_threshold = 300  # 5 minutes
        self.max_replicas = 8
        self.min_replicas = 1
        
        # GPU health thresholds
        self.max_gpu_temperature = 80  # Celsius
        self.max_gpu_memory_usage = 90  # Percentage
        
        # Cool-down periods (prevent rapid scaling)
        self.scale_up_cooldown = 300  # 5 minutes
        self.scale_down_cooldown = 600  # 10 minutes
        
        # State tracking
        self.last_scaling_action = None
        self.last_scaling_time = None
        self.scaling_history = []
        
        # Docker client
        self.docker_client = docker.from_env()
        
        # Redis connection
        self.redis = None
        
        # Queue and renderer references
        self.queue_manager = get_queue_manager()
        self.renderer = get_renderer()
    
    async def initialize(self):
        """Initialize Redis connection and validate services"""
        try:
            self.redis = await aioredis.from_url(self.redis_url)
            await self.redis.ping()
            logger.info("Auto-scaler initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize auto-scaler: {e}")
            raise
    
    async def get_current_metrics(self) -> ScalingMetrics:
        """Collect current system metrics for scaling decisions"""
        try:
            # Get queue statistics
            queue_stats = await self.queue_manager.get_queue_stats()
            
            # Get GPU metrics
            gpu_metrics = self.renderer.get_gpu_metrics()
            
            # Get current replica count
            current_replicas = await self._get_current_replicas()
            
            return ScalingMetrics(
                queue_depth=queue_stats.get("queue_depth", 0),
                active_jobs=queue_stats.get("active_jobs", 0),
                estimated_wait_time=queue_stats.get("estimated_wait_time", 0),
                gpu_utilization=gpu_metrics.utilization if gpu_metrics.available else 0,
                gpu_memory_usage=(gpu_metrics.memory_used / gpu_metrics.memory_total * 100) if gpu_metrics.available else 0,
                gpu_temperature=gpu_metrics.temperature if gpu_metrics.available else 0,
                current_replicas=current_replicas,
                processing_speed=queue_stats.get("metrics", {}).get("average_processing_time", 1.0),
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            # Return default metrics to prevent scaling errors
            return ScalingMetrics(
                queue_depth=0, active_jobs=0, estimated_wait_time=0,
                gpu_utilization=0, gpu_memory_usage=0, gpu_temperature=0,
                current_replicas=1, processing_speed=1.0, timestamp=datetime.utcnow()
            )
    
    async def make_scaling_decision(self, metrics: ScalingMetrics) -> ScalingDecision:
        """
        Make intelligent scaling decision based on current metrics
        
        Scaling Logic:
        - Scale UP if: queue_depth > 10 AND wait_time > 5min AND GPU healthy
        - Scale DOWN if: queue_depth < 3 AND active_jobs < max_concurrent AND cooldown passed
        - Health gates: Don't scale if GPU temp > 80°C or memory > 90%
        """
        
        # Check cooldown periods
        if self.last_scaling_time:
            time_since_last = (datetime.utcnow() - self.last_scaling_time).total_seconds()
            
            if (self.last_scaling_action == ScalingAction.SCALE_UP and 
                time_since_last < self.scale_up_cooldown):
                return ScalingDecision(
                    action=ScalingAction.NO_ACTION,
                    target_replicas=metrics.current_replicas,
                    current_replicas=metrics.current_replicas,
                    reasoning=f"Scale-up cooldown active ({time_since_last:.0f}s < {self.scale_up_cooldown}s)",
                    confidence=1.0,
                    metrics=metrics.__dict__
                )
            
            if (self.last_scaling_action == ScalingAction.SCALE_DOWN and 
                time_since_last < self.scale_down_cooldown):
                return ScalingDecision(
                    action=ScalingAction.NO_ACTION,
                    target_replicas=metrics.current_replicas,
                    current_replicas=metrics.current_replicas,
                    reasoning=f"Scale-down cooldown active ({time_since_last:.0f}s < {self.scale_down_cooldown}s)",
                    confidence=1.0,
                    metrics=metrics.__dict__
                )
        
        # Check GPU health constraints
        gpu_healthy = (metrics.gpu_temperature < self.max_gpu_temperature and 
                      metrics.gpu_memory_usage < self.max_gpu_memory_usage)
        
        # Scale UP decision
        if (metrics.queue_depth > self.scale_up_queue_threshold and
            metrics.estimated_wait_time > self.scale_up_wait_time_threshold and
            metrics.current_replicas < self.max_replicas and
            gpu_healthy):
            
            target_replicas = min(metrics.current_replicas + 1, self.max_replicas)
            confidence = min(
                (metrics.queue_depth / self.scale_up_queue_threshold) * 0.5 +
                (metrics.estimated_wait_time / self.scale_up_wait_time_threshold) * 0.5,
                1.0
            )
            
            return ScalingDecision(
                action=ScalingAction.SCALE_UP,
                target_replicas=target_replicas,
                current_replicas=metrics.current_replicas,
                reasoning=f"High queue depth ({metrics.queue_depth}) and wait time ({metrics.estimated_wait_time:.0f}s)",
                confidence=confidence,
                metrics=metrics.__dict__
            )
        
        # Scale DOWN decision
        if (metrics.queue_depth < self.scale_down_queue_threshold and
            metrics.active_jobs < self.renderer.max_concurrent_renders and
            metrics.current_replicas > self.min_replicas):
            
            target_replicas = max(metrics.current_replicas - 1, self.min_replicas)
            confidence = 1.0 - (metrics.queue_depth / self.scale_down_queue_threshold)
            
            return ScalingDecision(
                action=ScalingAction.SCALE_DOWN,
                target_replicas=target_replicas,
                current_replicas=metrics.current_replicas,
                reasoning=f"Low queue depth ({metrics.queue_depth}) and idle capacity",
                confidence=confidence,
                metrics=metrics.__dict__
            )
        
        # No action needed
        reasoning_parts = []
        if not gpu_healthy:
            reasoning_parts.append(f"GPU unhealthy (temp: {metrics.gpu_temperature}°C, mem: {metrics.gpu_memory_usage:.1f}%)")
        if metrics.queue_depth <= self.scale_up_queue_threshold:
            reasoning_parts.append(f"Queue depth acceptable ({metrics.queue_depth})")
        if metrics.estimated_wait_time <= self.scale_up_wait_time_threshold:
            reasoning_parts.append(f"Wait time acceptable ({metrics.estimated_wait_time:.0f}s)")
        
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "System in optimal state"
        
        return ScalingDecision(
            action=ScalingAction.NO_ACTION,
            target_replicas=metrics.current_replicas,
            current_replicas=metrics.current_replicas,
            reasoning=reasoning,
            confidence=0.8,
            metrics=metrics.__dict__
        )
    
    async def execute_scaling_decision(self, decision: ScalingDecision) -> bool:
        """Execute scaling decision by updating Docker Compose service replicas"""
        if decision.action == ScalingAction.NO_ACTION:
            return True
        
        try:
            # Use Docker Compose API to scale service
            if decision.action == ScalingAction.SCALE_UP:
                success = await self._scale_service(decision.target_replicas)
                action_name = "scale up"
            else:
                success = await self._scale_service(decision.target_replicas)
                action_name = "scale down"
            
            if success:
                self.last_scaling_action = decision.action
                self.last_scaling_time = datetime.utcnow()
                
                # Record scaling event
                scaling_event = {
                    "timestamp": self.last_scaling_time.isoformat(),
                    "action": decision.action.value,
                    "from_replicas": decision.current_replicas,
                    "to_replicas": decision.target_replicas,
                    "reasoning": decision.reasoning,
                    "confidence": decision.confidence,
                    "metrics": decision.metrics
                }
                
                self.scaling_history.append(scaling_event)
                
                # Store in Redis for monitoring
                await self._store_scaling_event(scaling_event)
                
                logger.info(
                    f"Successfully executed {action_name}: "
                    f"{decision.current_replicas} → {decision.target_replicas} replicas. "
                    f"Reason: {decision.reasoning}"
                )
                
                return True
            else:
                logger.error(f"Failed to execute {action_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing scaling decision: {e}")
            return False
    
    async def _get_current_replicas(self) -> int:
        """Get current number of service replicas"""
        try:
            # Get service from Docker
            service = self.docker_client.services.get(f"youtube-short-project_{self.service_name}")
            
            # Get current replica count
            spec = service.attrs['Spec']
            replicas = spec.get('Mode', {}).get('Replicated', {}).get('Replicas', 1)
            
            return replicas
            
        except Exception as e:
            logger.warning(f"Could not get current replicas, assuming 1: {e}")
            return 1
    
    async def _scale_service(self, target_replicas: int) -> bool:
        """Scale Docker service to target replica count"""
        try:
            # Get service
            service = self.docker_client.services.get(f"youtube-short-project_{self.service_name}")
            
            # Update replica count
            service.scale(target_replicas)
            
            # Wait briefly for scaling to take effect
            await asyncio.sleep(5)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to scale service: {e}")
            return False
    
    async def _store_scaling_event(self, event: Dict[str, Any]):
        """Store scaling event in Redis for monitoring"""
        try:
            if self.redis:
                key = f"scaling:events:{int(time.time())}"
                await self.redis.setex(key, 86400 * 7, json.dumps(event))  # 7 day TTL
                
                # Also update current status
                status_key = "scaling:status"
                status = {
                    "last_action": event["action"],
                    "last_timestamp": event["timestamp"],
                    "current_replicas": event["to_replicas"],
                    "last_reasoning": event["reasoning"]
                }
                await self.redis.setex(status_key, 3600, json.dumps(status))  # 1 hour TTL
                
        except Exception as e:
            logger.warning(f"Failed to store scaling event: {e}")
    
    async def get_scaling_status(self) -> Dict[str, Any]:
        """Get current scaling status and recent history"""
        try:
            metrics = await self.get_current_metrics()
            
            # Get recent scaling events
            recent_events = self.scaling_history[-10:] if self.scaling_history else []
            
            status = {
                "current_metrics": metrics.__dict__,
                "last_scaling_action": self.last_scaling_action.value if self.last_scaling_action else None,
                "last_scaling_time": self.last_scaling_time.isoformat() if self.last_scaling_time else None,
                "recent_events": recent_events,
                "thresholds": {
                    "scale_up_queue_threshold": self.scale_up_queue_threshold,
                    "scale_down_queue_threshold": self.scale_down_queue_threshold,
                    "scale_up_wait_time_threshold": self.scale_up_wait_time_threshold,
                    "max_replicas": self.max_replicas,
                    "min_replicas": self.min_replicas
                },
                "health_status": "healthy" if (
                    metrics.gpu_temperature < self.max_gpu_temperature and
                    metrics.gpu_memory_usage < self.max_gpu_memory_usage
                ) else "degraded"
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get scaling status: {e}")
            return {"error": str(e)}
    
    async def run_scaling_loop(self):
        """Main scaling control loop"""
        logger.info("Starting auto-scaling control loop")
        
        while True:
            try:
                # Collect metrics
                metrics = await self.get_current_metrics()
                
                # Make scaling decision
                decision = await self.make_scaling_decision(metrics)
                
                # Execute decision
                await self.execute_scaling_decision(decision)
                
                # Log current state
                logger.debug(
                    f"Scaling check: Queue={metrics.queue_depth}, "
                    f"Active={metrics.active_jobs}, Wait={metrics.estimated_wait_time:.0f}s, "
                    f"Replicas={metrics.current_replicas}, Action={decision.action.value}"
                )
                
                # Wait for next interval
                await asyncio.sleep(self.scaling_interval)
                
            except Exception as e:
                logger.error(f"Error in scaling loop: {e}")
                await asyncio.sleep(self.scaling_interval)


# Global auto-scaler instance
_auto_scaler: Optional[AutoScalingController] = None


async def get_auto_scaler() -> AutoScalingController:
    """Get or create global auto-scaler instance"""
    global _auto_scaler
    if _auto_scaler is None:
        _auto_scaler = AutoScalingController()
        await _auto_scaler.initialize()
    return _auto_scaler


async def start_auto_scaling():
    """Start the auto-scaling service"""
    scaler = await get_auto_scaler()
    await scaler.run_scaling_loop()


if __name__ == "__main__":
    # Run auto-scaler standalone
    asyncio.run(start_auto_scaling())