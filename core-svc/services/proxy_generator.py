"""
Proxy Video Generation - Phase 2
Creates timeline-optimized proxy videos, thumbnails, and WebGL-compatible formats
"""

import cv2
import numpy as np
import ffmpeg
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
import structlog
import tempfile
import json
import subprocess
import math
from fractions import Fraction

logger = structlog.get_logger()


@dataclass
class ProxyVideo:
    """Proxy video file information"""
    original_path: Path
    proxy_path: Path
    resolution: Tuple[int, int]  # (width, height)
    duration: float
    fps: float
    file_size: int
    format: str


@dataclass
class Thumbnail:
    """Video thumbnail information"""
    image_path: Path
    timestamp: float
    resolution: Tuple[int, int]
    scene_type: str  # keyframe, face, action, etc.


@dataclass
class ProxyManifest:
    """Complete proxy generation manifest"""
    proxy_videos: List[ProxyVideo]
    thumbnails: List[Thumbnail]
    timeline_data: Dict[str, Any]
    webgl_metadata: Dict[str, Any]
    generation_info: Dict[str, Any]


class ProxyGenerator:
    """
    Proxy Video Generation for Phase 2
    Creates responsive timeline-friendly video formats
    """
    
    def __init__(self):
        """Initialize proxy generator"""
        
        # Proxy video configurations
        self.proxy_configs = {
            "timeline": {
                "resolution": (480, 270),  # 480p for timeline scrubbing
                "fps": 15,                 # Lower FPS for faster seeking
                "bitrate": "500k",
                "codec": "libx264",
                "format": "mp4"
            },
            "preview": {
                "resolution": (720, 405),  # 720p for preview
                "fps": 30,
                "bitrate": "1M",
                "codec": "libx264", 
                "format": "mp4"
            },
            "webgl": {
                "resolution": (854, 480),  # WebGL-optimized
                "fps": 30,
                "bitrate": "800k",
                "codec": "libx264",
                "format": "mp4",
                "extra_params": {
                    "movflags": "faststart",  # Enable progressive download
                    "pix_fmt": "yuv420p"      # Ensure compatibility
                }
            }
        }
        
        # Thumbnail configurations
        self.thumbnail_configs = {
            "timeline": {
                "resolution": (160, 90),   # Small timeline thumbs
                "interval": 1.0,           # Every 1 second
                "format": "jpg",
                "quality": 85
            },
            "preview": {
                "resolution": (320, 180),  # Preview thumbnails
                "interval": 5.0,           # Every 5 seconds
                "format": "jpg",
                "quality": 90
            },
            "keyframes": {
                "resolution": (640, 360),  # High-quality keyframes
                "format": "png",           # Lossless for key moments
                "quality": 95
            }
        }
        
        logger.info("ProxyGenerator initialized")
    
    def get_video_info(self, video_path: Path) -> Dict[str, Any]:
        """Extract video metadata using ffprobe"""
        try:
            probe = ffmpeg.probe(str(video_path))
            video_stream = next(
                (stream for stream in probe['streams'] if stream['codec_type'] == 'video'), 
                None
            )
            
            if not video_stream:
                raise ValueError("No video stream found")
            
            # Safely parse frame rate fraction (e.g., "30000/1001" -> 29.97)
            fps_fraction = video_stream['r_frame_rate']
            try:
                fps = float(Fraction(fps_fraction))
            except (ValueError, ZeroDivisionError):
                logger.warning("Invalid frame rate, using default", fps_string=fps_fraction)
                fps = 30.0  # Default fallback
            
            info = {
                "duration": float(probe['format']['duration']),
                "width": int(video_stream['width']),
                "height": int(video_stream['height']),
                "fps": fps,
                "codec": video_stream['codec_name'],
                "bitrate": int(probe['format'].get('bit_rate', 0)),
                "file_size": int(probe['format']['size'])
            }
            
            logger.info("Video info extracted", 
                       duration=round(info["duration"], 2),
                       resolution=f"{info['width']}x{info['height']}",
                       fps=round(info["fps"], 2))
            
            return info
            
        except Exception as e:
            logger.error("Failed to extract video info", error=str(e))
            raise
    
    def create_proxy_video(self, input_path: Path, output_path: Path, 
                          config_name: str = "timeline") -> ProxyVideo:
        """Create proxy video with specified configuration"""
        config = self.proxy_configs.get(config_name, self.proxy_configs["timeline"])
        
        try:
            # Get original video info
            original_info = self.get_video_info(input_path)
            
            # Prepare ffmpeg stream
            input_stream = ffmpeg.input(str(input_path))
            
            # Video filters
            filters = []
            
            # Scale video
            target_width, target_height = config["resolution"]
            filters.append(f"scale={target_width}:{target_height}")
            
            # Frame rate adjustment
            if config["fps"] != original_info["fps"]:
                filters.append(f"fps={config['fps']}")
            
            # Combine filters
            filter_string = ",".join(filters) if filters else None
            
            # Apply filters if needed
            if filter_string:
                video_stream = ffmpeg.filter(input_stream['v'], 'scale', 
                                           target_width, target_height)
                if config["fps"] != original_info["fps"]:
                    video_stream = ffmpeg.filter(video_stream, 'fps', fps=config["fps"])
            else:
                video_stream = input_stream['v']
            
            # Audio stream (copy or transcode)
            audio_stream = input_stream['a']
            
            # Output parameters
            output_params = {
                'vcodec': config["codec"],
                'b:v': config["bitrate"],
                'acodec': 'aac',
                'b:a': '128k'
            }
            
            # Add extra parameters for specific formats
            if "extra_params" in config:
                output_params.update(config["extra_params"])
            
            # Create output
            output_stream = ffmpeg.output(
                video_stream, audio_stream,
                str(output_path),
                **output_params
            )
            
            # Run ffmpeg
            logger.info("Creating proxy video", 
                       config=config_name,
                       input_size=f"{original_info['width']}x{original_info['height']}",
                       output_size=f"{target_width}x{target_height}")
            
            ffmpeg.run(output_stream, overwrite_output=True, quiet=True)
            
            # Verify output and get info
            proxy_info = self.get_video_info(output_path)
            
            proxy_video = ProxyVideo(
                original_path=input_path,
                proxy_path=output_path,
                resolution=(target_width, target_height),
                duration=proxy_info["duration"],
                fps=proxy_info["fps"],
                file_size=proxy_info["file_size"],
                format=config["format"]
            )
            
            logger.info("Proxy video created successfully",
                       output_size_mb=round(proxy_info["file_size"] / 1024 / 1024, 2),
                       compression_ratio=round(original_info["file_size"] / proxy_info["file_size"], 2))
            
            return proxy_video
            
        except Exception as e:
            logger.error("Proxy video creation failed", error=str(e))
            raise
    
    def extract_thumbnails(self, video_path: Path, output_dir: Path, 
                          config_name: str = "timeline",
                          scene_boundaries: Optional[List] = None) -> List[Thumbnail]:
        """Extract thumbnails at specified intervals"""
        config = self.thumbnail_configs.get(config_name, self.thumbnail_configs["timeline"])
        
        try:
            video_info = self.get_video_info(video_path)
            duration = video_info["duration"]
            
            thumbnails = []
            output_dir.mkdir(parents=True, exist_ok=True)
            
            if config_name == "keyframes" and scene_boundaries:
                # Extract keyframes at scene boundaries
                for i, scene in enumerate(scene_boundaries):
                    timestamp = scene.start_time
                    output_path = output_dir / f"keyframe_{i:04d}_{timestamp:.2f}.{config['format']}"
                    
                    self._extract_single_thumbnail(
                        video_path, output_path, timestamp, config
                    )
                    
                    thumbnail = Thumbnail(
                        image_path=output_path,
                        timestamp=timestamp,
                        resolution=config["resolution"],
                        scene_type="keyframe"
                    )
                    thumbnails.append(thumbnail)
            else:
                # Extract thumbnails at regular intervals
                interval = config["interval"]
                num_thumbnails = int(duration / interval) + 1
                
                for i in range(num_thumbnails):
                    timestamp = min(i * interval, duration - 0.1)  # Avoid end-of-file
                    output_path = output_dir / f"thumb_{i:04d}_{timestamp:.2f}.{config['format']}"
                    
                    self._extract_single_thumbnail(
                        video_path, output_path, timestamp, config
                    )
                    
                    thumbnail = Thumbnail(
                        image_path=output_path,
                        timestamp=timestamp,
                        resolution=config["resolution"],
                        scene_type="timeline"
                    )
                    thumbnails.append(thumbnail)
            
            logger.info("Thumbnails extracted", 
                       count=len(thumbnails),
                       config=config_name)
            
            return thumbnails
            
        except Exception as e:
            logger.error("Thumbnail extraction failed", error=str(e))
            return []
    
    def _extract_single_thumbnail(self, video_path: Path, output_path: Path, 
                                 timestamp: float, config: Dict[str, Any]):
        """Extract a single thumbnail at specified timestamp"""
        try:
            width, height = config["resolution"]
            
            # Use ffmpeg to extract frame
            (
                ffmpeg
                .input(str(video_path), ss=timestamp)
                .filter('scale', width, height)
                .output(str(output_path), vframes=1, format='image2')
                .run(overwrite_output=True, quiet=True)
            )
            
        except Exception as e:
            logger.warning("Failed to extract thumbnail", 
                          timestamp=timestamp, 
                          error=str(e))
    
    def create_webgl_metadata(self, video_path: Path, proxy_videos: List[ProxyVideo],
                            thumbnails: List[Thumbnail]) -> Dict[str, Any]:
        """Create WebGL-compatible metadata for web player"""
        try:
            original_info = self.get_video_info(video_path)
            
            # Find WebGL proxy video
            webgl_proxy = next(
                (pv for pv in proxy_videos if "webgl" in str(pv.proxy_path).lower()),
                proxy_videos[0] if proxy_videos else None
            )
            
            # Timeline thumbnails for scrubbing
            timeline_thumbs = [t for t in thumbnails if t.scene_type == "timeline"]
            
            metadata = {
                "version": "1.0",
                "original": {
                    "duration": original_info["duration"],
                    "width": original_info["width"],
                    "height": original_info["height"],
                    "fps": original_info["fps"]
                },
                "proxy": {
                    "url": str(webgl_proxy.proxy_path) if webgl_proxy else None,
                    "width": webgl_proxy.resolution[0] if webgl_proxy else None,
                    "height": webgl_proxy.resolution[1] if webgl_proxy else None,
                    "fps": webgl_proxy.fps if webgl_proxy else None
                } if webgl_proxy else None,
                "thumbnails": {
                    "count": len(timeline_thumbs),
                    "interval": timeline_thumbs[1].timestamp - timeline_thumbs[0].timestamp if len(timeline_thumbs) > 1 else 1.0,
                    "urls": [str(t.image_path) for t in timeline_thumbs],
                    "width": timeline_thumbs[0].resolution[0] if timeline_thumbs else 160,
                    "height": timeline_thumbs[0].resolution[1] if timeline_thumbs else 90
                },
                "timeline": {
                    "seek_precision": "frame",  # Frame-accurate seeking
                    "supported_formats": ["mp4", "webm"],
                    "adaptive_quality": True,
                    "buffer_ahead": 5.0  # Buffer 5 seconds ahead
                },
                "features": {
                    "frame_seeking": True,
                    "timeline_scrubbing": True,
                    "adaptive_streaming": False,  # Could be added later
                    "hardware_acceleration": True
                }
            }
            
            logger.info("WebGL metadata created",
                       proxy_available=webgl_proxy is not None,
                       thumbnails_count=len(timeline_thumbs))
            
            return metadata
            
        except Exception as e:
            logger.error("WebGL metadata creation failed", error=str(e))
            return {}
    
    def create_timeline_data(self, video_path: Path, face_tracks: List = None,
                           scene_boundaries: List = None, 
                           audio_analysis = None) -> Dict[str, Any]:
        """Create timeline-specific data for editor UI"""
        try:
            video_info = self.get_video_info(video_path)
            
            timeline_data = {
                "duration": video_info["duration"],
                "fps": video_info["fps"],
                "resolution": {
                    "width": video_info["width"],
                    "height": video_info["height"]
                },
                "tracks": {
                    "video": {
                        "type": "video",
                        "duration": video_info["duration"],
                        "keyframes": []
                    },
                    "audio": {
                        "type": "audio", 
                        "duration": video_info["duration"],
                        "waveform": None  # Could add waveform data
                    }
                },
                "markers": [],
                "annotations": []
            }
            
            # Add scene boundaries as markers
            if scene_boundaries:
                for i, scene in enumerate(scene_boundaries):
                    timeline_data["markers"].append({
                        "type": "scene_boundary",
                        "time": scene.start_time,
                        "label": f"Scene {i+1}",
                        "confidence": scene.confidence
                    })
            
            # Add face tracking annotations
            if face_tracks:
                for track in face_tracks:
                    if track.frame_indices and track.confidence_scores:
                        fps = video_info["fps"]
                        start_time = track.frame_indices[0] / fps
                        end_time = track.frame_indices[-1] / fps
                        avg_confidence = np.mean(track.confidence_scores)
                        
                        timeline_data["annotations"].append({
                            "type": "face_track",
                            "start_time": start_time,
                            "end_time": end_time,
                            "track_id": track.track_id,
                            "confidence": avg_confidence,
                            "data": {
                                "frame_count": len(track.frame_indices),
                                "avg_confidence": avg_confidence
                            }
                        })
            
            # Add audio analysis markers
            if audio_analysis and hasattr(audio_analysis, 'filler_words'):
                for filler in audio_analysis.filler_words:
                    timeline_data["markers"].append({
                        "type": "filler_word",
                        "time": filler.get("start", 0),
                        "duration": filler.get("end", 0) - filler.get("start", 0),
                        "label": filler.get("word", ""),
                        "confidence": filler.get("confidence", 0),
                        "language": filler.get("language", "unknown")
                    })
            
            logger.info("Timeline data created",
                       markers=len(timeline_data["markers"]),
                       annotations=len(timeline_data["annotations"]))
            
            return timeline_data
            
        except Exception as e:
            logger.error("Timeline data creation failed", error=str(e))
            return {}
    
    def generate_proxy_manifest(self, video_path: Path, output_dir: Path,
                               face_tracks: List = None,
                               scene_boundaries: List = None,
                               audio_analysis = None) -> ProxyManifest:
        """
        Complete proxy generation pipeline
        Creates all proxy videos, thumbnails, and metadata
        """
        logger.info("Starting proxy generation", video_path=str(video_path))
        
        # Input validation
        if not video_path or not video_path.exists():
            raise ValueError(f"Video path does not exist: {video_path}")
        
        if not video_path.is_file():
            raise ValueError(f"Video path is not a file: {video_path}")
        
        # Check file size (limit to 10GB for safety)
        file_size = video_path.stat().st_size
        if file_size > 10 * 1024 * 1024 * 1024:  # 10GB
            raise ValueError(f"Video file too large: {file_size / (1024**3):.1f}GB")
        
        # Validate video format
        valid_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'}
        if video_path.suffix.lower() not in valid_extensions:
            raise ValueError(f"Unsupported video format: {video_path.suffix}")
        
        try:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories
            proxy_dir = output_dir / "proxy"
            thumb_dir = output_dir / "thumbnails"
            proxy_dir.mkdir(exist_ok=True)
            thumb_dir.mkdir(exist_ok=True)
            
            # Step 1: Create proxy videos
            proxy_videos = []
            
            for config_name in ["timeline", "preview", "webgl"]:
                proxy_path = proxy_dir / f"proxy_{config_name}.mp4"
                
                try:
                    proxy_video = self.create_proxy_video(
                        video_path, proxy_path, config_name
                    )
                    proxy_videos.append(proxy_video)
                except Exception as e:
                    logger.warning("Failed to create proxy video", 
                                 config=config_name, 
                                 error=str(e))
            
            # Step 2: Extract thumbnails
            thumbnails = []
            
            # Timeline thumbnails
            timeline_thumbs = self.extract_thumbnails(
                video_path, thumb_dir / "timeline", "timeline"
            )
            thumbnails.extend(timeline_thumbs)
            
            # Preview thumbnails
            preview_thumbs = self.extract_thumbnails(
                video_path, thumb_dir / "preview", "preview"
            )
            thumbnails.extend(preview_thumbs)
            
            # Keyframe thumbnails (if scene boundaries available)
            if scene_boundaries:
                keyframe_thumbs = self.extract_thumbnails(
                    video_path, thumb_dir / "keyframes", "keyframes", scene_boundaries
                )
                thumbnails.extend(keyframe_thumbs)
            
            # Step 3: Create WebGL metadata
            webgl_metadata = self.create_webgl_metadata(
                video_path, proxy_videos, thumbnails
            )
            
            # Step 4: Create timeline data
            timeline_data = self.create_timeline_data(
                video_path, face_tracks, scene_boundaries, audio_analysis
            )
            
            # Step 5: Generation info
            generation_info = {
                "timestamp": "",  # Will be set by caller
                "original_file": str(video_path),
                "output_directory": str(output_dir),
                "proxy_count": len(proxy_videos),
                "thumbnail_count": len(thumbnails),
                "total_size_mb": sum(pv.file_size for pv in proxy_videos) / 1024 / 1024
            }
            
            # Step 6: Save metadata files
            manifest_path = output_dir / "manifest.json"
            webgl_path = output_dir / "webgl.json"
            timeline_path = output_dir / "timeline.json"
            
            # Save JSON files
            with open(webgl_path, 'w') as f:
                json.dump(webgl_metadata, f, indent=2)
            
            with open(timeline_path, 'w') as f:
                json.dump(timeline_data, f, indent=2)
            
            manifest = ProxyManifest(
                proxy_videos=proxy_videos,
                thumbnails=thumbnails,
                timeline_data=timeline_data,
                webgl_metadata=webgl_metadata,
                generation_info=generation_info
            )
            
            # Save complete manifest
            manifest_dict = {
                "proxy_videos": [
                    {
                        "original_path": str(pv.original_path),
                        "proxy_path": str(pv.proxy_path),
                        "resolution": pv.resolution,
                        "duration": pv.duration,
                        "fps": pv.fps,
                        "file_size": pv.file_size,
                        "format": pv.format
                    } for pv in proxy_videos
                ],
                "thumbnails": [
                    {
                        "image_path": str(t.image_path),
                        "timestamp": t.timestamp,
                        "resolution": t.resolution,
                        "scene_type": t.scene_type
                    } for t in thumbnails
                ],
                "timeline_data": timeline_data,
                "webgl_metadata": webgl_metadata,
                "generation_info": generation_info
            }
            
            with open(manifest_path, 'w') as f:
                json.dump(manifest_dict, f, indent=2)
            
            logger.info("Proxy generation completed",
                       proxy_videos=len(proxy_videos),
                       thumbnails=len(thumbnails),
                       total_size_mb=round(generation_info["total_size_mb"], 2))
            
            return manifest
            
        except Exception as e:
            logger.error("Proxy generation failed", error=str(e))
            raise