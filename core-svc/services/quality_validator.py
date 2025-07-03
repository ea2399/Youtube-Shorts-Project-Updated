"""
Quality Validator - Phase 3
Real-time quality validation framework for cut smoothness and EDL validation
"""

import numpy as np
import cv2
import librosa
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import structlog
import time
import math

from .intelligence_coordinator import IntelligenceResults
from ..models.database import get_db, EditDecisionList, ClipInstance

logger = structlog.get_logger()


@dataclass
class CutQualityMetrics:
    """Quality metrics for a specific cut or transition"""
    start_time: float
    end_time: float
    duration: float
    
    # Core quality scores (0-10 scale)
    cut_smoothness: float           # Audio RMS delta measurement
    visual_continuity: float        # SSIM-based transition quality
    semantic_coherence: float       # Content completeness
    engagement_score: float         # Retention potential
    overall_score: float           # Weighted combination
    
    # Detailed metrics
    rms_delta_db: float            # Audio level change at cut points
    ssim_transition_score: float   # Visual similarity across cut
    face_tracking_quality: float   # Face stability through cut
    motion_consistency: float      # Motion vector alignment
    
    # Thresholds validation
    meets_smoothness_threshold: bool    # <-15dB RMS delta
    meets_visual_threshold: bool        # >0.4 SSIM
    meets_duration_threshold: bool      # 30-60s duration
    
    # Context factors
    silence_padding_start: float    # Silence before cut (seconds)
    silence_padding_end: float      # Silence after cut (seconds)
    scene_boundary_alignment: bool  # Aligns with scene change
    
    # Reasoning and alternatives
    validation_reasoning: str
    improvement_suggestions: List[str]
    quality_warnings: List[str]


@dataclass
class EDLQualityReport:
    """Complete quality assessment for an EDL"""
    edl_id: str
    overall_quality_score: float
    
    # Individual clip metrics
    clip_metrics: List[CutQualityMetrics]
    
    # Aggregate metrics
    avg_cut_smoothness: float
    avg_visual_continuity: float
    avg_semantic_coherence: float
    avg_engagement_score: float
    
    # Success criteria validation
    cuts_meeting_smoothness: int    # Target: 95%
    cuts_meeting_visual: int        # Target: 90%
    cuts_meeting_duration: int      # Target: 100%
    
    # Quality distribution
    high_quality_clips: int         # Score >= 8.0
    medium_quality_clips: int       # Score 6.0-7.9
    low_quality_clips: int          # Score < 6.0
    
    # Improvement recommendations
    recommended_adjustments: List[Dict[str, Any]]
    quality_bottlenecks: List[str]
    
    # Processing metadata
    validation_time_seconds: float
    meets_production_criteria: bool


class QualityValidator:
    """
    Quality validation framework for EDL and cut assessment
    Implements real-time quality metrics with production-ready thresholds
    """
    
    def __init__(self):
        """Initialize quality validator with thresholds"""
        # Quality thresholds (from Phase 3 success criteria)
        self.thresholds = {
            # Phase 3 targets
            "cut_smoothness_db": -15.0,      # RMS delta threshold
            "visual_continuity_ssim": 0.4,    # SSIM threshold
            "overall_quality_min": 8.0,       # Target quality score
            "smoothness_percentage": 95.0,     # 95% of cuts meet smoothness
            
            # Duration constraints
            "min_clip_duration": 30.0,        # Minimum clip length
            "max_clip_duration": 60.0,        # Maximum clip length
            
            # Context requirements
            "min_silence_padding": 0.1,       # Minimum silence around cuts
            "face_tracking_min": 0.7,         # Minimum face tracking quality
            
            # Engagement proxies
            "motion_consistency_min": 0.6,    # Motion vector alignment
            "semantic_coherence_min": 0.7     # Content completeness
        }
        
        # Scoring weights (aligned with EDL Generator)
        self.weights = {
            "cut_smoothness": 0.4,     # Audio quality
            "visual_continuity": 0.3,  # Visual stability
            "semantic_coherence": 0.2, # Content coherence
            "engagement_score": 0.1    # Engagement potential
        }
        
        logger.info("QualityValidator initialized", thresholds=self.thresholds)
    
    def validate_edl(self, edl_id: str, video_path: Path, 
                    intelligence_results: IntelligenceResults) -> EDLQualityReport:
        """
        Complete EDL quality validation
        Returns comprehensive quality assessment with recommendations
        """
        start_time = time.time()
        
        # Load EDL from database
        with next(get_db()) as db:
            edl = db.query(EditDecisionList).filter(EditDecisionList.id == edl_id).first()
            if not edl:
                raise ValueError(f"EDL not found: {edl_id}")
            
            clip_instances = db.query(ClipInstance).filter(
                ClipInstance.edl_id == edl_id
            ).order_by(ClipInstance.sequence).all()
        
        logger.info("Validating EDL quality", 
                   edl_id=edl_id, 
                   clip_count=len(clip_instances),
                   video_path=str(video_path))
        
        # Validate each clip
        clip_metrics = []
        for clip in clip_instances:
            metrics = self._validate_clip(clip, video_path, intelligence_results)
            clip_metrics.append(metrics)
        
        # Calculate aggregate metrics
        aggregate_metrics = self._calculate_aggregate_metrics(clip_metrics)
        
        # Generate improvement recommendations
        recommendations = self._generate_recommendations(clip_metrics, aggregate_metrics)
        
        # Create quality report
        report = EDLQualityReport(
            edl_id=edl_id,
            overall_quality_score=aggregate_metrics["overall_score"],
            clip_metrics=clip_metrics,
            avg_cut_smoothness=aggregate_metrics["avg_cut_smoothness"],
            avg_visual_continuity=aggregate_metrics["avg_visual_continuity"],
            avg_semantic_coherence=aggregate_metrics["avg_semantic_coherence"],
            avg_engagement_score=aggregate_metrics["avg_engagement_score"],
            cuts_meeting_smoothness=aggregate_metrics["cuts_meeting_smoothness"],
            cuts_meeting_visual=aggregate_metrics["cuts_meeting_visual"],
            cuts_meeting_duration=aggregate_metrics["cuts_meeting_duration"],
            high_quality_clips=aggregate_metrics["high_quality_clips"],
            medium_quality_clips=aggregate_metrics["medium_quality_clips"],
            low_quality_clips=aggregate_metrics["low_quality_clips"],
            recommended_adjustments=recommendations["adjustments"],
            quality_bottlenecks=recommendations["bottlenecks"],
            validation_time_seconds=time.time() - start_time,
            meets_production_criteria=aggregate_metrics["meets_production_criteria"]
        )
        
        logger.info("EDL quality validation completed",
                   overall_score=round(report.overall_quality_score, 2),
                   smoothness_rate=round(report.cuts_meeting_smoothness / len(clip_metrics) * 100, 1),
                   meets_criteria=report.meets_production_criteria)
        
        return report
    
    def _validate_clip(self, clip: ClipInstance, video_path: Path, 
                      intelligence_results: IntelligenceResults) -> CutQualityMetrics:
        """Validate individual clip quality with detailed metrics"""
        
        # Calculate cut smoothness (audio RMS delta)
        cut_smoothness, rms_delta = self._calculate_cut_smoothness(
            video_path, clip.source_start_time, clip.source_end_time, intelligence_results
        )
        
        # Calculate visual continuity (SSIM-based)
        visual_continuity, ssim_score = self._calculate_visual_continuity(
            video_path, clip.source_start_time, clip.source_end_time, intelligence_results
        )
        
        # Calculate semantic coherence
        semantic_coherence = self._calculate_semantic_coherence(
            clip, intelligence_results
        )
        
        # Calculate engagement score
        engagement_score = self._calculate_engagement_score(
            clip, intelligence_results
        )
        
        # Calculate face tracking quality for this clip
        face_quality = self._calculate_face_tracking_quality(
            clip.source_start_time, clip.source_end_time, intelligence_results
        )
        
        # Calculate motion consistency
        motion_consistency = self._calculate_motion_consistency(
            video_path, clip.source_start_time, clip.source_end_time
        )
        
        # Calculate overall score using weights
        overall_score = (
            cut_smoothness * self.weights["cut_smoothness"] +
            visual_continuity * self.weights["visual_continuity"] +
            semantic_coherence * self.weights["semantic_coherence"] +
            engagement_score * self.weights["engagement_score"]
        )
        
        # Threshold validation
        meets_smoothness = rms_delta >= self.thresholds["cut_smoothness_db"]
        meets_visual = ssim_score >= self.thresholds["visual_continuity_ssim"]
        meets_duration = (
            self.thresholds["min_clip_duration"] <= clip.source_duration <= 
            self.thresholds["max_clip_duration"]
        )
        
        # Calculate silence padding
        silence_start, silence_end = self._calculate_silence_padding(
            clip.source_start_time, clip.source_end_time, intelligence_results
        )
        
        # Check scene boundary alignment
        scene_alignment = self._check_scene_boundary_alignment(
            clip.source_start_time, clip.source_end_time, intelligence_results
        )
        
        # Generate reasoning and suggestions
        reasoning, suggestions, warnings = self._generate_clip_feedback(
            clip, cut_smoothness, visual_continuity, semantic_coherence, 
            engagement_score, meets_smoothness, meets_visual, meets_duration
        )
        
        return CutQualityMetrics(
            start_time=clip.source_start_time,
            end_time=clip.source_end_time,
            duration=clip.source_duration,
            cut_smoothness=cut_smoothness,
            visual_continuity=visual_continuity,
            semantic_coherence=semantic_coherence,
            engagement_score=engagement_score,
            overall_score=overall_score,
            rms_delta_db=rms_delta,
            ssim_transition_score=ssim_score,
            face_tracking_quality=face_quality,
            motion_consistency=motion_consistency,
            meets_smoothness_threshold=meets_smoothness,
            meets_visual_threshold=meets_visual,
            meets_duration_threshold=meets_duration,
            silence_padding_start=silence_start,
            silence_padding_end=silence_end,
            scene_boundary_alignment=scene_alignment,
            validation_reasoning=reasoning,
            improvement_suggestions=suggestions,
            quality_warnings=warnings
        )
    
    def _calculate_cut_smoothness(self, video_path: Path, start_time: float, 
                                 end_time: float, intelligence_results: IntelligenceResults) -> Tuple[float, float]:
        """Calculate audio cut smoothness using RMS delta measurement"""
        try:
            # Load audio for analysis
            audio, sr = librosa.load(str(video_path), sr=16000, 
                                   offset=max(0, start_time - 0.1), 
                                   duration=min(end_time - start_time + 0.2, 2.0))
            
            # Calculate RMS in 50ms windows around cut points
            window_size = int(0.05 * sr)  # 50ms windows
            
            # RMS at start (pre-cut)
            start_idx = int(0.1 * sr)  # Skip to actual start
            if start_idx + window_size < len(audio):
                start_rms = np.sqrt(np.mean(audio[start_idx:start_idx + window_size] ** 2))
            else:
                start_rms = 0.0
            
            # RMS at end (pre-cut)
            end_offset = int((end_time - start_time) * sr)
            if end_offset - window_size >= 0 and end_offset < len(audio):
                end_rms = np.sqrt(np.mean(audio[end_offset - window_size:end_offset] ** 2))
            else:
                end_rms = 0.0
            
            # Calculate RMS delta in dB
            if start_rms > 0 and end_rms > 0:
                rms_delta_db = 20 * np.log10(end_rms / start_rms)
            else:
                rms_delta_db = -50.0  # Very smooth (silence)
            
            # Convert to 0-10 score (target: delta < -15dB is perfect)
            if abs(rms_delta_db) <= 15.0:
                smoothness_score = 10.0
            elif abs(rms_delta_db) <= 25.0:
                smoothness_score = 8.0 - (abs(rms_delta_db) - 15.0) * 0.2
            else:
                smoothness_score = max(0.0, 6.0 - (abs(rms_delta_db) - 25.0) * 0.1)
            
            return smoothness_score, rms_delta_db
            
        except Exception as e:
            logger.warning("Cut smoothness calculation failed", error=str(e))
            return 5.0, 0.0  # Neutral score on failure
    
    def _calculate_visual_continuity(self, video_path: Path, start_time: float, 
                                   end_time: float, intelligence_results: IntelligenceResults) -> Tuple[float, float]:
        """Calculate visual continuity using SSIM analysis"""
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                return 5.0, 0.0
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            # Get frames at cut boundaries
            start_frame_idx = int(start_time * fps)
            end_frame_idx = int(end_time * fps)
            
            # Sample frames around cut points
            frames_to_check = [
                start_frame_idx - 1,  # Before start cut
                start_frame_idx,      # At start cut
                end_frame_idx - 1,    # Before end cut
                end_frame_idx         # At end cut
            ]
            
            frames = []
            for frame_idx in frames_to_check:
                if frame_idx >= 0:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    ret, frame = cap.read()
                    if ret:
                        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        frames.append(gray_frame)
            
            cap.release()
            
            if len(frames) < 2:
                return 5.0, 0.0
            
            # Calculate SSIM between consecutive frames
            from skimage.metrics import structural_similarity as ssim
            
            ssim_scores = []
            for i in range(len(frames) - 1):
                score = ssim(frames[i], frames[i + 1])
                ssim_scores.append(score)
            
            avg_ssim = np.mean(ssim_scores)
            
            # Convert SSIM to 0-10 score (target: >0.4 is good)
            if avg_ssim >= 0.7:
                continuity_score = 10.0
            elif avg_ssim >= 0.4:
                continuity_score = 6.0 + (avg_ssim - 0.4) * 13.33  # Linear mapping
            else:
                continuity_score = max(0.0, avg_ssim * 15.0)  # Lower scores for poor continuity
            
            return continuity_score, avg_ssim
            
        except Exception as e:
            logger.warning("Visual continuity calculation failed", error=str(e))
            return 5.0, 0.0
    
    def _calculate_semantic_coherence(self, clip: ClipInstance, 
                                    intelligence_results: IntelligenceResults) -> float:
        """Calculate semantic coherence based on content completeness"""
        # Use the semantic score from the ClipInstance if available
        if clip.semantic_score is not None:
            return clip.semantic_score
        
        # Fallback: analyze based on duration and reasoning
        coherence_score = 7.0  # Default
        
        # Duration factor
        if 30 <= clip.source_duration <= 60:
            coherence_score += 1.0  # Good duration
        elif clip.source_duration < 20:
            coherence_score -= 2.0  # Too short for coherence
        elif clip.source_duration > 90:
            coherence_score -= 1.0  # Might be too long
        
        # Reasoning quality factor
        if clip.reasoning and len(clip.reasoning) > 50:
            coherence_score += 0.5  # Has detailed reasoning
        
        return min(10.0, max(0.0, coherence_score))
    
    def _calculate_engagement_score(self, clip: ClipInstance, 
                                  intelligence_results: IntelligenceResults) -> float:
        """Calculate engagement potential score"""
        # Use the engagement score from the ClipInstance if available
        if clip.engagement_score is not None:
            return clip.engagement_score
        
        # Fallback calculation based on available metrics
        engagement = 6.0  # Base score
        
        # Face tracking quality boosts engagement
        if clip.face_tracking_quality and clip.face_tracking_quality > 0.8:
            engagement += 1.5
        elif clip.face_tracking_quality and clip.face_tracking_quality > 0.6:
            engagement += 0.5
        
        # Audio quality factor
        if clip.audio_score and clip.audio_score > 8.0:
            engagement += 1.0
        
        # Visual quality factor
        if clip.visual_score and clip.visual_score > 8.0:
            engagement += 0.5
        
        return min(10.0, max(0.0, engagement))
    
    def _calculate_face_tracking_quality(self, start_time: float, end_time: float,
                                       intelligence_results: IntelligenceResults) -> float:
        """Calculate face tracking quality for clip duration"""
        if not intelligence_results.visual_analysis or not intelligence_results.visual_analysis.face_tracks:
            return 0.0
        
        # Find relevant face tracks for this time range
        relevant_quality_scores = []
        
        for track in intelligence_results.visual_analysis.face_tracks:
            for i, frame_idx in enumerate(track.frame_indices):
                # Convert frame to time (assuming 30fps default)
                frame_time = frame_idx / 30.0
                
                if start_time <= frame_time <= end_time:
                    if i < len(track.confidence_scores):
                        relevant_quality_scores.append(track.confidence_scores[i])
        
        if relevant_quality_scores:
            return np.mean(relevant_quality_scores) * 10.0  # Convert to 0-10 scale
        
        return 5.0  # Neutral if no data
    
    def _calculate_motion_consistency(self, video_path: Path, start_time: float, end_time: float) -> float:
        """Calculate motion consistency for clip"""
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                return 5.0
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            start_frame = int(start_time * fps)
            end_frame = int(end_time * fps)
            
            # Sample frames for motion analysis
            sample_frames = []
            for frame_idx in range(start_frame, end_frame, max(1, (end_frame - start_frame) // 10)):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if ret:
                    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    sample_frames.append(gray_frame)
            
            cap.release()
            
            if len(sample_frames) < 2:
                return 5.0
            
            # Calculate motion vectors between consecutive frames
            motion_magnitudes = []
            for i in range(len(sample_frames) - 1):
                diff = cv2.absdiff(sample_frames[i], sample_frames[i + 1])
                motion_magnitude = np.mean(diff) / 255.0
                motion_magnitudes.append(motion_magnitude)
            
            # Consistency is inverse of motion variance
            if motion_magnitudes:
                motion_std = np.std(motion_magnitudes)
                consistency_score = max(0.0, 10.0 - motion_std * 50.0)
                return min(10.0, consistency_score)
            
            return 5.0
            
        except Exception as e:
            logger.warning("Motion consistency calculation failed", error=str(e))
            return 5.0
    
    def _calculate_silence_padding(self, start_time: float, end_time: float,
                                 intelligence_results: IntelligenceResults) -> Tuple[float, float]:
        """Calculate silence padding around cuts"""
        silence_start = 0.0
        silence_end = 0.0
        
        if (intelligence_results.audio_analysis and 
            intelligence_results.audio_analysis.silence_segments):
            
            # Find silence segments around cut points
            for segment in intelligence_results.audio_analysis.silence_segments:
                segment_start, segment_end = segment
                
                # Silence before cut start
                if segment_end <= start_time and start_time - segment_end < 1.0:
                    silence_start = max(silence_start, segment_end - segment_start)
                
                # Silence after cut end
                if segment_start >= end_time and segment_start - end_time < 1.0:
                    silence_end = max(silence_end, segment_end - segment_start)
        
        return silence_start, silence_end
    
    def _check_scene_boundary_alignment(self, start_time: float, end_time: float,
                                      intelligence_results: IntelligenceResults) -> bool:
        """Check if cuts align with scene boundaries"""
        if (not intelligence_results.visual_analysis or 
            not intelligence_results.visual_analysis.scene_boundaries):
            return False
        
        tolerance = 2.0  # 2 second tolerance
        
        for boundary in intelligence_results.visual_analysis.scene_boundaries:
            # Check if cut start aligns with scene boundary
            if (abs(boundary.start_time - start_time) <= tolerance or
                abs(boundary.end_time - start_time) <= tolerance):
                return True
            
            # Check if cut end aligns with scene boundary
            if (abs(boundary.start_time - end_time) <= tolerance or
                abs(boundary.end_time - end_time) <= tolerance):
                return True
        
        return False
    
    def _generate_clip_feedback(self, clip: ClipInstance, cut_smoothness: float,
                              visual_continuity: float, semantic_coherence: float,
                              engagement_score: float, meets_smoothness: bool,
                              meets_visual: bool, meets_duration: bool) -> Tuple[str, List[str], List[str]]:
        """Generate reasoning, suggestions, and warnings for clip"""
        
        # Generate reasoning
        reasoning_parts = []
        reasoning_parts.append(f"Cut smoothness: {cut_smoothness:.1f}/10")
        reasoning_parts.append(f"Visual continuity: {visual_continuity:.1f}/10")
        reasoning_parts.append(f"Semantic coherence: {semantic_coherence:.1f}/10")
        reasoning_parts.append(f"Engagement potential: {engagement_score:.1f}/10")
        
        reasoning = "; ".join(reasoning_parts)
        
        # Generate improvement suggestions
        suggestions = []
        if cut_smoothness < 7.0:
            suggestions.append("Consider adjusting cut points to natural speech pauses")
        if visual_continuity < 7.0:
            suggestions.append("Review visual transitions - may need scene boundary alignment")
        if semantic_coherence < 7.0:
            suggestions.append("Ensure clip contains complete thoughts or sentences")
        if engagement_score < 7.0:
            suggestions.append("Consider clips with better face tracking or visual appeal")
        
        # Generate quality warnings
        warnings = []
        if not meets_smoothness:
            warnings.append("Audio cut smoothness below threshold (-15dB)")
        if not meets_visual:
            warnings.append("Visual continuity below threshold (0.4 SSIM)")
        if not meets_duration:
            warnings.append("Duration outside optimal range (30-60 seconds)")
        
        return reasoning, suggestions, warnings
    
    def _calculate_aggregate_metrics(self, clip_metrics: List[CutQualityMetrics]) -> Dict[str, Any]:
        """Calculate aggregate metrics across all clips"""
        if not clip_metrics:
            return {}
        
        # Average scores
        avg_cut_smoothness = np.mean([m.cut_smoothness for m in clip_metrics])
        avg_visual_continuity = np.mean([m.visual_continuity for m in clip_metrics])
        avg_semantic_coherence = np.mean([m.semantic_coherence for m in clip_metrics])
        avg_engagement_score = np.mean([m.engagement_score for m in clip_metrics])
        
        # Overall score (weighted average)
        overall_score = (
            avg_cut_smoothness * self.weights["cut_smoothness"] +
            avg_visual_continuity * self.weights["visual_continuity"] +
            avg_semantic_coherence * self.weights["semantic_coherence"] +
            avg_engagement_score * self.weights["engagement_score"]
        )
        
        # Threshold compliance
        cuts_meeting_smoothness = sum(1 for m in clip_metrics if m.meets_smoothness_threshold)
        cuts_meeting_visual = sum(1 for m in clip_metrics if m.meets_visual_threshold)
        cuts_meeting_duration = sum(1 for m in clip_metrics if m.meets_duration_threshold)
        
        # Quality distribution
        high_quality_clips = sum(1 for m in clip_metrics if m.overall_score >= 8.0)
        medium_quality_clips = sum(1 for m in clip_metrics if 6.0 <= m.overall_score < 8.0)
        low_quality_clips = sum(1 for m in clip_metrics if m.overall_score < 6.0)
        
        # Production criteria (Phase 3 success criteria)
        smoothness_rate = cuts_meeting_smoothness / len(clip_metrics) * 100
        meets_production_criteria = (
            overall_score >= self.thresholds["overall_quality_min"] and
            smoothness_rate >= self.thresholds["smoothness_percentage"]
        )
        
        return {
            "overall_score": overall_score,
            "avg_cut_smoothness": avg_cut_smoothness,
            "avg_visual_continuity": avg_visual_continuity,
            "avg_semantic_coherence": avg_semantic_coherence,
            "avg_engagement_score": avg_engagement_score,
            "cuts_meeting_smoothness": cuts_meeting_smoothness,
            "cuts_meeting_visual": cuts_meeting_visual,
            "cuts_meeting_duration": cuts_meeting_duration,
            "high_quality_clips": high_quality_clips,
            "medium_quality_clips": medium_quality_clips,
            "low_quality_clips": low_quality_clips,
            "meets_production_criteria": meets_production_criteria
        }
    
    def _generate_recommendations(self, clip_metrics: List[CutQualityMetrics], 
                                aggregate_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate improvement recommendations and identify bottlenecks"""
        
        adjustments = []
        bottlenecks = []
        
        # Identify low-performing clips
        for i, metrics in enumerate(clip_metrics):
            if metrics.overall_score < 6.0:
                adjustments.append({
                    "clip_index": i,
                    "current_score": metrics.overall_score,
                    "primary_issue": self._identify_primary_issue(metrics),
                    "recommended_action": self._recommend_action(metrics),
                    "time_range": f"{metrics.start_time:.1f}s - {metrics.end_time:.1f}s"
                })
        
        # Identify system-wide bottlenecks
        if aggregate_metrics["avg_cut_smoothness"] < 7.0:
            bottlenecks.append("Audio cut smoothness - review silence detection accuracy")
        
        if aggregate_metrics["avg_visual_continuity"] < 7.0:
            bottlenecks.append("Visual continuity - improve scene boundary alignment")
        
        if aggregate_metrics["avg_semantic_coherence"] < 7.0:
            bottlenecks.append("Semantic coherence - extend clip durations for complete thoughts")
        
        if aggregate_metrics["cuts_meeting_smoothness"] / len(clip_metrics) < 0.9:
            bottlenecks.append("Cut smoothness threshold compliance - review audio processing")
        
        return {
            "adjustments": adjustments,
            "bottlenecks": bottlenecks
        }
    
    def _identify_primary_issue(self, metrics: CutQualityMetrics) -> str:
        """Identify the primary quality issue for a clip"""
        scores = {
            "cut_smoothness": metrics.cut_smoothness,
            "visual_continuity": metrics.visual_continuity,
            "semantic_coherence": metrics.semantic_coherence,
            "engagement_score": metrics.engagement_score
        }
        
        # Find the lowest scoring aspect
        min_aspect = min(scores.keys(), key=lambda k: scores[k])
        return min_aspect
    
    def _recommend_action(self, metrics: CutQualityMetrics) -> str:
        """Recommend specific action for improving clip quality"""
        primary_issue = self._identify_primary_issue(metrics)
        
        actions = {
            "cut_smoothness": "Adjust cut points to natural pauses or breathing points",
            "visual_continuity": "Align cuts with scene boundaries or stable visual moments",
            "semantic_coherence": "Extend clip to include complete sentences or thoughts",
            "engagement_score": "Select clips with better face tracking or visual appeal"
        }
        
        return actions.get(primary_issue, "Review and manually adjust clip boundaries")


def validate_edl_quality(edl_id: str, video_path: Path, 
                        intelligence_results: IntelligenceResults) -> EDLQualityReport:
    """
    Convenience function for EDL quality validation
    """
    validator = QualityValidator()
    return validator.validate_edl(edl_id, video_path, intelligence_results)