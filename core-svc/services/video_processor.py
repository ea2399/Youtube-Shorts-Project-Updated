"""
Video Processing Service - Phase 1 & 2
Integrates Phase 2 intelligence engine with existing processing logic
"""

import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
import structlog
import uuid

# Import existing processing modules
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from extract_shorts import create_pause_based_segments, create_multi_pass_analysis, filter_context_aware_clips
from cut_clips import cut_clip, create_subtitle_file
from reframe import reframe_to_vertical
import openai

from ..config import OPENAI_API_KEY, STORAGE_PATH
from .intelligence_coordinator import IntelligenceCoordinator, IntelligenceResults

logger = structlog.get_logger()


class VideoProcessingService:
    """
    Service wrapper for video processing pipeline with Phase 2 intelligence
    Maintains existing functionality while adding AI-powered analysis
    """
    
    def __init__(self, enable_phase2: bool = True):
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
        self.enable_phase2 = enable_phase2
        
        # Phase 2 intelligence coordinator (lazy loaded)
        self._intelligence_coordinator = None
        
        logger.info("VideoProcessingService initialized", 
                   phase2_enabled=enable_phase2,
                   openai_configured=self.client is not None)
    
    def _get_intelligence_coordinator(self) -> Optional[IntelligenceCoordinator]:
        """Lazy load intelligence coordinator for Phase 2"""
        if not self.enable_phase2:
            return None
            
        if self._intelligence_coordinator is None:
            self._intelligence_coordinator = IntelligenceCoordinator()
        
        return self._intelligence_coordinator
        
    def download_video_from_url(self, url: str, output_dir: Path) -> Path:
        """Download video from URL - wrapper for existing function"""
        try:
            logger.info("Downloading video", url=url)
            
            # Import download function from existing module
            from download import download_video
            
            # Use existing download function
            video_path = download_video(url, output_dir)
            
            logger.info("Video downloaded successfully", path=str(video_path))
            return video_path
            
        except Exception as e:
            logger.error("Video download failed", url=url, error=str(e))
            raise
    
    def create_natural_segments(self, transcript: Dict[str, Any], 
                              min_duration: int = 30, 
                              max_duration: int = 60) -> List[Dict[str, Any]]:
        """Create natural segments - wrapper for existing function"""
        try:
            logger.info("Creating natural segments", 
                       segments_count=len(transcript.get("segments", [])))
            
            # Use existing pause-based segmentation
            potential_clips = create_pause_based_segments(
                transcript=transcript,
                min_duration=min_duration,
                max_duration=max_duration
            )
            
            logger.info("Natural segments created", count=len(potential_clips))
            return potential_clips
            
        except Exception as e:
            logger.error("Segment creation failed", error=str(e))
            raise
    
    def analyze_clips_with_gpt(self, transcript_segments: List[Dict], 
                              potential_clips: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze clips with GPT - wrapper for existing function"""
        if not self.client:
            raise ValueError("OpenAI API key not configured")
        
        try:
            logger.info("Starting GPT analysis", clips_count=len(potential_clips))
            
            # Use existing context-aware analysis
            analysis_results = create_multi_pass_analysis(
                all_segments=transcript_segments,
                potential_clips=potential_clips,
                client=self.client
            )
            
            evaluations = analysis_results["clip_evaluations"]
            
            logger.info("GPT analysis completed", 
                       evaluated_clips=len(evaluations),
                       themes=analysis_results["theme_analysis"]["main_themes"][:3])
            
            return evaluations
            
        except Exception as e:
            logger.error("GPT analysis failed", error=str(e))
            raise
    
    def select_top_clips(self, evaluations: List[Dict[str, Any]], 
                        num_clips: int = 3) -> List[Dict[str, Any]]:
        """Select top clips - wrapper for existing function"""
        try:
            logger.info("Selecting top clips", 
                       candidates=len(evaluations), 
                       target_count=num_clips)
            
            # Use existing context-aware filtering
            top_clips = filter_context_aware_clips(
                evaluations=evaluations, 
                top_n=num_clips
            )
            
            logger.info("Top clips selected", selected_count=len(top_clips))
            return top_clips
            
        except Exception as e:
            logger.error("Clip selection failed", error=str(e))
            raise
    
    def cut_video_clips(self, video_path: Path, clips: List[Dict[str, Any]], 
                       output_dir: Path, vertical: bool = True, 
                       subtitles: bool = True) -> List[Dict[str, Any]]:
        """Cut video clips - wrapper for existing function"""
        try:
            logger.info("Cutting video clips", 
                       clips_count=len(clips), 
                       vertical=vertical, 
                       subtitles=subtitles)
            
            clips_dir = output_dir / "clips"
            clips_dir.mkdir(exist_ok=True, parents=True)
            
            if vertical:
                vertical_dir = output_dir / "vertical"
                vertical_dir.mkdir(exist_ok=True, parents=True)
            
            clip_results = []
            
            for i, clip in enumerate(clips, 1):
                try:
                    # Cut the main clip using existing function
                    clip_path = cut_clip(
                        video_path=video_path,
                        output_dir=clips_dir,
                        start_time=clip["start"],
                        end_time=clip["end"],
                        clip_name=f"{i:02d}_{clip['title'][:30]}",
                        vertical=False  # We'll do vertical separately
                    )
                    
                    # Create vertical version if requested
                    vertical_path = None
                    if vertical:
                        vertical_path = reframe_to_vertical(clip_path, output_dir)
                    
                    # Create subtitles if requested
                    subtitle_path = None
                    if subtitles:
                        subtitle_path = create_subtitle_file(clip, clips_dir)
                    
                    clip_result = {
                        "index": i,
                        "title": clip["title"],
                        "start": clip["start"],
                        "end": clip["end"],
                        "duration": clip["duration"],
                        "score": clip["overall_score"],
                        "context_dependency": clip.get("context_dependency", "Unknown"),
                        "reasoning": clip["reasoning"],
                        "tags": clip["tags"],
                        "files": {
                            "horizontal": str(clip_path),
                            "vertical": str(vertical_path) if vertical_path else None,
                            "subtitle": str(subtitle_path) if subtitle_path else None
                        }
                    }
                    clip_results.append(clip_result)
                    
                    logger.info("Clip processed successfully", 
                               index=i, 
                               title=clip["title"])
                    
                except Exception as e:
                    logger.error("Clip processing failed", 
                               index=i, 
                               title=clip["title"], 
                               error=str(e))
                    # Continue with other clips
                    clip_results.append({
                        "index": i,
                        "title": clip["title"],
                        "error": str(e)
                    })
            
            logger.info("Video cutting completed", 
                       successful_clips=len([c for c in clip_results if "error" not in c]))
            
            return clip_results
            
        except Exception as e:
            logger.error("Video cutting failed", error=str(e))
            raise
    
    def process_video_complete(self, video_url: str, transcript_json: Dict[str, Any],
                             processing_options: Dict[str, Any], 
                             video_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Complete video processing pipeline with Phase 2 intelligence
        Maintains backward compatibility while adding AI analysis
        """
        
        # Extract processing options
        language = processing_options.get("language", "he")
        num_clips = processing_options.get("num_clips", 3)
        min_duration = processing_options.get("min_duration", 30)
        max_duration = processing_options.get("max_duration", 60)
        vertical = processing_options.get("vertical", True)
        subtitles = processing_options.get("subtitles", True)
        
        logger.info("Starting complete video processing", 
                   url=video_url, 
                   language=language, 
                   num_clips=num_clips,
                   phase2_enabled=self.enable_phase2)
        
        try:
            # Create temporary working directory
            with tempfile.TemporaryDirectory() as temp_dir:
                work_dir = Path(temp_dir)
                downloads_dir = work_dir / "downloads"
                intelligence_dir = work_dir / "intelligence"
                downloads_dir.mkdir(exist_ok=True)
                intelligence_dir.mkdir(exist_ok=True)
                
                # Step 1: Download video
                logger.info("Step 1: Downloading video")
                video_path = self.download_video_from_url(video_url, downloads_dir)
                
                # Step 2: Phase 2 Intelligence Analysis (if enabled)
                intelligence_results = None
                if self.enable_phase2:
                    logger.info("Step 2: Running Phase 2 intelligence analysis")
                    try:
                        coordinator = self._get_intelligence_coordinator()
                        if coordinator:
                            intelligence_results = coordinator.process_intelligence_parallel(
                                video_path=video_path,
                                transcript=transcript_json,
                                output_dir=intelligence_dir
                            )
                            
                            # Save to database if video_id provided
                            if video_id:
                                coordinator.save_to_database(video_id, intelligence_results)
                                
                            logger.info("Phase 2 intelligence analysis completed",
                                       overall_quality=round(intelligence_results.quality_metrics.get("overall_score", 0), 2),
                                       success_criteria=sum(intelligence_results.success_metrics.values()))
                    except Exception as e:
                        logger.warning("Phase 2 intelligence analysis failed, continuing with Phase 1", error=str(e))
                
                # Step 3: Create natural segments (Phase 1)
                logger.info("Step 3: Creating natural segments")
                potential_clips = self.create_natural_segments(
                    transcript=transcript_json,
                    min_duration=min_duration,
                    max_duration=max_duration
                )
                
                # Step 4: Analyze with GPT (Phase 1)
                logger.info("Step 4: Analyzing clips with GPT")
                evaluations = self.analyze_clips_with_gpt(
                    transcript_segments=transcript_json["segments"],
                    potential_clips=potential_clips
                )
                
                # Step 5: Select top clips (Phase 1)
                logger.info("Step 5: Selecting top clips")
                top_clips = self.select_top_clips(evaluations, num_clips)
                
                # Step 6: Cut video clips (Phase 1)
                logger.info("Step 6: Cutting video clips")
                clip_results = self.cut_video_clips(
                    video_path=video_path,
                    clips=top_clips,
                    output_dir=work_dir,
                    vertical=vertical,
                    subtitles=subtitles
                )
                
                # Step 7: Move files to permanent storage
                logger.info("Step 7: Moving files to permanent storage")
                # TODO: Implement file movement to STORAGE_PATH
                
                # Prepare result with Phase 2 data if available
                result = {
                    "success": True,
                    "clips_generated": len(clip_results),
                    "clips": clip_results,
                    "processing_info": {
                        "language": language,
                        "vertical_created": vertical,
                        "subtitles_created": subtitles,
                        "video_url": video_url,
                        "phase2_enabled": self.enable_phase2
                    }
                }
                
                # Add Phase 2 intelligence data if available
                if intelligence_results:
                    result["intelligence_analysis"] = {
                        "quality_metrics": intelligence_results.quality_metrics,
                        "success_criteria": intelligence_results.success_metrics,
                        "processing_times": intelligence_results.processing_times,
                        "audio_analysis": {
                            "filler_words_detected": len(intelligence_results.audio_analysis.filler_words),
                            "speech_rate_wpm": intelligence_results.audio_analysis.speech_rate,
                            "language_segments": len(intelligence_results.audio_analysis.language_segments),
                            "quality_score": intelligence_results.quality_metrics.get("audio_quality", 0)
                        },
                        "visual_analysis": {
                            "face_tracks_found": len(intelligence_results.visual_analysis.face_tracks),
                            "scene_boundaries": len(intelligence_results.visual_analysis.scene_boundaries),
                            "reframing_method": intelligence_results.visual_analysis.reframing_data.get("method", "unknown"),
                            "quality_score": intelligence_results.quality_metrics.get("visual_quality", 0)
                        },
                        "proxy_files": {
                            "proxy_videos": len(intelligence_results.proxy_manifest.proxy_videos),
                            "thumbnails": len(intelligence_results.proxy_manifest.thumbnails),
                            "webgl_ready": bool(intelligence_results.proxy_manifest.webgl_metadata)
                        }
                    }
                    
                    # Add recommendations based on intelligence analysis
                    result["recommendations"] = self._generate_recommendations(intelligence_results)
                
                logger.info("Video processing completed successfully", 
                           clips_generated=len(clip_results),
                           phase2_analysis=intelligence_results is not None)
                
                return result
                
        except Exception as e:
            logger.error("Video processing failed", error=str(e))
            raise
    
    def _generate_recommendations(self, intelligence_results: IntelligenceResults) -> Dict[str, Any]:
        """Generate processing recommendations based on intelligence analysis"""
        recommendations = {
            "quality_improvements": [],
            "cutting_suggestions": [],
            "technical_notes": []
        }
        
        # Audio recommendations
        if intelligence_results.audio_analysis:
            filler_count = len(intelligence_results.audio_analysis.filler_words)
            speech_rate = intelligence_results.audio_analysis.speech_rate
            snr = intelligence_results.audio_analysis.quality_metrics.get("snr_estimate_db", 0)
            
            if filler_count > 10:
                recommendations["quality_improvements"].append(
                    f"High filler word count ({filler_count}). Consider removing during editing."
                )
            
            if speech_rate < 120 or speech_rate > 180:
                recommendations["quality_improvements"].append(
                    f"Speech rate ({speech_rate:.1f} WPM) may affect engagement. Optimal range: 120-180 WPM."
                )
            
            if snr < 15:
                recommendations["technical_notes"].append(
                    f"Audio quality could be improved (SNR: {snr:.1f}dB). Consider audio processing."
                )
        
        # Visual recommendations
        if intelligence_results.visual_analysis:
            face_tracks = len(intelligence_results.visual_analysis.face_tracks)
            face_stability = intelligence_results.visual_analysis.quality_metrics.get("face_stability", 0)
            
            if face_tracks == 0:
                recommendations["cutting_suggestions"].append(
                    "No face tracking detected. Consider center-crop for vertical format."
                )
            elif face_stability < 0.8:
                recommendations["cutting_suggestions"].append(
                    "Face tracking unstable. May need manual reframing adjustments."
                )
            
            scene_count = len(intelligence_results.visual_analysis.scene_boundaries)
            if scene_count > 10:
                recommendations["cutting_suggestions"].append(
                    f"Many scene changes detected ({scene_count}). Consider shorter clips."
                )
        
        # Overall quality recommendations
        overall_score = intelligence_results.quality_metrics.get("overall_score", 0)
        if overall_score < 6:
            recommendations["quality_improvements"].append(
                "Overall quality score is low. Review audio and visual quality before publishing."
            )
        elif overall_score > 8:
            recommendations["quality_improvements"].append(
                "High quality content detected. Consider highlighting best segments."
            )
        
        # Success criteria warnings
        if not intelligence_results.success_metrics.get("filler_detection_90_percent"):
            recommendations["technical_notes"].append(
                "Filler word detection confidence below target. Manual review recommended."
            )
        
        if not intelligence_results.success_metrics.get("face_tracking_95_percent"):
            recommendations["technical_notes"].append(
                "Face tracking stability below target. May affect automatic reframing."
            )
        
        return recommendations