"""
EDL Generator - Phase 3
Multi-modal fusion engine for intelligent cutting decisions
"""

import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import structlog
import time
import uuid
import math

from .intelligence_coordinator import IntelligenceResults, IntelligenceCoordinator
from ..models.database import (
    get_db, EditDecisionList, ClipInstance, CutCandidate,
    AudioAnalysis as AudioAnalysisDB, VisualAnalysis as VisualAnalysisDB
)

logger = structlog.get_logger()


@dataclass
class CutCandidateScore:
    """Detailed scoring breakdown for a cut candidate"""
    start_time: float
    end_time: float
    duration: float
    
    # Multi-modal scores (0-10 scale)
    audio_score: float
    visual_score: float
    semantic_score: float
    engagement_score: float
    overall_score: float
    
    # Detailed components
    filler_word_penalty: float
    face_stability_score: float
    motion_intensity: float
    speech_clarity: float
    scene_boundary_alignment: float
    
    # Context factors
    preceding_silence: float
    following_silence: float
    contains_scene_boundary: bool
    filler_word_count: int
    
    # Reasoning
    reasoning: str
    exclusion_reason: Optional[str] = None


@dataclass
class EDLOutput:
    """Complete EDL generation output"""
    edl_id: str
    video_id: str
    version: int
    
    # EDL metadata
    target_duration: float
    actual_duration: float
    clip_count: int
    
    # Quality metrics
    overall_score: float
    cut_smoothness: float
    visual_continuity: float
    semantic_coherence: float
    engagement_score: float
    
    # Clips and alternatives
    clips: List[Dict[str, Any]]
    alternative_edls: List[Dict[str, Any]]
    
    # Generation metadata
    generation_strategy: str
    reasoning: str
    processing_time: float


class CuttingEngine:
    """
    Multi-modal fusion scoring engine for cut candidates
    Implements the 40/30/20/10 weighting strategy from plan
    """
    
    def __init__(self):
        """Initialize cutting engine with scoring parameters"""
        # Fusion weights (must sum to 1.0)
        self.weights = {
            "audio": 0.4,      # Audio quality and clarity
            "visual": 0.3,     # Visual stability and quality
            "semantic": 0.2,   # Content coherence
            "engagement": 0.1  # Engagement potential
        }
        
        # Scoring thresholds
        self.min_duration = 5.0   # Minimum clip duration
        self.max_duration = 60.0  # Maximum clip duration
        self.min_silence_gap = 0.5  # Minimum silence between cuts
        
        logger.info("CuttingEngine initialized", weights=self.weights)
    
    def score_candidate(self, candidate: Dict[str, Any], 
                       intelligence_results: IntelligenceResults) -> CutCandidateScore:
        """
        Score a cut candidate using multi-modal fusion
        Returns detailed scoring breakdown
        """
        start_time = candidate["start_time"]
        end_time = candidate["end_time"]
        duration = end_time - start_time
        
        # Calculate component scores
        audio_score = self._calculate_audio_score(start_time, end_time, intelligence_results)
        visual_score = self._calculate_visual_score(start_time, end_time, intelligence_results)
        semantic_score = self._calculate_semantic_score(start_time, end_time, intelligence_results)
        engagement_score = self._calculate_engagement_score(start_time, end_time, intelligence_results)
        
        # Apply fusion weights
        overall_score = (
            audio_score * self.weights["audio"] +
            visual_score * self.weights["visual"] +
            semantic_score * self.weights["semantic"] +
            engagement_score * self.weights["engagement"]
        )
        
        # Calculate detailed components
        filler_penalty = self._calculate_filler_penalty(start_time, end_time, intelligence_results)
        face_stability = self._calculate_face_stability(start_time, end_time, intelligence_results)
        motion_intensity = self._calculate_motion_intensity(start_time, end_time, intelligence_results)
        speech_clarity = self._calculate_speech_clarity(start_time, end_time, intelligence_results)
        scene_alignment = self._calculate_scene_alignment(start_time, end_time, intelligence_results)
        
        # Context analysis
        preceding_silence = candidate.get("preceding_silence", 0.0)
        following_silence = candidate.get("following_silence", 0.0)
        contains_scene_boundary = self._contains_scene_boundary(start_time, end_time, intelligence_results)
        filler_count = self._count_filler_words(start_time, end_time, intelligence_results)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(audio_score, visual_score, semantic_score, 
                                           engagement_score, duration, filler_count)
        
        # Check exclusion criteria
        exclusion_reason = self._check_exclusion_criteria(duration, overall_score, filler_count)
        
        return CutCandidateScore(
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            audio_score=audio_score,
            visual_score=visual_score,
            semantic_score=semantic_score,
            engagement_score=engagement_score,
            overall_score=overall_score,
            filler_word_penalty=filler_penalty,
            face_stability_score=face_stability,
            motion_intensity=motion_intensity,
            speech_clarity=speech_clarity,
            scene_boundary_alignment=scene_alignment,
            preceding_silence=preceding_silence,
            following_silence=following_silence,
            contains_scene_boundary=contains_scene_boundary,
            filler_word_count=filler_count,
            reasoning=reasoning,
            exclusion_reason=exclusion_reason
        )
    
    def _calculate_audio_score(self, start_time: float, end_time: float, 
                              intelligence_results: IntelligenceResults) -> float:
        """Calculate audio quality score (0-10)"""
        if not intelligence_results.audio_analysis:
            return 5.0  # Default neutral score
        
        audio_analysis = intelligence_results.audio_analysis
        
        # Base score from quality metrics
        snr = audio_analysis.quality_metrics.get("snr_estimate_db", 0)
        speech_rate = audio_analysis.speech_rate
        rms_mean = audio_analysis.quality_metrics.get("rms_mean", 0)
        
        # SNR contribution (0-4 points)
        snr_score = min(snr / 20.0, 1.0) * 4.0
        
        # Speech rate optimization (0-3 points)
        ideal_speech_rate = 150  # WPM
        speech_rate_score = 1.0 - abs(speech_rate - ideal_speech_rate) / ideal_speech_rate
        speech_rate_score = max(0, min(1, speech_rate_score)) * 3.0
        
        # Audio level consistency (0-2 points)
        rms_score = min(rms_mean * 10, 1.0) * 2.0
        
        # Filler word penalty (0-1 points deduction)
        filler_penalty = self._calculate_filler_penalty(start_time, end_time, intelligence_results)
        
        audio_score = snr_score + speech_rate_score + rms_score - filler_penalty
        return max(0, min(10, audio_score))
    
    def _calculate_visual_score(self, start_time: float, end_time: float,
                               intelligence_results: IntelligenceResults) -> float:
        """Calculate visual quality score (0-10)"""
        if not intelligence_results.visual_analysis:
            return 5.0  # Default neutral score
        
        visual_analysis = intelligence_results.visual_analysis
        
        # Base score from quality metrics
        ssim_mean = visual_analysis.quality_metrics.get("ssim_mean", 0.5)
        face_quality = visual_analysis.quality_metrics.get("face_tracking_quality", 0.5)
        motion_intensity = visual_analysis.quality_metrics.get("motion_intensity_mean", 0.5)
        face_stability = visual_analysis.quality_metrics.get("face_stability", 0.5)
        
        # SSIM contribution (0-3 points)
        ssim_score = ssim_mean * 3.0
        
        # Face quality contribution (0-4 points)
        face_score = face_quality * 4.0
        
        # Motion stability (0-2 points) - prefer moderate motion
        ideal_motion = 0.3  # Some motion is good, too much is jarring
        motion_score = (1.0 - abs(motion_intensity - ideal_motion)) * 2.0
        
        # Face stability bonus (0-1 points)
        stability_bonus = face_stability * 1.0
        
        visual_score = ssim_score + face_score + motion_score + stability_bonus
        return max(0, min(10, visual_score))
    
    def _calculate_semantic_score(self, start_time: float, end_time: float,
                                 intelligence_results: IntelligenceResults) -> float:
        """Calculate semantic coherence score (0-10)"""
        # Simplified semantic scoring based on segment boundaries
        duration = end_time - start_time
        
        # Duration appropriateness (0-5 points)
        ideal_duration = 45.0  # Ideal 45-second clips
        duration_score = 1.0 - abs(duration - ideal_duration) / ideal_duration
        duration_score = max(0, min(1, duration_score)) * 5.0
        
        # Scene boundary alignment (0-3 points)
        scene_alignment = self._calculate_scene_alignment(start_time, end_time, intelligence_results)
        
        # Silence boundary alignment (0-2 points)
        silence_alignment = self._calculate_silence_alignment(start_time, end_time, intelligence_results)
        
        semantic_score = duration_score + scene_alignment + silence_alignment
        return max(0, min(10, semantic_score))
    
    def _calculate_engagement_score(self, start_time: float, end_time: float,
                                   intelligence_results: IntelligenceResults) -> float:
        """Calculate engagement potential score (0-10)"""
        # Simplified engagement scoring based on energy and variety
        
        # Speech clarity contribution (0-4 points)
        speech_clarity = self._calculate_speech_clarity(start_time, end_time, intelligence_results)
        
        # Face prominence (0-3 points)
        face_prominence = 0.0
        if intelligence_results.visual_analysis:
            face_quality = intelligence_results.visual_analysis.quality_metrics.get("face_tracking_quality", 0)
            face_prominence = face_quality * 3.0
        
        # Content variety (0-2 points) - prefer some motion/gestures
        motion_variety = 0.0
        if intelligence_results.visual_analysis:
            motion_intensity = intelligence_results.visual_analysis.quality_metrics.get("motion_intensity_mean", 0)
            motion_variety = min(motion_intensity * 2, 2.0)  # Cap at 2 points
        
        # Opening/hook potential (0-1 points)
        hook_bonus = 1.0 if start_time < 10.0 else 0.5  # Prefer early content
        
        engagement_score = speech_clarity + face_prominence + motion_variety + hook_bonus
        return max(0, min(10, engagement_score))
    
    def _calculate_filler_penalty(self, start_time: float, end_time: float,
                                 intelligence_results: IntelligenceResults) -> float:
        """Calculate filler word penalty (0-2 points deduction)"""
        if not intelligence_results.audio_analysis:
            return 0.0
        
        filler_count = self._count_filler_words(start_time, end_time, intelligence_results)
        duration = end_time - start_time
        
        # Penalty based on filler density
        filler_density = filler_count / (duration / 60.0)  # Fillers per minute
        penalty = min(filler_density * 0.5, 2.0)  # Cap at 2 points
        
        return penalty
    
    def _calculate_face_stability(self, start_time: float, end_time: float,
                                 intelligence_results: IntelligenceResults) -> float:
        """Calculate face tracking stability score (0-1)"""
        if not intelligence_results.visual_analysis:
            return 0.5
        
        return intelligence_results.visual_analysis.quality_metrics.get("face_stability", 0.5)
    
    def _calculate_motion_intensity(self, start_time: float, end_time: float,
                                   intelligence_results: IntelligenceResults) -> float:
        """Calculate motion intensity (0-1)"""
        if not intelligence_results.visual_analysis:
            return 0.3  # Default moderate motion
        
        return intelligence_results.visual_analysis.quality_metrics.get("motion_intensity_mean", 0.3)
    
    def _calculate_speech_clarity(self, start_time: float, end_time: float,
                                 intelligence_results: IntelligenceResults) -> float:
        """Calculate speech clarity score (0-4)"""
        if not intelligence_results.audio_analysis:
            return 2.0
        
        snr = intelligence_results.audio_analysis.quality_metrics.get("snr_estimate_db", 10)
        speech_rate = intelligence_results.audio_analysis.speech_rate
        
        # SNR contribution
        snr_score = min(snr / 20.0, 1.0) * 2.0
        
        # Speech rate contribution
        ideal_speech_rate = 150
        rate_score = 1.0 - abs(speech_rate - ideal_speech_rate) / ideal_speech_rate
        rate_score = max(0, min(1, rate_score)) * 2.0
        
        return snr_score + rate_score
    
    def _calculate_scene_alignment(self, start_time: float, end_time: float,
                                  intelligence_results: IntelligenceResults) -> float:
        """Calculate scene boundary alignment score (0-3)"""
        if not intelligence_results.visual_analysis:
            return 1.5  # Default moderate score
        
        scene_boundaries = intelligence_results.visual_analysis.scene_boundaries
        if not scene_boundaries:
            return 1.5
        
        # Check if segment aligns with scene boundaries
        alignment_score = 0.0
        
        for scene in scene_boundaries:
            # Bonus for starting near scene boundary
            if abs(start_time - scene.start_time) < 2.0:
                alignment_score += 1.5
            
            # Bonus for ending near scene boundary
            if abs(end_time - scene.end_time) < 2.0:
                alignment_score += 1.5
        
        return min(alignment_score, 3.0)
    
    def _calculate_silence_alignment(self, start_time: float, end_time: float,
                                    intelligence_results: IntelligenceResults) -> float:
        """Calculate silence boundary alignment score (0-2)"""
        if not intelligence_results.audio_analysis:
            return 1.0
        
        silence_segments = intelligence_results.audio_analysis.silence_segments
        if not silence_segments:
            return 1.0
        
        alignment_score = 0.0
        
        for silence_start, silence_end in silence_segments:
            # Bonus for starting after silence
            if abs(start_time - silence_end) < 1.0:
                alignment_score += 1.0
            
            # Bonus for ending before silence
            if abs(end_time - silence_start) < 1.0:
                alignment_score += 1.0
        
        return min(alignment_score, 2.0)
    
    def _contains_scene_boundary(self, start_time: float, end_time: float,
                                intelligence_results: IntelligenceResults) -> bool:
        """Check if segment contains a scene boundary"""
        if not intelligence_results.visual_analysis:
            return False
        
        scene_boundaries = intelligence_results.visual_analysis.scene_boundaries
        if not scene_boundaries:
            return False
        
        for scene in scene_boundaries:
            if start_time <= scene.start_time <= end_time:
                return True
        
        return False
    
    def _count_filler_words(self, start_time: float, end_time: float,
                           intelligence_results: IntelligenceResults) -> int:
        """Count filler words in segment"""
        if not intelligence_results.audio_analysis:
            return 0
        
        filler_words = intelligence_results.audio_analysis.filler_words
        if not filler_words:
            return 0
        
        count = 0
        for filler in filler_words:
            filler_start = filler.get("start", 0)
            if start_time <= filler_start <= end_time:
                count += 1
        
        return count
    
    def _generate_reasoning(self, audio_score: float, visual_score: float,
                           semantic_score: float, engagement_score: float,
                           duration: float, filler_count: int) -> str:
        """Generate human-readable reasoning for the score"""
        reasons = []
        
        # Audio reasoning
        if audio_score > 7.5:
            reasons.append("excellent audio clarity")
        elif audio_score < 5.0:
            reasons.append("poor audio quality")
        
        # Visual reasoning
        if visual_score > 7.5:
            reasons.append("stable face tracking")
        elif visual_score < 5.0:
            reasons.append("unstable visuals")
        
        # Semantic reasoning
        if semantic_score > 7.0:
            reasons.append("good content boundaries")
        
        # Engagement reasoning
        if engagement_score > 7.0:
            reasons.append("high engagement potential")
        
        # Duration reasoning
        if 30 <= duration <= 60:
            reasons.append("optimal duration")
        elif duration < 10:
            reasons.append("too short")
        elif duration > 90:
            reasons.append("too long")
        
        # Filler word reasoning
        if filler_count == 0:
            reasons.append("no filler words")
        elif filler_count > 3:
            reasons.append(f"many filler words ({filler_count})")
        
        if not reasons:
            return "moderate quality across all metrics"
        
        return ", ".join(reasons)
    
    def _check_exclusion_criteria(self, duration: float, overall_score: float,
                                 filler_count: int) -> Optional[str]:
        """Check if candidate should be excluded"""
        if duration < self.min_duration:
            return f"too short ({duration:.1f}s < {self.min_duration}s)"
        
        if duration > self.max_duration:
            return f"too long ({duration:.1f}s > {self.max_duration}s)"
        
        if overall_score < 3.0:
            return f"low quality score ({overall_score:.1f})"
        
        if filler_count > 5:
            return f"too many filler words ({filler_count})"
        
        return None


class EDLGenerator:
    """
    Main EDL generation service that orchestrates the cutting engine
    """
    
    def __init__(self):
        """Initialize EDL generator"""
        self.cutting_engine = CuttingEngine()
        
        logger.info("EDLGenerator initialized")
    
    def generate_edl(self, video_id: str, target_duration: float = 60.0,
                    intelligence_results: Optional[IntelligenceResults] = None) -> EDLOutput:
        """
        Generate an EDL for a video using multi-modal fusion
        
        Args:
            video_id: UUID of the video to process
            target_duration: Target duration for the final EDL in seconds
            intelligence_results: Pre-computed intelligence results (or fetch from DB)
        
        Returns:
            Complete EDL output with clips and metadata
        """
        start_time = time.time()
        
        logger.info("Starting EDL generation", 
                   video_id=video_id, 
                   target_duration=target_duration)
        
        try:
            # Step 1: Get or fetch intelligence results
            if intelligence_results is None:
                intelligence_results = self._fetch_intelligence_results(video_id)
            
            # Step 2: Generate cut candidates
            candidates = self._generate_candidates(intelligence_results)
            
            # Step 3: Score all candidates
            scored_candidates = self._score_candidates(candidates, intelligence_results)
            
            # Step 4: Select best clips for EDL
            selected_clips = self._select_clips_for_edl(scored_candidates, target_duration)
            
            # Step 5: Validate and optimize EDL
            optimized_clips = self._optimize_edl(selected_clips, intelligence_results)
            
            # Step 6: Calculate EDL quality metrics
            quality_metrics = self._calculate_edl_quality(optimized_clips)
            
            # Step 7: Generate alternatives
            alternatives = self._generate_alternative_edls(scored_candidates, target_duration)
            
            # Step 8: Create EDL output
            edl_output = self._create_edl_output(
                video_id, optimized_clips, quality_metrics, alternatives, start_time
            )
            
            # Step 9: Save to database
            self._save_edl_to_database(edl_output, scored_candidates)
            
            logger.info("EDL generation completed", 
                       edl_id=edl_output.edl_id,
                       clip_count=edl_output.clip_count,
                       overall_score=round(edl_output.overall_score, 2),
                       processing_time=round(edl_output.processing_time, 2))
            
            return edl_output
            
        except Exception as e:
            logger.error("EDL generation failed", video_id=video_id, error=str(e))
            raise
    
    def _fetch_intelligence_results(self, video_id: str) -> IntelligenceResults:
        """Fetch intelligence results from database or coordinator"""
        # For now, return empty results - this would integrate with IntelligenceCoordinator
        # In practice, this would fetch from database or trigger intelligence processing
        logger.warning("Using empty intelligence results - implement database fetch")
        
        from .audio_processor import AudioAnalysis
        from .visual_processor import VisualAnalysis
        from .proxy_generator import ProxyManifest
        
        return IntelligenceResults(
            audio_analysis=AudioAnalysis([], [], {}, [], 0.0, [], []),
            visual_analysis=VisualAnalysis([], [], [], {}, {}, {}),
            proxy_manifest=ProxyManifest([], [], {}, {}, {}),
            quality_metrics={},
            processing_times={},
            success_metrics={}
        )
    
    def _generate_candidates(self, intelligence_results: IntelligenceResults) -> List[Dict[str, Any]]:
        """Generate cut candidates based on silence segments"""
        candidates = []
        
        if intelligence_results.audio_analysis and intelligence_results.audio_analysis.silence_segments:
            silence_segments = intelligence_results.audio_analysis.silence_segments
            
            # Create candidates between silence segments
            for i in range(len(silence_segments) - 1):
                _, prev_silence_end = silence_segments[i]
                next_silence_start, _ = silence_segments[i + 1]
                
                # Create candidate segment
                candidate = {
                    "start_time": prev_silence_end,
                    "end_time": next_silence_start,
                    "duration": next_silence_start - prev_silence_end,
                    "preceding_silence": silence_segments[i][1] - silence_segments[i][0],
                    "following_silence": silence_segments[i + 1][1] - silence_segments[i + 1][0]
                }
                
                candidates.append(candidate)
        else:
            # Fallback: create fixed-duration candidates
            logger.warning("No silence segments found, using fixed intervals")
            for start in range(0, 300, 30):  # 30-second intervals up to 5 minutes
                candidates.append({
                    "start_time": start,
                    "end_time": start + 30,
                    "duration": 30,
                    "preceding_silence": 1.0,
                    "following_silence": 1.0
                })
        
        logger.info("Generated cut candidates", count=len(candidates))
        return candidates
    
    def _score_candidates(self, candidates: List[Dict[str, Any]], 
                         intelligence_results: IntelligenceResults) -> List[CutCandidateScore]:
        """Score all cut candidates using the cutting engine"""
        scored_candidates = []
        
        for candidate in candidates:
            try:
                score = self.cutting_engine.score_candidate(candidate, intelligence_results)
                scored_candidates.append(score)
            except Exception as e:
                logger.warning("Failed to score candidate", 
                             start_time=candidate["start_time"],
                             error=str(e))
        
        # Sort by overall score (descending)
        scored_candidates.sort(key=lambda x: x.overall_score, reverse=True)
        
        logger.info("Scored cut candidates", 
                   total=len(scored_candidates),
                   excluded=len([c for c in scored_candidates if c.exclusion_reason]))
        
        return scored_candidates
    
    def _select_clips_for_edl(self, scored_candidates: List[CutCandidateScore],
                             target_duration: float) -> List[CutCandidateScore]:
        """Select clips for EDL using greedy algorithm"""
        selected_clips = []
        current_timeline_duration = 0.0
        used_time_ranges = []  # Track used source time to avoid overlaps
        
        for candidate in scored_candidates:
            # Skip excluded candidates
            if candidate.exclusion_reason:
                continue
            
            # Check if candidate overlaps with already selected clips
            overlaps = any(
                self._time_ranges_overlap(
                    (candidate.start_time, candidate.end_time),
                    used_range
                ) for used_range in used_time_ranges
            )
            
            if overlaps:
                continue
            
            # Check if adding this clip would exceed target duration
            if current_timeline_duration + candidate.duration > target_duration:
                # Try to fit a shorter version
                remaining_duration = target_duration - current_timeline_duration
                if remaining_duration >= self.cutting_engine.min_duration:
                    # Create a shortened version
                    shortened_candidate = self._create_shortened_candidate(
                        candidate, remaining_duration
                    )
                    selected_clips.append(shortened_candidate)
                    current_timeline_duration = target_duration
                break
            
            # Add the clip
            selected_clips.append(candidate)
            current_timeline_duration += candidate.duration
            used_time_ranges.append((candidate.start_time, candidate.end_time))
            
            # Check if we've reached the target duration
            if current_timeline_duration >= target_duration * 0.95:  # Within 5% of target
                break
        
        logger.info("Selected clips for EDL", 
                   count=len(selected_clips),
                   total_duration=round(current_timeline_duration, 1),
                   target_duration=target_duration)
        
        return selected_clips
    
    def _time_ranges_overlap(self, range1: Tuple[float, float], 
                            range2: Tuple[float, float]) -> bool:
        """Check if two time ranges overlap"""
        start1, end1 = range1
        start2, end2 = range2
        return start1 < end2 and start2 < end1
    
    def _create_shortened_candidate(self, candidate: CutCandidateScore,
                                   target_duration: float) -> CutCandidateScore:
        """Create a shortened version of a candidate"""
        # Keep the start time, adjust end time
        new_end_time = candidate.start_time + target_duration
        
        # Proportionally adjust the score (shorter clips might be less ideal)
        duration_factor = target_duration / candidate.duration
        adjusted_score = candidate.overall_score * (0.8 + 0.2 * duration_factor)
        
        return CutCandidateScore(
            start_time=candidate.start_time,
            end_time=new_end_time,
            duration=target_duration,
            audio_score=candidate.audio_score,
            visual_score=candidate.visual_score,
            semantic_score=candidate.semantic_score * duration_factor,
            engagement_score=candidate.engagement_score,
            overall_score=adjusted_score,
            filler_word_penalty=candidate.filler_word_penalty,
            face_stability_score=candidate.face_stability_score,
            motion_intensity=candidate.motion_intensity,
            speech_clarity=candidate.speech_clarity,
            scene_boundary_alignment=candidate.scene_boundary_alignment,
            preceding_silence=candidate.preceding_silence,
            following_silence=candidate.following_silence,
            contains_scene_boundary=candidate.contains_scene_boundary,
            filler_word_count=int(candidate.filler_word_count * duration_factor),
            reasoning=f"shortened version: {candidate.reasoning}",
            exclusion_reason=None
        )
    
    def _optimize_edl(self, selected_clips: List[CutCandidateScore],
                     intelligence_results: IntelligenceResults) -> List[CutCandidateScore]:
        """Optimize the EDL for better flow and transitions"""
        if len(selected_clips) <= 1:
            return selected_clips
        
        optimized_clips = []
        
        for i, clip in enumerate(selected_clips):
            optimized_clip = clip
            
            # Apply reframing data if available
            if intelligence_results.visual_analysis and intelligence_results.visual_analysis.reframing_data:
                # This would be implemented based on face-centered reframing
                pass
            
            # Apply audio crossfading optimization
            # This would be implemented for smooth transitions
            
            optimized_clips.append(optimized_clip)
        
        return optimized_clips
    
    def _calculate_edl_quality(self, clips: List[CutCandidateScore]) -> Dict[str, float]:
        """Calculate overall EDL quality metrics"""
        if not clips:
            return {
                "overall_score": 0.0,
                "cut_smoothness": 0.0,
                "visual_continuity": 0.0,
                "semantic_coherence": 0.0,
                "engagement_score": 0.0
            }
        
        # Calculate averages
        overall_score = np.mean([clip.overall_score for clip in clips])
        cut_smoothness = np.mean([clip.face_stability_score for clip in clips])
        visual_continuity = np.mean([clip.visual_score for clip in clips])
        semantic_coherence = np.mean([clip.semantic_score for clip in clips])
        engagement_score = np.mean([clip.engagement_score for clip in clips])
        
        return {
            "overall_score": float(overall_score),
            "cut_smoothness": float(cut_smoothness),
            "visual_continuity": float(visual_continuity),
            "semantic_coherence": float(semantic_coherence),
            "engagement_score": float(engagement_score)
        }
    
    def _generate_alternative_edls(self, scored_candidates: List[CutCandidateScore],
                                  target_duration: float) -> List[Dict[str, Any]]:
        """Generate 2-3 alternative EDLs with different strategies"""
        alternatives = []
        
        # Alternative 1: Prioritize audio quality
        audio_prioritized = sorted(scored_candidates, key=lambda x: x.audio_score, reverse=True)
        alt1_clips = self._select_clips_for_edl(audio_prioritized, target_duration)
        if alt1_clips:
            alternatives.append({
                "strategy": "audio_prioritized",
                "clips": len(alt1_clips),
                "quality": self._calculate_edl_quality(alt1_clips)
            })
        
        # Alternative 2: Prioritize engagement
        engagement_prioritized = sorted(scored_candidates, key=lambda x: x.engagement_score, reverse=True)
        alt2_clips = self._select_clips_for_edl(engagement_prioritized, target_duration)
        if alt2_clips:
            alternatives.append({
                "strategy": "engagement_prioritized",
                "clips": len(alt2_clips),
                "quality": self._calculate_edl_quality(alt2_clips)
            })
        
        # Alternative 3: Balanced shorter clips
        shorter_candidates = [c for c in scored_candidates if c.duration <= 30]
        if shorter_candidates:
            alt3_clips = self._select_clips_for_edl(shorter_candidates, target_duration)
            if alt3_clips:
                alternatives.append({
                    "strategy": "shorter_clips",
                    "clips": len(alt3_clips),
                    "quality": self._calculate_edl_quality(alt3_clips)
                })
        
        return alternatives
    
    def _create_edl_output(self, video_id: str, clips: List[CutCandidateScore],
                          quality_metrics: Dict[str, float], alternatives: List[Dict[str, Any]],
                          start_time: float) -> EDLOutput:
        """Create the final EDL output object"""
        edl_id = str(uuid.uuid4())
        
        # Convert clips to output format
        clips_output = []
        timeline_position = 0.0
        
        for i, clip in enumerate(clips):
            clip_output = {
                "sequence": i,
                "source_start": clip.start_time,
                "source_end": clip.end_time,
                "timeline_start": timeline_position,
                "timeline_end": timeline_position + clip.duration,
                "scores": {
                    "audio": clip.audio_score,
                    "visual": clip.visual_score,
                    "semantic": clip.semantic_score,
                    "engagement": clip.engagement_score,
                    "overall": clip.overall_score
                },
                "reasoning": clip.reasoning,
                "filler_word_count": clip.filler_word_count,
                "face_stability": clip.face_stability_score
            }
            clips_output.append(clip_output)
            timeline_position += clip.duration
        
        actual_duration = timeline_position
        processing_time = time.time() - start_time
        
        return EDLOutput(
            edl_id=edl_id,
            video_id=video_id,
            version=1,
            target_duration=60.0,  # Default target
            actual_duration=actual_duration,
            clip_count=len(clips),
            overall_score=quality_metrics["overall_score"],
            cut_smoothness=quality_metrics["cut_smoothness"],
            visual_continuity=quality_metrics["visual_continuity"],
            semantic_coherence=quality_metrics["semantic_coherence"],
            engagement_score=quality_metrics["engagement_score"],
            clips=clips_output,
            alternative_edls=alternatives,
            generation_strategy="silence_based_fusion",
            reasoning="Multi-modal fusion with 40/30/20/10 weighting",
            processing_time=processing_time
        )
    
    def _save_edl_to_database(self, edl_output: EDLOutput, 
                             all_candidates: List[CutCandidateScore]):
        """Save EDL and candidates to database"""
        try:
            db = next(get_db())
            
            # Save EDL
            edl_db = EditDecisionList(
                id=edl_output.edl_id,
                video_id=edl_output.video_id,
                version=edl_output.version,
                status="completed",
                target_duration=edl_output.target_duration,
                actual_duration=edl_output.actual_duration,
                overall_score=edl_output.overall_score,
                cut_smoothness=edl_output.cut_smoothness,
                visual_continuity=edl_output.visual_continuity,
                semantic_coherence=edl_output.semantic_coherence,
                engagement_score=edl_output.engagement_score,
                generation_strategy=edl_output.generation_strategy,
                reasoning={"explanation": edl_output.reasoning, "alternatives": edl_output.alternative_edls},
                alternative_count=len(edl_output.alternative_edls),
                generation_time_seconds=edl_output.processing_time
            )
            db.add(edl_db)
            
            # Save clip instances
            for clip_data in edl_output.clips:
                clip_instance = ClipInstance(
                    edl_id=edl_output.edl_id,
                    sequence=clip_data["sequence"],
                    source_start_time=clip_data["source_start"],
                    source_end_time=clip_data["source_end"],
                    source_duration=clip_data["source_end"] - clip_data["source_start"],
                    timeline_start_time=clip_data["timeline_start"],
                    timeline_end_time=clip_data["timeline_end"],
                    timeline_duration=clip_data["timeline_end"] - clip_data["timeline_start"],
                    audio_score=clip_data["scores"]["audio"],
                    visual_score=clip_data["scores"]["visual"],
                    semantic_score=clip_data["scores"]["semantic"],
                    engagement_score=clip_data["scores"]["engagement"],
                    overall_score=clip_data["scores"]["overall"],
                    face_tracking_quality=clip_data["face_stability"],
                    reasoning=clip_data["reasoning"],
                    transformations={}
                )
                db.add(clip_instance)
            
            # Save cut candidates
            generation_id = f"edl_{edl_output.edl_id}"
            for i, candidate in enumerate(all_candidates):
                cut_candidate = CutCandidate(
                    video_id=edl_output.video_id,
                    edl_generation_id=generation_id,
                    start_time=candidate.start_time,
                    end_time=candidate.end_time,
                    duration=candidate.duration,
                    audio_score=candidate.audio_score,
                    visual_score=candidate.visual_score,
                    semantic_score=candidate.semantic_score,
                    engagement_score=candidate.engagement_score,
                    overall_score=candidate.overall_score,
                    filler_word_penalty=candidate.filler_word_penalty,
                    face_stability_score=candidate.face_stability_score,
                    motion_intensity=candidate.motion_intensity,
                    speech_clarity=candidate.speech_clarity,
                    scene_boundary_alignment=candidate.scene_boundary_alignment,
                    selected_for_edl=any(
                        clip["source_start"] == candidate.start_time 
                        for clip in edl_output.clips
                    ),
                    selection_rank=i + 1,
                    exclusion_reason=candidate.exclusion_reason,
                    preceding_silence_duration=candidate.preceding_silence,
                    following_silence_duration=candidate.following_silence,
                    overlaps_scene_boundary=candidate.contains_scene_boundary,
                    contains_filler_words=candidate.filler_word_count
                )
                db.add(cut_candidate)
            
            db.commit()
            logger.info("EDL saved to database", edl_id=edl_output.edl_id)
            
        except Exception as e:
            logger.error("Failed to save EDL to database", error=str(e))
            db.rollback()
        finally:
            db.close()