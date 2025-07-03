"""
GPU-Optimized Video Rendering Engine - Phase 5A
High-performance video rendering with NVENC/NVDEC hardware acceleration
"""

import asyncio
import logging
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import json
import psutil
import pynvml

from pydantic import BaseModel
from fastapi import HTTPException

from ..models.schemas import EDL, RenderedVideo, RenderingJob, GPUMetrics, ReframingFrame
from .mediapipe_processor import get_mediapipe_processor


logger = logging.getLogger(__name__)


class RenderConfig(BaseModel):
    """Configuration for GPU rendering operations"""
    preset: str = "fast"  # fast, balanced, quality
    target_format: str = "mp4"
    resolution: Tuple[int, int] = (720, 1280)  # 9:16 vertical
    bitrate: str = "2M"
    framerate: int = 30
    hardware_acceleration: bool = True
    nvenc_preset: str = "p4"  # NVENC preset (p1-p7, p4=balanced)
    use_gpu_filters: bool = True
    enable_face_tracking: bool = True
    reframing_sample_interval: float = 1.0


class GPURenderingEngine:
    """
    Advanced GPU-accelerated video rendering engine
    Optimized for YouTube Shorts production pipeline
    """
    
    def __init__(self):
        self.gpu_available = False
        self.gpu_memory_total = 0
        self.gpu_memory_free = 0
        self.concurrent_renders = 0
        self.max_concurrent_renders = 3
        self.render_queue = asyncio.Queue()
        
        # Initialize GPU monitoring
        try:
            pynvml.nvmlInit()
            self.gpu_available = True
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            self.gpu_memory_total = info.total
            logger.info(f"GPU initialized with {self.gpu_memory_total // 1024**2}MB memory")
        except Exception as e:
            logger.warning(f"GPU not available: {e}")
            self.gpu_available = False
    
    async def render_from_edl(
        self, 
        edl: EDL, 
        source_video_path: str,
        output_directory: str,
        config: RenderConfig = None
    ) -> List[RenderedVideo]:
        """
        Render multiple clips from EDL with GPU acceleration
        
        Args:
            edl: Edit Decision List with clip specifications
            source_video_path: Path to source video file
            output_directory: Directory for rendered outputs
            config: Rendering configuration
            
        Returns:
            List of rendered video metadata
        """
        if config is None:
            config = RenderConfig()
            
        # Validate inputs
        if not Path(source_video_path).exists():
            raise HTTPException(status_code=404, detail="Source video not found")
            
        output_dir = Path(output_directory)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        rendered_videos = []
        
        try:
            # Generate reframing data if face tracking is enabled
            reframing_frames = []
            if config.enable_face_tracking:
                processor = get_mediapipe_processor()
                reframing_frames = await processor.process_video_for_reframing(
                    source_video_path, 
                    config.reframing_sample_interval
                )
                logger.info(f"Generated {len(reframing_frames)} reframing frames")
            
            # Process clips in parallel (respecting GPU memory limits)
            tasks = []
            for i, clip in enumerate(edl.timeline):
                if clip.type == "clip":
                    task = self._render_single_clip(
                        clip=clip,
                        source_path=source_video_path,
                        output_path=output_dir / f"clip_{i:03d}.{config.target_format}",
                        config=config,
                        clip_index=i,
                        reframing_frames=reframing_frames
                    )
                    tasks.append(task)
            
            # Execute renders with concurrency control
            semaphore = asyncio.Semaphore(self.max_concurrent_renders)
            results = await asyncio.gather(*[
                self._controlled_render(task, semaphore) for task in tasks
            ])
            
            rendered_videos = [r for r in results if r is not None]
            
        except Exception as e:
            logger.error(f"EDL rendering failed: {e}")
            raise HTTPException(status_code=500, detail=f"Rendering failed: {str(e)}")
            
        return rendered_videos
    
    async def _controlled_render(self, task_coro, semaphore):
        """Control concurrent rendering with semaphore"""
        async with semaphore:
            return await task_coro
    
    async def _render_single_clip(
        self,
        clip: Any,
        source_path: str,
        output_path: Path,
        config: RenderConfig,
        clip_index: int,
        reframing_frames: List[ReframingFrame] = None
    ) -> Optional[RenderedVideo]:
        """
        Render a single clip with GPU acceleration
        
        Args:
            clip: Clip definition from EDL
            source_path: Source video file path
            output_path: Output file path
            config: Rendering configuration
            clip_index: Index for tracking
            
        Returns:
            Rendered video metadata or None if failed
        """
        start_time = time.time()
        
        try:
            # Build FFmpeg command with GPU acceleration and reframing
            cmd = await self._build_ffmpeg_command(
                source_path=source_path,
                output_path=str(output_path),
                start_time=clip.source_start,
                duration=clip.duration,
                config=config,
                reframing_frames=reframing_frames
            )
            
            logger.info(f"Rendering clip {clip_index}: {clip.source_start}s - {clip.source_end}s")
            
            # Execute FFmpeg with GPU acceleration
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"FFmpeg failed for clip {clip_index}: {stderr.decode()}")
                return None
            
            # Verify output file
            if not output_path.exists():
                logger.error(f"Output file not created: {output_path}")
                return None
            
            file_size = output_path.stat().st_size
            render_time = time.time() - start_time
            
            # Calculate performance metrics
            processing_speed = clip.duration / render_time if render_time > 0 else 0
            
            logger.info(
                f"Clip {clip_index} rendered: {file_size} bytes, "
                f"{render_time:.2f}s, {processing_speed:.2f}x realtime"
            )
            
            return RenderedVideo(
                clip_id=clip.id,
                file_path=str(output_path),
                file_size=file_size,
                duration=clip.duration,
                resolution=config.resolution,
                bitrate=config.bitrate,
                render_time=render_time,
                processing_speed=processing_speed,
                quality_score=getattr(clip, 'quality_score', 0.8)
            )
            
        except Exception as e:
            logger.error(f"Clip {clip_index} rendering failed: {e}")
            return None
    
    async def _build_ffmpeg_command(
        self,
        source_path: str,
        output_path: str,
        start_time: float,
        duration: float,
        config: RenderConfig,
        reframing_frames: List[ReframingFrame] = None
    ) -> List[str]:
        """
        Build optimized FFmpeg command with GPU acceleration
        
        Returns:
            FFmpeg command as list of arguments
        """
        cmd = ["ffmpeg", "-y"]  # -y to overwrite output files
        
        # Hardware acceleration setup
        if self.gpu_available and config.hardware_acceleration:
            # Use NVDEC for decoding
            cmd.extend([
                "-hwaccel", "cuda",
                "-hwaccel_output_format", "cuda",
                "-c:v", "h264_cuvid"
            ])
        
        # Input configuration
        cmd.extend([
            "-ss", str(start_time),
            "-i", source_path,
            "-t", str(duration)
        ])
        
        # Video processing filters
        filters = []
        
        # Smart reframing using MediaPipe face tracking
        if reframing_frames and config.resolution == (720, 1280):
            # Find reframing data for this time range
            relevant_frames = [
                f for f in reframing_frames 
                if start_time <= f.timestamp <= start_time + duration
            ]
            
            if relevant_frames:
                # Use first frame's crop settings (could be enhanced with keyframe interpolation)
                frame = relevant_frames[0]
                crop_filter = f"crop={frame.cropWidth}:{frame.cropHeight}:{frame.cropX}:{frame.cropY}"
                filters.append(crop_filter)
                filters.append(f"scale={config.resolution[0]}:{config.resolution[1]}")
                logger.debug(f"Applied face-centered crop: {crop_filter}")
            else:
                # Fallback to center crop
                filters.append(f"scale={config.resolution[0]}:{config.resolution[1]}")
        elif config.resolution == (720, 1280):
            # Standard center crop for vertical format
            filters.append(f"scale={config.resolution[0]}:{config.resolution[1]}")
            
        # Apply filters
        if filters and config.use_gpu_filters and self.gpu_available:
            # Use GPU filters when available
            filter_chain = ",".join(filters)
            cmd.extend(["-vf", f"{filter_chain}"])
        elif filters:
            # Fallback to CPU filters
            filter_chain = ",".join(filters)
            cmd.extend(["-vf", filter_chain])
        
        # Output encoding
        if self.gpu_available and config.hardware_acceleration:
            # Use NVENC for encoding
            cmd.extend([
                "-c:v", "h264_nvenc",
                "-preset", config.nvenc_preset,
                "-profile:v", "high",
                "-level:v", "4.1",
                "-b:v", config.bitrate,
                "-maxrate", config.bitrate,
                "-bufsize", f"{int(config.bitrate[:-1]) * 2}M"
            ])
        else:
            # Fallback to CPU encoding
            cmd.extend([
                "-c:v", "libx264",
                "-preset", "fast",
                "-profile:v", "high",
                "-level:v", "4.1",
                "-b:v", config.bitrate
            ])
        
        # Audio configuration
        cmd.extend([
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100"
        ])
        
        # Output format
        cmd.extend([
            "-f", config.target_format,
            "-movflags", "+faststart",  # Optimize for web streaming
            output_path
        ])
        
        return cmd
    
    def get_gpu_metrics(self) -> GPUMetrics:
        """Get current GPU utilization metrics"""
        if not self.gpu_available:
            return GPUMetrics(
                available=False,
                utilization=0,
                memory_used=0,
                memory_total=0,
                temperature=0
            )
        
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            
            # Get utilization
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            
            # Get memory info
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            
            # Get temperature
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            
            return GPUMetrics(
                available=True,
                utilization=util.gpu,
                memory_used=mem_info.used,
                memory_total=mem_info.total,
                temperature=temp
            )
            
        except Exception as e:
            logger.error(f"Failed to get GPU metrics: {e}")
            return GPUMetrics(available=False)
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for rendering service"""
        health = {
            "status": "healthy",
            "timestamp": time.time(),
            "gpu": self.get_gpu_metrics(),
            "system": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            },
            "rendering": {
                "concurrent_jobs": self.concurrent_renders,
                "max_concurrent": self.max_concurrent_renders,
                "queue_size": self.render_queue.qsize()
            }
        }
        
        # Determine overall health status
        if not self.gpu_available:
            health["status"] = "degraded"
            health["warning"] = "GPU not available, using CPU fallback"
        
        if health["system"]["memory_percent"] > 90:
            health["status"] = "unhealthy"
            health["error"] = "High memory usage"
        
        if health["rendering"]["queue_size"] > 50:
            health["status"] = "degraded" 
            health["warning"] = "High queue backlog"
        
        return health
    
    async def estimate_render_time(self, edl: EDL) -> float:
        """
        Estimate total rendering time for an EDL
        
        Args:
            edl: Edit Decision List
            
        Returns:
            Estimated render time in seconds
        """
        total_duration = sum(clip.duration for clip in edl.timeline if clip.type == "clip")
        
        # Performance estimates based on GPU availability
        if self.gpu_available:
            # GPU: 2-3x realtime performance
            performance_multiplier = 0.4  # 2.5x average
        else:
            # CPU: 0.5-1x realtime performance
            performance_multiplier = 1.5  # 0.67x average
        
        # Add overhead for setup and file I/O
        overhead_per_clip = 2.0  # seconds
        num_clips = len([c for c in edl.timeline if c.type == "clip"])
        
        estimated_time = (total_duration * performance_multiplier) + (num_clips * overhead_per_clip)
        
        return max(estimated_time, 10.0)  # Minimum 10 seconds


# Global renderer instance
_renderer_instance: Optional[GPURenderingEngine] = None


def get_renderer() -> GPURenderingEngine:
    """Get or create global renderer instance"""
    global _renderer_instance
    if _renderer_instance is None:
        _renderer_instance = GPURenderingEngine()
    return _renderer_instance


async def render_video_from_edl(
    edl: EDL,
    source_video_path: str,
    output_directory: str,
    config: RenderConfig = None
) -> List[RenderedVideo]:
    """
    Convenience function for rendering videos from EDL
    
    Args:
        edl: Edit Decision List
        source_video_path: Path to source video
        output_directory: Output directory
        config: Optional rendering configuration
        
    Returns:
        List of rendered videos
    """
    renderer = get_renderer()
    return await renderer.render_from_edl(edl, source_video_path, output_directory, config)