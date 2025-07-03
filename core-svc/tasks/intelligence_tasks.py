"""
Celery Tasks for Phase 2 Intelligence Processing
Provides GPU/CPU resource isolation and distributed processing
"""

from celery import Celery, chord, group
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import structlog
import time
import tempfile
import os

from ..services.audio_processor import AudioProcessor, AudioAnalysis
from ..services.visual_processor import VisualProcessor, VisualAnalysis
from ..services.proxy_generator import ProxyGenerator, ProxyManifest
from ..config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

logger = structlog.get_logger()

# Create Celery app with separate queues
app = Celery('intelligence_engine')
app.conf.update(
    broker_url=CELERY_BROKER_URL,
    result_backend=CELERY_RESULT_BACKEND,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Queue routing for resource isolation
    task_routes={
        'intelligence_tasks.process_audio_task': {'queue': 'cpu_queue'},
        'intelligence_tasks.process_visual_task': {'queue': 'gpu_queue'},
        'intelligence_tasks.generate_proxy_task': {'queue': 'cpu_queue'},
        'intelligence_tasks.calculate_quality_metrics_task': {'queue': 'cpu_queue'},
        'intelligence_tasks.coordination_callback': {'queue': 'cpu_queue'},
    },
    
    # Worker configuration
    worker_prefetch_multiplier=1,  # Prevent GPU memory hoarding
    task_acks_late=True,
    worker_max_tasks_per_child=10,  # Prevent memory leaks
)


@app.task(bind=True, queue='cpu_queue')
def process_audio_task(self, audio_path_str: str, transcript: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
    """
    Process audio with timing measurement
    Runs on CPU queue for resource isolation
    """
    start_time = time.time()
    
    try:
        audio_path = Path(audio_path_str)
        
        # Initialize AudioProcessor (lazy loading)
        audio_processor = AudioProcessor()
        result = audio_processor.process_audio(audio_path, transcript)
        processing_time = time.time() - start_time
        
        # Convert AudioAnalysis to serializable dict
        result_dict = {
            "silence_segments": result.silence_segments,
            "filler_words": result.filler_words,
            "quality_metrics": result.quality_metrics,
            "language_segments": result.language_segments,
            "speech_rate": result.speech_rate,
            "rms_levels": result.rms_levels,
            "breathing_patterns": result.breathing_patterns
        }
        
        logger.info("Audio processing task completed", 
                   processing_time=round(processing_time, 2),
                   task_id=self.request.id)
        
        return result_dict, processing_time
        
    except Exception as e:
        logger.error("Audio processing task failed", 
                    error=str(e), 
                    task_id=self.request.id)
        processing_time = time.time() - start_time
        
        # Return empty result on failure
        empty_result = {
            "silence_segments": [],
            "filler_words": [],
            "quality_metrics": {},
            "language_segments": [],
            "speech_rate": 0.0,
            "rms_levels": [],
            "breathing_patterns": []
        }
        return empty_result, processing_time


@app.task(bind=True, queue='gpu_queue')
def process_visual_task(self, video_path_str: str) -> Tuple[Dict[str, Any], float]:
    """
    Process visual with timing measurement
    Runs on GPU queue for resource isolation
    """
    start_time = time.time()
    
    try:
        video_path = Path(video_path_str)
        
        # Initialize VisualProcessor (lazy loading)
        visual_processor = VisualProcessor()
        result = visual_processor.process_video(video_path)
        processing_time = time.time() - start_time
        
        # Convert VisualAnalysis to serializable dict
        result_dict = {
            "face_tracks": [
                {
                    "track_id": ft.track_id,
                    "bounding_boxes": ft.bounding_boxes,
                    "confidence_scores": ft.confidence_scores,
                    "frame_indices": ft.frame_indices,
                    "landmarks": [
                        {
                            "left_eye": lm.left_eye,
                            "right_eye": lm.right_eye,
                            "nose_tip": lm.nose_tip,
                            "mouth_center": lm.mouth_center,
                            "left_ear": lm.left_ear,
                            "right_ear": lm.right_ear,
                            "confidence": lm.confidence
                        } for lm in ft.landmarks
                    ]
                } for ft in result.face_tracks
            ],
            "object_detections": result.object_detections,
            "scene_boundaries": [
                {
                    "start_frame": sb.start_frame,
                    "end_frame": sb.end_frame,
                    "start_time": sb.start_time,
                    "end_time": sb.end_time,
                    "scene_type": sb.scene_type,
                    "confidence": sb.confidence
                } for sb in result.scene_boundaries
            ],
            "quality_metrics": result.quality_metrics,
            "motion_analysis": result.motion_analysis,
            "reframing_data": result.reframing_data
        }
        
        logger.info("Visual processing task completed", 
                   processing_time=round(processing_time, 2),
                   task_id=self.request.id)
        
        return result_dict, processing_time
        
    except Exception as e:
        logger.error("Visual processing task failed", 
                    error=str(e), 
                    task_id=self.request.id)
        processing_time = time.time() - start_time
        
        # Return empty result on failure
        empty_result = {
            "face_tracks": [],
            "object_detections": [],
            "scene_boundaries": [],
            "quality_metrics": {},
            "motion_analysis": {},
            "reframing_data": {}
        }
        return empty_result, processing_time


@app.task(bind=True, queue='cpu_queue')
def generate_proxy_task(self, video_path_str: str, output_dir_str: str,
                       face_tracks: List = None, scene_boundaries: List = None,
                       audio_analysis: Dict = None) -> Tuple[Dict[str, Any], float]:
    """
    Generate proxy videos and thumbnails
    Runs on CPU queue as it's I/O intensive
    """
    start_time = time.time()
    
    try:
        video_path = Path(video_path_str)
        output_dir = Path(output_dir_str)
        
        # Initialize ProxyGenerator
        proxy_generator = ProxyGenerator()
        
        # Reconstruct objects from serialized data
        reconstructed_audio = None
        if audio_analysis:
            reconstructed_audio = AudioAnalysis(
                silence_segments=audio_analysis.get("silence_segments", []),
                filler_words=audio_analysis.get("filler_words", []),
                quality_metrics=audio_analysis.get("quality_metrics", {}),
                language_segments=audio_analysis.get("language_segments", []),
                speech_rate=audio_analysis.get("speech_rate", 0.0),
                rms_levels=audio_analysis.get("rms_levels", []),
                breathing_patterns=audio_analysis.get("breathing_patterns", [])
            )
        
        result = proxy_generator.generate_proxy_manifest(
            video_path=video_path,
            output_dir=output_dir,
            face_tracks=face_tracks,  # Will be None or reconstructed objects
            scene_boundaries=scene_boundaries,  # Will be None or reconstructed objects
            audio_analysis=reconstructed_audio
        )
        processing_time = time.time() - start_time
        
        # Convert ProxyManifest to serializable dict
        result_dict = {
            "proxy_videos": [
                {
                    "original_path": str(pv.original_path),
                    "proxy_path": str(pv.proxy_path),
                    "resolution": pv.resolution,
                    "duration": pv.duration,
                    "fps": pv.fps,
                    "file_size": pv.file_size,
                    "format": pv.format
                } for pv in result.proxy_videos
            ],
            "thumbnails": [
                {
                    "image_path": str(t.image_path),
                    "timestamp": t.timestamp,
                    "resolution": t.resolution,
                    "scene_type": t.scene_type
                } for t in result.thumbnails
            ],
            "timeline_data": result.timeline_data,
            "webgl_metadata": result.webgl_metadata,
            "generation_info": result.generation_info
        }
        
        logger.info("Proxy generation task completed", 
                   processing_time=round(processing_time, 2),
                   task_id=self.request.id)
        
        return result_dict, processing_time
        
    except Exception as e:
        logger.error("Proxy generation task failed", 
                    error=str(e), 
                    task_id=self.request.id)
        processing_time = time.time() - start_time
        
        # Return empty result on failure
        empty_result = {
            "proxy_videos": [],
            "thumbnails": [],
            "timeline_data": {},
            "webgl_metadata": {},
            "generation_info": {}
        }
        return empty_result, processing_time


@app.task(bind=True, queue='cpu_queue')
def calculate_quality_metrics_task(self, audio_result: Dict, visual_result: Dict, 
                                  proxy_result: Dict) -> Dict[str, float]:
    """
    Calculate comprehensive quality metrics from all analyses
    Runs on CPU queue for resource efficiency
    """
    try:
        metrics = {}
        
        # Audio quality metrics
        if audio_result and audio_result.get("quality_metrics"):
            audio_metrics = audio_result["quality_metrics"]
            
            # Speech clarity (SNR + speech rate)
            snr = audio_metrics.get("snr_estimate_db", 0)
            speech_rate = audio_result.get("speech_rate", 0)
            ideal_speech_rate = 150  # 150 WPM is ideal
            
            speech_rate_score = 1.0 - abs(speech_rate - ideal_speech_rate) / ideal_speech_rate
            speech_rate_score = max(0, min(1, speech_rate_score))
            
            metrics["speech_clarity"] = (snr / 30.0 + speech_rate_score) / 2  # Normalize
            
            # Filler word density
            filler_words = audio_result.get("filler_words", [])
            if filler_words:
                duration = 60  # Default duration, should be calculated from transcript
                filler_density = len(filler_words) / (duration / 60)  # per minute
                metrics["filler_density"] = filler_density
            else:
                metrics["filler_density"] = 0.0
            
            # Audio quality score (0-10)
            audio_score = (
                min(snr / 20.0, 1.0) * 4 +  # SNR contribution (0-4)
                speech_rate_score * 3 +      # Speech rate (0-3)
                (1.0 / (1.0 + metrics["filler_density"])) * 3  # Filler penalty (0-3)
            )
            metrics["audio_quality"] = min(audio_score, 10.0)
        else:
            metrics["speech_clarity"] = 0.0
            metrics["filler_density"] = 0.0
            metrics["audio_quality"] = 0.0
        
        # Visual quality metrics
        if visual_result and visual_result.get("quality_metrics"):
            visual_metrics = visual_result["quality_metrics"]
            
            # Visual stability (SSIM + motion)
            ssim_mean = visual_metrics.get("ssim_mean", 0)
            motion_intensity = visual_metrics.get("motion_intensity_mean", 0)
            face_stability = visual_metrics.get("face_stability", 0)
            
            stability_score = (ssim_mean + face_stability + (1.0 - motion_intensity)) / 3
            metrics["visual_stability"] = stability_score
            
            # Face prominence
            face_quality = visual_metrics.get("face_tracking_quality", 0)
            face_tracks_count = visual_metrics.get("face_tracks_count", 0)
            
            if face_tracks_count > 0:
                metrics["face_prominence"] = face_quality
            else:
                metrics["face_prominence"] = 0.0
            
            # Visual quality score (0-10)
            visual_score = (
                ssim_mean * 3 +           # SSIM (0-3)
                face_quality * 4 +        # Face quality (0-4)
                stability_score * 3       # Stability (0-3)
            )
            metrics["visual_quality"] = min(visual_score, 10.0)
        else:
            metrics["visual_stability"] = 0.0
            metrics["face_prominence"] = 0.0
            metrics["visual_quality"] = 0.0
        
        # Proxy generation success
        if proxy_result and proxy_result.get("proxy_videos"):
            metrics["proxy_success"] = 1.0
            metrics["proxy_count"] = len(proxy_result["proxy_videos"])
        else:
            metrics["proxy_success"] = 0.0
            metrics["proxy_count"] = 0.0
        
        # Overall quality score
        audio_weight = 0.4
        visual_weight = 0.4
        proxy_weight = 0.2
        
        overall_score = (
            metrics["audio_quality"] * audio_weight +
            metrics["visual_quality"] * visual_weight +
            metrics["proxy_success"] * 10.0 * proxy_weight  # Convert to 0-10 scale
        )
        metrics["overall_score"] = overall_score
        
        # Engagement proxy (heuristic)
        engagement_score = (
            metrics["speech_clarity"] * 3 +
            metrics["face_prominence"] * 4 +
            (1.0 / (1.0 + metrics["filler_density"])) * 3
        )
        metrics["engagement_proxy"] = min(engagement_score, 10.0)
        
        logger.info("Quality metrics calculated", 
                   overall_score=round(metrics["overall_score"], 2),
                   task_id=self.request.id)
        
        return metrics
        
    except Exception as e:
        logger.error("Quality metrics calculation failed", 
                    error=str(e), 
                    task_id=self.request.id)
        return {}


@app.task(bind=True, queue='cpu_queue')
def coordination_callback(self, results: List[Tuple[Dict, float]], video_path_str: str, 
                         output_dir_str: str) -> Dict[str, Any]:
    """
    Callback to coordinate all results and generate final intelligence output
    """
    try:
        video_path = Path(video_path_str)
        output_dir = Path(output_dir_str)
        
        # Extract results
        audio_result, audio_time = results[0] if len(results) > 0 else ({}, 0.0)
        visual_result, visual_time = results[1] if len(results) > 1 else ({}, 0.0)
        
        # Generate proxies with available results
        proxy_start = time.time()
        proxy_task_result = generate_proxy_task.delay(
            video_path_str, str(output_dir),
            visual_result.get("face_tracks"),
            visual_result.get("scene_boundaries"), 
            audio_result
        )
        proxy_result, proxy_time = proxy_task_result.get()
        
        # Calculate quality metrics
        quality_start = time.time()
        quality_task_result = calculate_quality_metrics_task.delay(
            audio_result, visual_result, proxy_result
        )
        quality_metrics = quality_task_result.get()
        quality_time = time.time() - quality_start
        
        # Calculate processing times
        processing_times = {
            "audio": audio_time,
            "visual": visual_time,
            "proxy": proxy_time,
            "quality": quality_time,
            "total": audio_time + visual_time + proxy_time + quality_time
        }
        
        # Validate success criteria
        success_metrics = {
            "filler_detection_90_percent": False,
            "face_tracking_95_percent": False,
            "proxy_generation_smooth": False,
            "audio_quality_metrics": False,
            "scene_boundary_detection": False
        }
        
        # Populate success metrics (simplified validation)
        if audio_result and audio_result.get("filler_words"):
            confidences = [fw.get("confidence", 0) for fw in audio_result["filler_words"]]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            success_metrics["filler_detection_90_percent"] = avg_confidence > 0.9
        
        if visual_result and visual_result.get("quality_metrics"):
            face_stability = visual_result["quality_metrics"].get("face_stability", 0)
            success_metrics["face_tracking_95_percent"] = face_stability > 0.95
        
        if proxy_result and proxy_result.get("proxy_videos"):
            proxy_types = [str(pv["proxy_path"]) for pv in proxy_result["proxy_videos"]]
            has_timeline = any("timeline" in path for path in proxy_types)
            has_webgl = any("webgl" in path for path in proxy_types)
            success_metrics["proxy_generation_smooth"] = has_timeline and has_webgl
        
        if audio_result and audio_result.get("quality_metrics"):
            snr = audio_result["quality_metrics"].get("snr_estimate_db", 0)
            speech_rate = audio_result.get("speech_rate", 0)
            success_metrics["audio_quality_metrics"] = snr > 10 and 100 < speech_rate < 200
        
        if visual_result and visual_result.get("scene_boundaries"):
            scene_count = len(visual_result["scene_boundaries"])
            success_metrics["scene_boundary_detection"] = 1 <= scene_count <= 20
        
        # Create final results
        final_results = {
            "audio_analysis": audio_result,
            "visual_analysis": visual_result,
            "proxy_manifest": proxy_result,
            "quality_metrics": quality_metrics,
            "processing_times": processing_times,
            "success_metrics": success_metrics
        }
        
        logger.info("Intelligence coordination completed",
                   total_time=round(processing_times["total"], 2),
                   success_criteria_met=sum(success_metrics.values()),
                   quality_score=round(quality_metrics.get("overall_score", 0), 2),
                   task_id=self.request.id)
        
        return final_results
        
    except Exception as e:
        logger.error("Intelligence coordination failed", 
                    error=str(e), 
                    task_id=self.request.id)
        raise


def process_intelligence_chord(video_path: Path, transcript: Dict[str, Any], 
                              output_dir: Path) -> str:
    """
    Orchestrate intelligence processing using Celery chord workflow
    Returns task ID for monitoring
    """
    logger.info("Starting Celery chord intelligence processing", 
               video_path=str(video_path))
    
    # Create temporary audio file for audio processing
    temp_audio = tempfile.mktemp(suffix=".wav")
    
    try:
        import ffmpeg
        # Extract audio using ffmpeg
        (
            ffmpeg
            .input(str(video_path))
            .output(temp_audio, acodec='pcm_s16le', ac=1, ar=16000)
            .run(overwrite_output=True, quiet=True)
        )
        
        # Create chord workflow: parallel tasks -> coordination callback
        parallel_tasks = group([
            process_audio_task.s(temp_audio, transcript),
            process_visual_task.s(str(video_path))
        ])
        
        callback = coordination_callback.s(str(video_path), str(output_dir))
        
        # Execute chord
        chord_result = chord(parallel_tasks)(callback)
        
        logger.info("Celery chord submitted", 
                   task_id=chord_result.id,
                   video_path=str(video_path))
        
        return chord_result.id
        
    except Exception as e:
        # Cleanup temporary file
        if os.path.exists(temp_audio):
            os.unlink(temp_audio)
        logger.error("Failed to submit intelligence chord", error=str(e))
        raise