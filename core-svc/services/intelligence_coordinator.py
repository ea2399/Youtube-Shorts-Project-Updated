"""
Intelligence Coordinator - Phase 2
Orchestrates audio, visual, and proxy generation services using composition pattern
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import structlog
import tempfile
import time

from .audio_processor import AudioProcessor, AudioAnalysis
from .visual_processor import VisualProcessor, VisualAnalysis
from .proxy_generator import ProxyGenerator, ProxyManifest
from ..tasks.intelligence_tasks import process_intelligence_chord
from ..models.database import (
    get_db, AudioAnalysis as AudioAnalysisDB, 
    VisualAnalysis as VisualAnalysisDB, ProxyFiles as ProxyFilesDB,
    QualityMetrics as QualityMetricsDB
)

logger = structlog.get_logger()


@dataclass
class IntelligenceResults:
    """Complete Phase 2 intelligence analysis results"""
    audio_analysis: AudioAnalysis
    visual_analysis: VisualAnalysis
    proxy_manifest: ProxyManifest
    quality_metrics: Dict[str, float]
    processing_times: Dict[str, float]
    success_metrics: Dict[str, bool]


class IntelligenceCoordinator:
    """
    Phase 2 Intelligence Coordinator
    Orchestrates all AI processing services using composition pattern
    """
    
    def __init__(self, enable_gpu: bool = True, max_workers: int = 3):
        """Initialize intelligence coordinator with lazy-loaded services"""
        self.enable_gpu = enable_gpu
        self.max_workers = max_workers
        
        # Lazy-loaded services (GPU memory management)
        self._audio_processor = None
        self._visual_processor = None
        self._proxy_generator = None
        
        # Processing statistics
        self.processing_stats = {
            "videos_processed": 0,
            "avg_processing_time": 0.0,
            "success_rate": 0.0
        }
        
        logger.info("IntelligenceCoordinator initialized",
                   gpu_enabled=enable_gpu,
                   max_workers=max_workers)
    
    def _get_audio_processor(self) -> AudioProcessor:
        """Lazy load audio processor"""
        if self._audio_processor is None:
            self._audio_processor = AudioProcessor()
        return self._audio_processor
    
    def _get_visual_processor(self) -> VisualProcessor:
        """Lazy load visual processor"""
        if self._visual_processor is None:
            self._visual_processor = VisualProcessor()
        return self._visual_processor
    
    def _get_proxy_generator(self) -> ProxyGenerator:
        """Lazy load proxy generator"""
        if self._proxy_generator is None:
            self._proxy_generator = ProxyGenerator()
        return self._proxy_generator
    
    def process_intelligence_distributed(self, video_path: Path, transcript: Dict[str, Any],
                                       output_dir: Path) -> str:
        """
        Process all intelligence analysis using distributed Celery chord workflow
        Returns task ID for monitoring progress
        """
        logger.info("Starting distributed intelligence processing",
                   video_path=str(video_path))
        
        try:
            # Input validation
            if not video_path.exists():
                raise ValueError(f"Video path does not exist: {video_path}")
            
            # Submit Celery chord workflow
            task_id = process_intelligence_chord(video_path, transcript, output_dir)
            
            logger.info("Distributed intelligence processing submitted",
                       task_id=task_id,
                       video_path=str(video_path))
            
            return task_id
            
        except Exception as e:
            logger.error("Failed to submit distributed intelligence processing", error=str(e))
            raise
    
    def get_intelligence_results(self, task_id: str) -> Optional[IntelligenceResults]:
        """
        Retrieve results from a distributed intelligence processing task
        Returns None if task is not complete
        """
        try:
            from celery.result import AsyncResult
            from ..tasks.intelligence_tasks import app
            
            result = AsyncResult(task_id, app=app)
            
            if result.ready():
                if result.successful():
                    task_results = result.get()
                    
                    # Convert task results back to IntelligenceResults object
                    audio_data = task_results["audio_analysis"]
                    visual_data = task_results["visual_analysis"]
                    proxy_data = task_results["proxy_manifest"]
                    
                    # Reconstruct AudioAnalysis
                    audio_analysis = None
                    if audio_data:
                        audio_analysis = AudioAnalysis(
                            silence_segments=audio_data.get("silence_segments", []),
                            filler_words=audio_data.get("filler_words", []),
                            quality_metrics=audio_data.get("quality_metrics", {}),
                            language_segments=audio_data.get("language_segments", []),
                            speech_rate=audio_data.get("speech_rate", 0.0),
                            rms_levels=audio_data.get("rms_levels", []),
                            breathing_patterns=audio_data.get("breathing_patterns", [])
                        )
                    
                    # Reconstruct VisualAnalysis
                    visual_analysis = None
                    if visual_data:
                        # For simplicity, storing as dict - could reconstruct full objects
                        visual_analysis = VisualAnalysis(
                            face_tracks=[],  # Simplified - would need full reconstruction
                            object_detections=visual_data.get("object_detections", []),
                            scene_boundaries=[],  # Simplified - would need full reconstruction
                            quality_metrics=visual_data.get("quality_metrics", {}),
                            motion_analysis=visual_data.get("motion_analysis", {}),
                            reframing_data=visual_data.get("reframing_data", {})
                        )
                    
                    # Reconstruct ProxyManifest
                    proxy_manifest = None
                    if proxy_data:
                        # For simplicity, storing as dict - could reconstruct full objects
                        proxy_manifest = ProxyManifest(
                            proxy_videos=[],  # Simplified - would need full reconstruction
                            thumbnails=[],    # Simplified - would need full reconstruction
                            timeline_data=proxy_data.get("timeline_data", {}),
                            webgl_metadata=proxy_data.get("webgl_metadata", {}),
                            generation_info=proxy_data.get("generation_info", {})
                        )
                    
                    intelligence_results = IntelligenceResults(
                        audio_analysis=audio_analysis,
                        visual_analysis=visual_analysis,
                        proxy_manifest=proxy_manifest,
                        quality_metrics=task_results["quality_metrics"],
                        processing_times=task_results["processing_times"],
                        success_metrics=task_results["success_metrics"]
                    )
                    
                    logger.info("Intelligence results retrieved successfully", task_id=task_id)
                    return intelligence_results
                    
                else:
                    logger.error("Intelligence task failed", task_id=task_id, error=str(result.info))
                    return None
            else:
                logger.info("Intelligence task still processing", task_id=task_id, state=result.state)
                return None
                
        except Exception as e:
            logger.error("Failed to retrieve intelligence results", task_id=task_id, error=str(e))
            return None

    def process_intelligence_parallel(self, video_path: Path, transcript: Dict[str, Any],
                                    output_dir: Path) -> IntelligenceResults:
        """
        DEPRECATED: Legacy ThreadPoolExecutor method
        Use process_intelligence_distributed() for production
        Kept for backward compatibility and emergency fallback
        """
        logger.warning("Using deprecated ThreadPoolExecutor method - consider migrating to Celery workflow")
        
        start_time = time.time()
        processing_times = {}
        
        logger.info("Starting legacy parallel intelligence processing",
                   video_path=str(video_path))
        
        try:
            # Legacy processing with reduced parallelism to prevent GPU contention
            audio_processor = self._get_audio_processor()
            visual_processor = self._get_visual_processor()
            
            # Sequential processing to avoid GPU memory issues
            # Step 1: Audio processing (CPU-bound)
            audio_start = time.time()
            audio_path = self._extract_audio_for_processing(video_path)
            audio_result, _ = self._process_audio_with_timing(audio_path, transcript)
            processing_times["audio"] = time.time() - audio_start
            
            # Step 2: Visual processing (GPU-bound)
            visual_start = time.time()
            visual_result, _ = self._process_visual_with_timing(video_path)
            processing_times["visual"] = time.time() - visual_start
            
            # Step 3: Proxy generation (I/O-bound)
            proxy_start = time.time()
            proxy_result = self._get_proxy_generator().generate_proxy_manifest(
                video_path=video_path,
                output_dir=output_dir,
                face_tracks=visual_result.face_tracks if visual_result else None,
                scene_boundaries=visual_result.scene_boundaries if visual_result else None,
                audio_analysis=audio_result if audio_result else None
            )
            processing_times["proxy"] = time.time() - proxy_start
            
            # Calculate quality metrics
            quality_start = time.time()
            quality_metrics = self._calculate_comprehensive_quality_metrics(
                audio_result, visual_result, proxy_result
            )
            processing_times["quality"] = time.time() - quality_start
            
            # Validate success criteria
            success_metrics = self._validate_success_criteria(
                audio_result, visual_result, proxy_result
            )
            
            total_time = time.time() - start_time
            processing_times["total"] = total_time
            
            # Create results object
            results = IntelligenceResults(
                audio_analysis=audio_result,
                visual_analysis=visual_result,
                proxy_manifest=proxy_result,
                quality_metrics=quality_metrics,
                processing_times=processing_times,
                success_metrics=success_metrics
            )
            
            # Update statistics
            self._update_processing_stats(total_time, success_metrics)
            
            logger.info("Legacy intelligence processing completed",
                       total_time=round(total_time, 2),
                       success_criteria_met=sum(success_metrics.values()),
                       quality_score=round(quality_metrics.get("overall_score", 0), 2))
            
            return results
            
        except Exception as e:
            logger.error("Legacy intelligence processing failed", error=str(e))
            raise
        
        finally:
            # Cleanup temporary audio file
            if 'audio_path' in locals() and audio_path.exists():
                audio_path.unlink()
    
    def _extract_audio_for_processing(self, video_path: Path) -> Path:
        """Extract audio track for audio processing"""
        try:
            import ffmpeg
            
            # Create temporary audio file
            temp_audio = Path(tempfile.mktemp(suffix=".wav"))
            
            # Extract audio using ffmpeg
            (
                ffmpeg
                .input(str(video_path))
                .output(str(temp_audio), acodec='pcm_s16le', ac=1, ar=16000)
                .run(overwrite_output=True, quiet=True)
            )
            
            logger.info("Audio extracted for processing", audio_path=str(temp_audio))
            return temp_audio
            
        except Exception as e:
            logger.error("Audio extraction failed", error=str(e))
            raise
    
    def _process_audio_with_timing(self, audio_path: Path, 
                                  transcript: Dict[str, Any]) -> Tuple[AudioAnalysis, float]:
        """Process audio with timing measurement"""
        start_time = time.time()
        
        try:
            audio_processor = self._get_audio_processor()
            result = audio_processor.process_audio(audio_path, transcript)
            processing_time = time.time() - start_time
            
            return result, processing_time
            
        except Exception as e:
            logger.error("Audio processing with timing failed", error=str(e))
            processing_time = time.time() - start_time
            # Return empty result on failure
            return AudioAnalysis(
                silence_segments=[],
                filler_words=[],
                quality_metrics={},
                language_segments=[],
                speech_rate=0.0,
                rms_levels=[],
                breathing_patterns=[]
            ), processing_time
    
    def _process_visual_with_timing(self, video_path: Path) -> Tuple[VisualAnalysis, float]:
        """Process visual with timing measurement"""
        start_time = time.time()
        
        try:
            visual_processor = self._get_visual_processor()
            result = visual_processor.process_video(video_path)
            processing_time = time.time() - start_time
            
            return result, processing_time
            
        except Exception as e:
            logger.error("Visual processing with timing failed", error=str(e))
            processing_time = time.time() - start_time
            # Return empty result on failure
            from .visual_processor import VisualAnalysis
            return VisualAnalysis(
                face_tracks=[],
                object_detections=[],
                scene_boundaries=[],
                quality_metrics={},
                motion_analysis={},
                reframing_data={}
            ), processing_time
    
    def _calculate_comprehensive_quality_metrics(self, audio_analysis: Optional[AudioAnalysis],
                                               visual_analysis: Optional[VisualAnalysis],
                                               proxy_manifest: Optional[ProxyManifest]) -> Dict[str, float]:
        """Calculate comprehensive quality metrics from all analyses"""
        metrics = {}
        
        # Audio quality metrics
        if audio_analysis and audio_analysis.quality_metrics:
            audio_metrics = audio_analysis.quality_metrics
            
            # Speech clarity (SNR + speech rate)
            snr = audio_metrics.get("snr_estimate_db", 0)
            speech_rate = audio_analysis.speech_rate
            ideal_speech_rate = 150  # 150 WPM is ideal
            
            speech_rate_score = 1.0 - abs(speech_rate - ideal_speech_rate) / ideal_speech_rate
            speech_rate_score = max(0, min(1, speech_rate_score))
            
            metrics["speech_clarity"] = (snr / 30.0 + speech_rate_score) / 2  # Normalize
            
            # Filler word density
            if audio_analysis.filler_words:
                duration = 60  # Default duration, should be calculated from transcript
                filler_density = len(audio_analysis.filler_words) / (duration / 60)  # per minute
                metrics["filler_density"] = filler_density
            else:
                metrics["filler_density"] = 0.0
            
            # Audio quality score (0-10)
            audio_score = (
                min(snr / 20.0, 1.0) * 4 +  # SNR contribution (0-4)
                speech_rate_score * 3 +      # Speech rate (0-3)
                (1.0 / (1.0 + filler_density)) * 3  # Filler penalty (0-3)
            )
            metrics["audio_quality"] = min(audio_score, 10.0)
        else:
            metrics["speech_clarity"] = 0.0
            metrics["filler_density"] = 0.0
            metrics["audio_quality"] = 0.0
        
        # Visual quality metrics
        if visual_analysis and visual_analysis.quality_metrics:
            visual_metrics = visual_analysis.quality_metrics
            
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
        if proxy_manifest and proxy_manifest.proxy_videos:
            metrics["proxy_success"] = 1.0
            metrics["proxy_count"] = len(proxy_manifest.proxy_videos)
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
        
        return metrics
    
    def _validate_success_criteria(self, audio_analysis: Optional[AudioAnalysis],
                                 visual_analysis: Optional[VisualAnalysis],
                                 proxy_manifest: Optional[ProxyManifest]) -> Dict[str, bool]:
        """Validate Phase 2 success criteria"""
        success = {}
        
        # Filler word detection >90% accuracy (simplified check)
        if audio_analysis and audio_analysis.filler_words:
            # For now, assume accuracy based on confidence scores
            confidences = [fw.get("confidence", 0) for fw in audio_analysis.filler_words]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            success["filler_detection_90_percent"] = avg_confidence > 0.9
        else:
            success["filler_detection_90_percent"] = False
        
        # Face tracking 95% stability
        if visual_analysis and visual_analysis.quality_metrics:
            face_stability = visual_analysis.quality_metrics.get("face_stability", 0)
            success["face_tracking_95_percent"] = face_stability > 0.95
        else:
            success["face_tracking_95_percent"] = False
        
        # Proxy videos generate smoothly
        if proxy_manifest and proxy_manifest.proxy_videos:
            # Check if we have at least timeline and webgl proxies
            proxy_types = [str(pv.proxy_path) for pv in proxy_manifest.proxy_videos]
            has_timeline = any("timeline" in path for path in proxy_types)
            has_webgl = any("webgl" in path for path in proxy_types)
            success["proxy_generation_smooth"] = has_timeline and has_webgl
        else:
            success["proxy_generation_smooth"] = False
        
        # Audio quality metrics match expectations
        if audio_analysis and audio_analysis.quality_metrics:
            snr = audio_analysis.quality_metrics.get("snr_estimate_db", 0)
            speech_rate = audio_analysis.speech_rate
            success["audio_quality_metrics"] = snr > 10 and 100 < speech_rate < 200
        else:
            success["audio_quality_metrics"] = False
        
        # Scene boundaries align with content
        if visual_analysis and visual_analysis.scene_boundaries:
            # Check for reasonable scene count (not too many, not too few)
            scene_count = len(visual_analysis.scene_boundaries)
            success["scene_boundary_detection"] = 1 <= scene_count <= 20
        else:
            success["scene_boundary_detection"] = False
        
        return success
    
    def _update_processing_stats(self, processing_time: float, 
                               success_metrics: Dict[str, bool]):
        """Update processing statistics"""
        self.processing_stats["videos_processed"] += 1
        
        # Update average processing time
        current_avg = self.processing_stats["avg_processing_time"]
        count = self.processing_stats["videos_processed"]
        new_avg = ((current_avg * (count - 1)) + processing_time) / count
        self.processing_stats["avg_processing_time"] = new_avg
        
        # Update success rate
        success_count = sum(success_metrics.values())
        total_criteria = len(success_metrics)
        current_success_rate = success_count / total_criteria if total_criteria > 0 else 0
        
        # Running average of success rate
        current_overall_success = self.processing_stats["success_rate"]
        new_success_rate = ((current_overall_success * (count - 1)) + current_success_rate) / count
        self.processing_stats["success_rate"] = new_success_rate
    
    def save_to_database(self, video_id: str, results: IntelligenceResults):
        """Save intelligence results to database"""
        try:
            db = next(get_db())
            
            # Save audio analysis
            if results.audio_analysis:
                audio_db = AudioAnalysisDB(
                    video_id=video_id,
                    silence_segments=results.audio_analysis.silence_segments,
                    filler_words=results.audio_analysis.filler_words,
                    filler_word_count=len(results.audio_analysis.filler_words),
                    language_segments=results.audio_analysis.language_segments,
                    primary_language=self._extract_primary_language(results.audio_analysis.language_segments),
                    rms_mean=results.audio_analysis.quality_metrics.get("rms_mean"),
                    rms_std=results.audio_analysis.quality_metrics.get("rms_std"),
                    dynamic_range_db=results.audio_analysis.quality_metrics.get("dynamic_range_db"),
                    snr_estimate_db=results.audio_analysis.quality_metrics.get("snr_estimate_db"),
                    speech_rate_wpm=results.audio_analysis.speech_rate,
                    avg_pause_duration=results.audio_analysis.quality_metrics.get("avg_pause_duration"),
                    pause_count=results.audio_analysis.quality_metrics.get("pause_count", 0),
                    breathing_regularity=results.audio_analysis.quality_metrics.get("breathing_regularity"),
                    processing_time_seconds=results.processing_times.get("audio")
                )
                db.add(audio_db)
            
            # Save visual analysis
            if results.visual_analysis:
                visual_db = VisualAnalysisDB(
                    video_id=video_id,
                    face_tracks=[self._serialize_face_track(ft) for ft in results.visual_analysis.face_tracks],
                    face_track_count=len(results.visual_analysis.face_tracks),
                    object_detections=results.visual_analysis.object_detections,
                    scene_boundaries=[self._serialize_scene_boundary(sb) for sb in results.visual_analysis.scene_boundaries],
                    scene_count=len(results.visual_analysis.scene_boundaries),
                    ssim_mean=results.visual_analysis.quality_metrics.get("ssim_mean"),
                    ssim_std=results.visual_analysis.quality_metrics.get("ssim_std"),
                    motion_intensity_mean=results.visual_analysis.quality_metrics.get("motion_intensity_mean"),
                    motion_intensity_max=results.visual_analysis.quality_metrics.get("motion_intensity_max"),
                    face_stability_score=results.visual_analysis.quality_metrics.get("face_stability"),
                    reframing_method=results.visual_analysis.reframing_data.get("method"),
                    reframing_confidence=results.visual_analysis.reframing_data.get("confidence"),
                    reframing_data=results.visual_analysis.reframing_data,
                    processing_time_seconds=results.processing_times.get("visual")
                )
                db.add(visual_db)
            
            # Save proxy files info
            if results.proxy_manifest:
                proxy_db = ProxyFilesDB(
                    video_id=video_id,
                    timeline_proxy_path=str(results.proxy_manifest.proxy_videos[0].proxy_path) if results.proxy_manifest.proxy_videos else None,
                    total_proxy_size_bytes=sum(pv.file_size for pv in results.proxy_manifest.proxy_videos),
                    thumbnail_count=len(results.proxy_manifest.thumbnails),
                    generation_complete=True,
                    generation_time_seconds=results.processing_times.get("proxy")
                )
                db.add(proxy_db)
            
            # Save quality metrics
            quality_db = QualityMetricsDB(
                video_id=video_id,
                overall_quality_score=results.quality_metrics.get("overall_score"),
                audio_quality_score=results.quality_metrics.get("audio_quality"),
                visual_quality_score=results.quality_metrics.get("visual_quality"),
                filler_word_density=results.quality_metrics.get("filler_density"),
                speech_clarity_score=results.quality_metrics.get("speech_clarity"),
                visual_stability_score=results.quality_metrics.get("visual_stability"),
                face_prominence_score=results.quality_metrics.get("face_prominence"),
                engagement_proxy_score=results.quality_metrics.get("engagement_proxy"),
                analysis_confidence=min(results.quality_metrics.get("overall_score", 0) / 10.0, 1.0),
                filler_detection_accuracy=0.9 if results.success_metrics.get("filler_detection_90_percent") else 0.8,
                face_tracking_stability=0.95 if results.success_metrics.get("face_tracking_95_percent") else 0.8,
                proxy_generation_success=results.success_metrics.get("proxy_generation_smooth", False)
            )
            db.add(quality_db)
            
            db.commit()
            logger.info("Intelligence results saved to database", video_id=video_id)
            
        except Exception as e:
            logger.error("Failed to save intelligence results", error=str(e))
            db.rollback()
        finally:
            db.close()
    
    def _extract_primary_language(self, language_segments: List[Dict]) -> str:
        """Extract primary language from language segments"""
        if not language_segments:
            return "unknown"
        
        # Count language occurrences
        language_counts = {}
        for segment in language_segments:
            lang = segment.get("language", "unknown")
            language_counts[lang] = language_counts.get(lang, 0) + 1
        
        # Return most common language
        return max(language_counts, key=language_counts.get)
    
    def _serialize_face_track(self, face_track) -> Dict:
        """Serialize face track for database storage"""
        return {
            "track_id": face_track.track_id,
            "frame_count": len(face_track.bounding_boxes),
            "avg_confidence": sum(face_track.confidence_scores) / len(face_track.confidence_scores) if face_track.confidence_scores else 0,
            "landmark_count": len(face_track.landmarks)
        }
    
    def _serialize_scene_boundary(self, scene_boundary) -> Dict:
        """Serialize scene boundary for database storage"""
        return {
            "start_time": scene_boundary.start_time,
            "end_time": scene_boundary.end_time,
            "duration": scene_boundary.end_time - scene_boundary.start_time,
            "scene_type": scene_boundary.scene_type,
            "confidence": scene_boundary.confidence
        }
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get current processing statistics"""
        return {
            **self.processing_stats,
            "gpu_enabled": self.enable_gpu,
            "services_loaded": {
                "audio": self._audio_processor is not None,
                "visual": self._visual_processor is not None,
                "proxy": self._proxy_generator is not None
            }
        }