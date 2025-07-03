"""
Smart Reframing Service - Phase 3
Face-centered reframing with Hebrew/English mixed content support
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional, Union
from dataclasses import dataclass
import structlog
import json

from .visual_processor import FaceTrack, FaceLandmarks
from ..models.database import VisualAnalysis as VisualAnalysisDB

logger = structlog.get_logger()


@dataclass
class ReframingConfig:
    """Configuration for reframing operations"""
    target_width: int = 720
    target_height: int = 1280
    aspect_ratio: str = "9:16"
    
    # Face-centered reframing parameters
    face_center_weight: float = 0.7     # Weight for face center vs geometric center
    eye_line_target: float = 0.3        # Target eye line position (0.3 = upper third)
    face_margin_factor: float = 1.5     # Margin around face bbox
    
    # Stability parameters
    smoothing_window: int = 5           # Frames for temporal smoothing
    max_position_change: float = 0.05   # Max position change per frame (as fraction)
    confidence_threshold: float = 0.6   # Minimum face confidence for tracking
    
    # Fallback parameters
    safe_zone_margin: float = 0.1       # Safe zone margin (10% from edges)
    default_center_x: float = 0.5       # Default horizontal center
    default_center_y: float = 0.4       # Default vertical center (slightly above center)


@dataclass
class ReframingFrame:
    """Single frame reframing data"""
    frame_index: int
    timestamp: float
    
    # Crop parameters
    crop_x: int
    crop_y: int
    crop_width: int
    crop_height: int
    
    # Source frame info
    source_width: int
    source_height: int
    
    # Face tracking data
    face_center_x: Optional[float]
    face_center_y: Optional[float]
    face_confidence: Optional[float]
    landmarks_confidence: Optional[float]
    
    # Reframing metadata
    reframing_method: str  # face_centered, safe_zone, center_crop
    stability_score: float
    reasoning: str


@dataclass
class ReframingPlan:
    """Complete reframing plan for a video segment"""
    start_time: float
    end_time: float
    duration: float
    
    # Reframing strategy
    primary_method: str
    fallback_method: str
    confidence_score: float
    
    # Frame-by-frame reframing data
    frames: List[ReframingFrame]
    
    # Quality metrics
    stability_score: float          # Temporal stability (0-1)
    coverage_score: float          # How well faces are framed (0-1)
    smoothness_score: float        # Transition smoothness (0-1)
    
    # Hebrew/English content handling
    text_orientation: str          # ltr, rtl, mixed
    subtitle_positioning: Dict[str, Any]
    text_safe_zones: List[Dict[str, float]]
    
    # Processing metadata
    total_frames: int
    processing_time: float


class ReframingService:
    """
    Smart reframing service for vertical video generation
    Supports face-centered reframing with Hebrew/English mixed content
    """
    
    def __init__(self, config: Optional[ReframingConfig] = None):
        """Initialize reframing service"""
        self.config = config or ReframingConfig()
        
        logger.info("ReframingService initialized",
                   target_resolution=f"{self.config.target_width}x{self.config.target_height}",
                   aspect_ratio=self.config.aspect_ratio)
    
    def generate_reframing_plan(self, video_path: Path, face_tracks: List[FaceTrack],
                              visual_analysis: VisualAnalysisDB, start_time: float = 0,
                              end_time: Optional[float] = None) -> ReframingPlan:
        """
        Generate complete reframing plan for a video segment
        
        Args:
            video_path: Path to source video
            face_tracks: Face tracking data from visual processor
            visual_analysis: Visual analysis results from database
            start_time: Start time for reframing (seconds)
            end_time: End time for reframing (seconds, None for full video)
        """
        logger.info("Generating reframing plan",
                   video_path=str(video_path),
                   face_tracks_count=len(face_tracks),
                   segment_start=start_time,
                   segment_end=end_time)
        
        # Get video info
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        source_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        source_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        video_duration = total_frames / fps
        
        # Calculate segment boundaries
        if end_time is None:
            end_time = video_duration
        
        start_frame = int(start_time * fps)
        end_frame = int(min(end_time * fps, total_frames))
        
        # Determine primary reframing strategy
        primary_method, confidence = self._determine_reframing_strategy(
            face_tracks, start_time, end_time, fps
        )
        
        # Generate frame-by-frame reframing data
        frames = self._generate_frame_reframing(
            cap, face_tracks, start_frame, end_frame, fps,
            source_width, source_height, primary_method
        )
        
        cap.release()
        
        # Calculate quality metrics
        stability_score = self._calculate_stability_score(frames)
        coverage_score = self._calculate_coverage_score(frames)
        smoothness_score = self._calculate_smoothness_score(frames)
        
        # Analyze text content for Hebrew/English handling
        text_analysis = self._analyze_text_content(visual_analysis)
        
        # Create reframing plan
        plan = ReframingPlan(
            start_time=start_time,
            end_time=end_time,
            duration=end_time - start_time,
            primary_method=primary_method,
            fallback_method="center_crop",
            confidence_score=confidence,
            frames=frames,
            stability_score=stability_score,
            coverage_score=coverage_score,
            smoothness_score=smoothness_score,
            text_orientation=text_analysis["orientation"],
            subtitle_positioning=text_analysis["subtitle_positioning"],
            text_safe_zones=text_analysis["safe_zones"],
            total_frames=len(frames),
            processing_time=0.0  # TODO: Track actual processing time
        )
        
        logger.info("Reframing plan generated",
                   primary_method=primary_method,
                   confidence=round(confidence, 3),
                   stability=round(stability_score, 3),
                   coverage=round(coverage_score, 3),
                   frames_count=len(frames))
        
        return plan
    
    def apply_reframing(self, video_path: Path, reframing_plan: ReframingPlan,
                       output_path: Path) -> Dict[str, Any]:
        """
        Apply reframing plan to generate vertical video
        
        Args:
            video_path: Source video path
            reframing_plan: Reframing plan from generate_reframing_plan
            output_path: Output video path
        """
        logger.info("Applying reframing plan",
                   input_video=str(video_path),
                   output_video=str(output_path),
                   method=reframing_plan.primary_method,
                   frames_count=len(reframing_plan.frames))
        
        # Open input video
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Cannot open source video: {video_path}")
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Create output video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(
            str(output_path),
            fourcc,
            fps,
            (self.config.target_width, self.config.target_height)
        )
        
        if not out.isOpened():
            raise ValueError(f"Cannot create output video: {output_path}")
        
        try:
            # Process frames according to reframing plan
            frames_processed = 0
            
            for frame_data in reframing_plan.frames:
                # Seek to frame
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_data.frame_index)
                ret, frame = cap.read()
                
                if not ret:
                    logger.warning("Failed to read frame", frame_index=frame_data.frame_index)
                    continue
                
                # Apply reframing
                reframed_frame = self._apply_frame_reframing(frame, frame_data)
                
                # Write reframed frame
                out.write(reframed_frame)
                frames_processed += 1
                
                # Progress logging
                if frames_processed % 100 == 0:
                    progress = frames_processed / len(reframing_plan.frames) * 100
                    logger.info("Reframing progress", 
                               frames_processed=frames_processed,
                               progress=f"{progress:.1f}%")
            
            logger.info("Reframing completed successfully",
                       frames_processed=frames_processed,
                       output_path=str(output_path))
            
            return {
                "status": "success",
                "frames_processed": frames_processed,
                "output_path": str(output_path),
                "reframing_method": reframing_plan.primary_method,
                "quality_scores": {
                    "stability": reframing_plan.stability_score,
                    "coverage": reframing_plan.coverage_score,
                    "smoothness": reframing_plan.smoothness_score
                }
            }
            
        finally:
            cap.release()
            out.release()
    
    def _determine_reframing_strategy(self, face_tracks: List[FaceTrack],
                                    start_time: float, end_time: float,
                                    fps: float) -> Tuple[str, float]:
        """Determine the best reframing strategy for the segment"""
        
        if not face_tracks:
            return "center_crop", 0.3
        
        # Find primary face track for this time segment
        primary_track = None
        max_overlap = 0
        
        for track in face_tracks:
            # Calculate overlap with time segment
            track_start_time = min(track.frame_indices) / fps if track.frame_indices else 0
            track_end_time = max(track.frame_indices) / fps if track.frame_indices else 0
            
            overlap_start = max(start_time, track_start_time)
            overlap_end = min(end_time, track_end_time)
            overlap_duration = max(0, overlap_end - overlap_start)
            
            if overlap_duration > max_overlap:
                max_overlap = overlap_duration
                primary_track = track
        
        if not primary_track or max_overlap < (end_time - start_time) * 0.3:
            # Less than 30% face coverage, use safe zone
            return "safe_zone", 0.4
        
        # Analyze face track quality
        avg_confidence = np.mean(primary_track.confidence_scores) if primary_track.confidence_scores else 0
        landmark_coverage = len(primary_track.landmarks) / len(primary_track.bounding_boxes) if primary_track.bounding_boxes else 0
        
        # Calculate strategy confidence
        confidence = min(1.0, avg_confidence * landmark_coverage * 1.2)
        
        if confidence >= self.config.confidence_threshold:
            return "face_centered", confidence
        else:
            return "safe_zone", confidence * 0.8
    
    def _generate_frame_reframing(self, cap: cv2.VideoCapture, face_tracks: List[FaceTrack],
                                start_frame: int, end_frame: int, fps: float,
                                source_width: int, source_height: int,
                                primary_method: str) -> List[ReframingFrame]:
        """Generate frame-by-frame reframing data"""
        
        frames = []
        
        # Create face data lookup by frame
        face_data_by_frame = {}
        for track in face_tracks:
            for i, frame_idx in enumerate(track.frame_indices):
                if start_frame <= frame_idx <= end_frame:
                    bbox = track.bounding_boxes[i] if i < len(track.bounding_boxes) else None
                    landmarks = track.landmarks[i] if i < len(track.landmarks) else None
                    confidence = track.confidence_scores[i] if i < len(track.confidence_scores) else 0
                    
                    face_data_by_frame[frame_idx] = {
                        'bbox': bbox,
                        'landmarks': landmarks,
                        'confidence': confidence
                    }
        
        # Generate reframing for each frame
        previous_crop = None
        
        for frame_idx in range(start_frame, end_frame + 1):
            timestamp = frame_idx / fps
            
            # Get face data for this frame
            face_data = face_data_by_frame.get(frame_idx)
            
            # Calculate crop parameters
            crop_params = self._calculate_frame_crop(
                face_data, source_width, source_height, primary_method, previous_crop
            )
            
            # Create frame reframing data
            frame_reframing = ReframingFrame(
                frame_index=frame_idx,
                timestamp=timestamp,
                crop_x=crop_params['x'],
                crop_y=crop_params['y'],
                crop_width=crop_params['width'],
                crop_height=crop_params['height'],
                source_width=source_width,
                source_height=source_height,
                face_center_x=crop_params.get('face_center_x'),
                face_center_y=crop_params.get('face_center_y'),
                face_confidence=crop_params.get('face_confidence'),
                landmarks_confidence=crop_params.get('landmarks_confidence'),
                reframing_method=crop_params['method'],
                stability_score=crop_params['stability_score'],
                reasoning=crop_params['reasoning']
            )
            
            frames.append(frame_reframing)
            previous_crop = crop_params
        
        # Apply temporal smoothing
        frames = self._apply_temporal_smoothing(frames)
        
        return frames
    
    def _calculate_frame_crop(self, face_data: Optional[Dict], source_width: int, source_height: int,
                            primary_method: str, previous_crop: Optional[Dict]) -> Dict[str, Any]:
        """Calculate crop parameters for a single frame"""
        
        # Calculate target crop dimensions maintaining aspect ratio
        target_aspect = self.config.target_width / self.config.target_height
        source_aspect = source_width / source_height
        
        if source_aspect > target_aspect:
            # Source is wider, crop horizontally
            crop_height = source_height
            crop_width = int(source_height * target_aspect)
        else:
            # Source is taller, crop vertically
            crop_width = source_width
            crop_height = int(source_width / target_aspect)
        
        # Default crop position (center)
        default_x = (source_width - crop_width) // 2
        default_y = int((source_height - crop_height) * self.config.default_center_y)
        
        if primary_method == "face_centered" and face_data and face_data['confidence'] >= self.config.confidence_threshold:
            # Use face-centered reframing
            crop_params = self._calculate_face_centered_crop(
                face_data, source_width, source_height, crop_width, crop_height
            )
        elif primary_method == "safe_zone":
            # Use safe zone positioning
            crop_params = self._calculate_safe_zone_crop(
                source_width, source_height, crop_width, crop_height
            )
        else:
            # Fall back to center crop
            crop_params = {
                'x': default_x,
                'y': default_y,
                'width': crop_width,
                'height': crop_height,
                'method': 'center_crop',
                'stability_score': 1.0,
                'reasoning': 'Center crop fallback'
            }
        
        # Apply stability constraints if we have previous crop
        if previous_crop:
            crop_params = self._apply_stability_constraints(crop_params, previous_crop)
        
        return crop_params
    
    def _calculate_face_centered_crop(self, face_data: Dict, source_width: int, source_height: int,
                                    crop_width: int, crop_height: int) -> Dict[str, Any]:
        """Calculate face-centered crop parameters"""
        
        bbox = face_data['bbox']
        landmarks = face_data['landmarks']
        confidence = face_data['confidence']
        
        if landmarks and landmarks.confidence > 0.7:
            # Use landmark-based centering (more accurate)
            eye_center_x = (landmarks.left_eye[0] + landmarks.right_eye[0]) / 2
            eye_center_y = (landmarks.left_eye[1] + landmarks.right_eye[1]) / 2
            mouth_y = landmarks.mouth_center[1]
            
            # Face center is between eyes and mouth
            face_center_x = eye_center_x
            face_center_y = (eye_center_y + mouth_y) / 2
            
            landmarks_confidence = landmarks.confidence
            reasoning = "Face-centered using landmarks"
            
        else:
            # Use bounding box center
            face_center_x = bbox[0] + bbox[2] / 2
            face_center_y = bbox[1] + bbox[3] / 2
            landmarks_confidence = 0.0
            reasoning = "Face-centered using bounding box"
        
        # Position face center in target composition
        # Eyes should be at 1/3 from top for vertical videos
        target_face_x = crop_width / 2
        target_face_y = crop_height * self.config.eye_line_target
        
        # Calculate crop position
        crop_x = int(face_center_x - target_face_x)
        crop_y = int(face_center_y - target_face_y)
        
        # Ensure crop stays within source boundaries
        crop_x = max(0, min(crop_x, source_width - crop_width))
        crop_y = max(0, min(crop_y, source_height - crop_height))
        
        # Calculate stability score based on landmarks quality
        stability_score = min(1.0, confidence * landmarks_confidence * 1.2)
        
        return {
            'x': crop_x,
            'y': crop_y,
            'width': crop_width,
            'height': crop_height,
            'face_center_x': face_center_x,
            'face_center_y': face_center_y,
            'face_confidence': confidence,
            'landmarks_confidence': landmarks_confidence,
            'method': 'face_centered',
            'stability_score': stability_score,
            'reasoning': reasoning
        }
    
    def _calculate_safe_zone_crop(self, source_width: int, source_height: int,
                                crop_width: int, crop_height: int) -> Dict[str, Any]:
        """Calculate safe zone crop parameters"""
        
        # Safe zone positioning - avoid extreme edges
        margin_x = int(self.config.safe_zone_margin * (source_width - crop_width))
        margin_y = int(self.config.safe_zone_margin * (source_height - crop_height))
        
        # Center within safe zone
        crop_x = margin_x + (source_width - crop_width - 2 * margin_x) // 2
        crop_y = margin_y + int((source_height - crop_height - 2 * margin_y) * self.config.default_center_y)
        
        return {
            'x': crop_x,
            'y': crop_y,
            'width': crop_width,
            'height': crop_height,
            'method': 'safe_zone',
            'stability_score': 0.8,
            'reasoning': 'Safe zone positioning'
        }
    
    def _apply_stability_constraints(self, current_crop: Dict, previous_crop: Dict) -> Dict:
        """Apply temporal stability constraints to prevent jitter"""
        
        max_change_x = int(self.config.max_position_change * current_crop['width'])
        max_change_y = int(self.config.max_position_change * current_crop['height'])
        
        # Limit position changes
        dx = current_crop['x'] - previous_crop['x']
        dy = current_crop['y'] - previous_crop['y']
        
        if abs(dx) > max_change_x:
            current_crop['x'] = previous_crop['x'] + np.sign(dx) * max_change_x
            current_crop['reasoning'] += " (X-stabilized)"
        
        if abs(dy) > max_change_y:
            current_crop['y'] = previous_crop['y'] + np.sign(dy) * max_change_y
            current_crop['reasoning'] += " (Y-stabilized)"
        
        # Update stability score based on changes
        position_change = np.sqrt(dx*dx + dy*dy) / np.sqrt(current_crop['width']**2 + current_crop['height']**2)
        stability_penalty = min(0.5, position_change * 2)
        current_crop['stability_score'] = max(0.0, current_crop['stability_score'] - stability_penalty)
        
        return current_crop
    
    def _apply_temporal_smoothing(self, frames: List[ReframingFrame]) -> List[ReframingFrame]:
        """Apply temporal smoothing to reduce jitter"""
        
        if len(frames) <= self.config.smoothing_window:
            return frames
        
        smoothed_frames = []
        half_window = self.config.smoothing_window // 2
        
        for i, frame in enumerate(frames):
            if half_window <= i < len(frames) - half_window:
                # Apply smoothing window
                window_start = i - half_window
                window_end = i + half_window + 1
                window_frames = frames[window_start:window_end]
                
                # Calculate weighted average (center frame has highest weight)
                weights = [1.0] * self.config.smoothing_window
                weights[half_window] = 2.0  # Center frame
                total_weight = sum(weights)
                
                smoothed_x = sum(f.crop_x * w for f, w in zip(window_frames, weights)) / total_weight
                smoothed_y = sum(f.crop_y * w for f, w in zip(window_frames, weights)) / total_weight
                
                # Update frame with smoothed position
                frame.crop_x = int(smoothed_x)
                frame.crop_y = int(smoothed_y)
                frame.reasoning += " (smoothed)"
            
            smoothed_frames.append(frame)
        
        return smoothed_frames
    
    def _apply_frame_reframing(self, frame: np.ndarray, frame_data: ReframingFrame) -> np.ndarray:
        """Apply reframing to a single frame"""
        
        # Extract crop region
        crop = frame[
            frame_data.crop_y:frame_data.crop_y + frame_data.crop_height,
            frame_data.crop_x:frame_data.crop_x + frame_data.crop_width
        ]
        
        # Resize to target dimensions
        reframed = cv2.resize(crop, (self.config.target_width, self.config.target_height))
        
        return reframed
    
    def _analyze_text_content(self, visual_analysis: VisualAnalysisDB) -> Dict[str, Any]:
        """Analyze text content for Hebrew/English mixed content handling"""
        
        # Default text analysis
        text_analysis = {
            "orientation": "ltr",  # Default to left-to-right
            "subtitle_positioning": {
                "bottom_margin": 0.1,   # 10% from bottom
                "side_margin": 0.05,    # 5% from sides
                "max_width": 0.9        # 90% of screen width
            },
            "safe_zones": [
                {"x": 0.05, "y": 0.8, "width": 0.9, "height": 0.15}  # Bottom subtitle area
            ]
        }
        
        # If we had text detection results, we would analyze them here
        # For now, return default configuration suitable for both Hebrew and English
        
        return text_analysis
    
    def _calculate_stability_score(self, frames: List[ReframingFrame]) -> float:
        """Calculate temporal stability score"""
        if len(frames) <= 1:
            return 1.0
        
        position_changes = []
        for i in range(1, len(frames)):
            dx = frames[i].crop_x - frames[i-1].crop_x
            dy = frames[i].crop_y - frames[i-1].crop_y
            change = np.sqrt(dx*dx + dy*dy)
            position_changes.append(change)
        
        # Normalize by frame size
        avg_frame_size = np.mean([f.crop_width + f.crop_height for f in frames]) / 2
        normalized_changes = [c / avg_frame_size for c in position_changes]
        
        # Calculate stability (lower changes = higher stability)
        avg_change = np.mean(normalized_changes)
        stability = max(0.0, 1.0 - avg_change * 10)  # Scale factor for sensitivity
        
        return stability
    
    def _calculate_coverage_score(self, frames: List[ReframingFrame]) -> float:
        """Calculate face coverage quality score"""
        face_frames = [f for f in frames if f.face_confidence and f.face_confidence > 0.5]
        
        if not face_frames:
            return 0.3  # Low score if no face detected
        
        # Average face confidence
        avg_confidence = np.mean([f.face_confidence for f in face_frames])
        
        # Face coverage ratio
        coverage_ratio = len(face_frames) / len(frames)
        
        return avg_confidence * coverage_ratio
    
    def _calculate_smoothness_score(self, frames: List[ReframingFrame]) -> float:
        """Calculate transition smoothness score"""
        individual_scores = [f.stability_score for f in frames]
        return np.mean(individual_scores)


def create_reframing_plan(video_path: Path, face_tracks: List[FaceTrack],
                         visual_analysis: VisualAnalysisDB, start_time: float = 0,
                         end_time: Optional[float] = None,
                         config: Optional[ReframingConfig] = None) -> ReframingPlan:
    """
    Convenience function for creating reframing plans
    """
    service = ReframingService(config)
    return service.generate_reframing_plan(video_path, face_tracks, visual_analysis, start_time, end_time)


def apply_reframing_to_video(video_path: Path, reframing_plan: ReframingPlan,
                           output_path: Path) -> Dict[str, Any]:
    """
    Convenience function for applying reframing to videos
    """
    service = ReframingService()
    return service.apply_reframing(video_path, reframing_plan, output_path)