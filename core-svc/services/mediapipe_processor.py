"""
MediaPipe Tasks Integration - Phase 5A
Advanced face detection and landmark tracking with MediaPipe Tasks API
"""

import logging
import numpy as np
import cv2
from typing import List, Dict, Optional, Tuple, Any
import tempfile
from pathlib import Path
import asyncio
import time

try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    from mediapipe.framework.formats import landmark_pb2
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    
from pydantic import BaseModel

from ..models.schemas import ReframingFrame


logger = logging.getLogger(__name__)


class FaceDetectionResult(BaseModel):
    """Face detection result for a single frame"""
    timestamp: float
    faces: List[Dict[str, Any]] = []
    landmarks: List[Dict[str, Any]] = []
    confidence: float = 0.0
    frame_width: int = 0
    frame_height: int = 0


class MediaPipeProcessor:
    """
    Advanced MediaPipe Tasks processor for face detection and landmarks
    Optimized for video reframing and quality assessment
    """
    
    def __init__(self):
        self.available = MEDIAPIPE_AVAILABLE
        self.face_detector = None
        self.face_landmarker = None
        self.initialized = False
        
        # Processing configuration
        self.min_detection_confidence = 0.5
        self.min_tracking_confidence = 0.5
        self.face_detection_model = "blaze_face_short_range.tflite"
        self.face_landmark_model = "face_landmarker.task"
        
        if self.available:
            self._initialize_models()
    
    def _initialize_models(self):
        """Initialize MediaPipe models"""
        try:
            # Initialize Face Detector
            face_detector_options = vision.FaceDetectorOptions(
                base_options=python.BaseOptions(
                    model_asset_path=self._get_model_path("face_detector.tflite")
                ),
                min_detection_confidence=self.min_detection_confidence
            )
            
            self.face_detector = vision.FaceDetector.create_from_options(face_detector_options)
            
            # Initialize Face Landmarker  
            face_landmarker_options = vision.FaceLandmarkerOptions(
                base_options=python.BaseOptions(
                    model_asset_path=self._get_model_path("face_landmarker.task")
                ),
                min_face_detection_confidence=self.min_detection_confidence,
                min_face_presence_confidence=self.min_tracking_confidence,
                min_tracking_confidence=self.min_tracking_confidence,
                output_face_blendshapes=False,
                output_facial_transformation_matrixes=False,
                num_faces=1  # Optimize for single face scenarios
            )
            
            self.face_landmarker = vision.FaceLandmarker.create_from_options(face_landmarker_options)
            
            self.initialized = True
            logger.info("MediaPipe processor initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MediaPipe models: {e}")
            self.available = False
    
    def _get_model_path(self, model_name: str) -> str:
        """Get path to MediaPipe model file"""
        # In production, models should be downloaded and cached
        # For now, use placeholder path
        return f"/models/mediapipe/{model_name}"
    
    async def process_video_for_reframing(
        self, 
        video_path: str,
        sample_interval: float = 1.0
    ) -> List[ReframingFrame]:
        """
        Process video to generate reframing data using face detection
        
        Args:
            video_path: Path to input video file
            sample_interval: Seconds between samples (default: 1.0)
            
        Returns:
            List of reframing frames with face-centered crop data
        """
        if not self.available or not self.initialized:
            logger.warning("MediaPipe not available, using fallback reframing")
            return self._fallback_reframing(video_path, sample_interval)
        
        reframing_frames = []
        
        try:
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_interval = int(fps * sample_interval)
            
            frame_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Process every nth frame based on sample_interval
                if frame_count % frame_interval == 0:
                    timestamp = frame_count / fps
                    
                    # Process frame for face detection and landmarks
                    detection_result = await self._process_frame(frame, timestamp)
                    
                    # Generate reframing data
                    reframing_frame = self._generate_reframing_frame(
                        detection_result, frame.shape
                    )
                    
                    if reframing_frame:
                        reframing_frames.append(reframing_frame)
                
                frame_count += 1
            
            cap.release()
            
            # Smooth reframing data to avoid jitter
            reframing_frames = self._smooth_reframing_data(reframing_frames)
            
            logger.info(f"Generated {len(reframing_frames)} reframing frames for {video_path}")
            return reframing_frames
            
        except Exception as e:
            logger.error(f"Error processing video for reframing: {e}")
            return self._fallback_reframing(video_path, sample_interval)
    
    async def _process_frame(self, frame: np.ndarray, timestamp: float) -> FaceDetectionResult:
        """Process single frame for face detection and landmarks"""
        try:
            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width = frame.shape[:2]
            
            # Create MediaPipe Image
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            faces = []
            landmarks = []
            max_confidence = 0.0
            
            # Face Detection
            if self.face_detector:
                detection_result = self.face_detector.detect(mp_image)
                
                for detection in detection_result.detections:
                    bbox = detection.bounding_box
                    confidence = detection.categories[0].score
                    
                    faces.append({
                        'bbox': {
                            'x': bbox.origin_x,
                            'y': bbox.origin_y,
                            'width': bbox.width,
                            'height': bbox.height
                        },
                        'confidence': confidence
                    })
                    
                    max_confidence = max(max_confidence, confidence)
            
            # Face Landmarks
            if self.face_landmarker:
                landmark_result = self.face_landmarker.detect(mp_image)
                
                for face_landmarks in landmark_result.face_landmarks:
                    # Extract key landmarks (eyes, nose, mouth)
                    key_points = self._extract_key_landmarks(face_landmarks, width, height)
                    landmarks.append(key_points)
            
            return FaceDetectionResult(
                timestamp=timestamp,
                faces=faces,
                landmarks=landmarks,
                confidence=max_confidence,
                frame_width=width,
                frame_height=height
            )
            
        except Exception as e:
            logger.error(f"Error processing frame at {timestamp}s: {e}")
            return FaceDetectionResult(timestamp=timestamp)
    
    def _extract_key_landmarks(self, face_landmarks, width: int, height: int) -> Dict[str, Any]:
        """Extract key facial landmarks for reframing"""
        # MediaPipe face landmark indices
        LEFT_EYE = 33
        RIGHT_EYE = 263
        NOSE_TIP = 1
        MOUTH_CENTER = 13
        LEFT_EAR = 234
        RIGHT_EAR = 454
        
        landmarks = {}
        
        try:
            # Convert normalized coordinates to pixel coordinates
            for name, idx in [
                ('left_eye', LEFT_EYE),
                ('right_eye', RIGHT_EYE), 
                ('nose_tip', NOSE_TIP),
                ('mouth_center', MOUTH_CENTER),
                ('left_ear', LEFT_EAR),
                ('right_ear', RIGHT_EAR)
            ]:
                if idx < len(face_landmarks):
                    landmark = face_landmarks[idx]
                    landmarks[name] = {
                        'x': int(landmark.x * width),
                        'y': int(landmark.y * height),
                        'z': landmark.z  # Relative depth
                    }
            
            # Calculate face center from eye midpoint
            if 'left_eye' in landmarks and 'right_eye' in landmarks:
                landmarks['face_center'] = {
                    'x': (landmarks['left_eye']['x'] + landmarks['right_eye']['x']) // 2,
                    'y': (landmarks['left_eye']['y'] + landmarks['right_eye']['y']) // 2
                }
            
            return landmarks
            
        except Exception as e:
            logger.error(f"Error extracting landmarks: {e}")
            return {}
    
    def _generate_reframing_frame(
        self, 
        detection: FaceDetectionResult, 
        frame_shape: Tuple[int, int, int]
    ) -> Optional[ReframingFrame]:
        """Generate reframing data from face detection results"""
        height, width = frame_shape[:2]
        
        # Target 9:16 aspect ratio for vertical format
        target_aspect = 9 / 16
        target_width = int(height * target_aspect)
        
        try:
            if detection.faces and detection.confidence > self.min_detection_confidence:
                # Use face detection for reframing
                face = detection.faces[0]  # Use most confident face
                bbox = face['bbox']
                
                # Calculate face center
                face_center_x = bbox['x'] + bbox['width'] // 2
                face_center_y = bbox['y'] + bbox['height'] // 2
                
                # Use landmarks for more precise centering if available
                if detection.landmarks:
                    landmarks = detection.landmarks[0]
                    if 'face_center' in landmarks:
                        face_center_x = landmarks['face_center']['x']
                        face_center_y = landmarks['face_center']['y']
                
                # Calculate crop area centered on face
                crop_x = max(0, face_center_x - target_width // 2)
                if crop_x + target_width > width:
                    crop_x = width - target_width
                
                # Position face in upper third of frame for better composition
                crop_y = max(0, face_center_y - height // 3)
                crop_height = height
                
                return ReframingFrame(
                    timestamp=detection.timestamp,
                    cropX=crop_x,
                    cropY=crop_y,
                    cropWidth=target_width,
                    cropHeight=crop_height,
                    confidence=detection.confidence,
                    faceCenter={'x': face_center_x, 'y': face_center_y}
                )
            
            else:
                # Fallback to center crop
                crop_x = (width - target_width) // 2
                
                return ReframingFrame(
                    timestamp=detection.timestamp,
                    cropX=crop_x,
                    cropY=0,
                    cropWidth=target_width,
                    cropHeight=height,
                    confidence=0.1,  # Low confidence for fallback
                    faceCenter=None
                )
                
        except Exception as e:
            logger.error(f"Error generating reframing frame: {e}")
            return None
    
    def _smooth_reframing_data(self, frames: List[ReframingFrame]) -> List[ReframingFrame]:
        """Apply temporal smoothing to reduce jitter in reframing"""
        if len(frames) < 3:
            return frames
        
        smoothed_frames = []
        window_size = 3
        
        for i, frame in enumerate(frames):
            # Calculate moving average for crop position
            start_idx = max(0, i - window_size // 2)
            end_idx = min(len(frames), i + window_size // 2 + 1)
            
            avg_crop_x = sum(f.cropX for f in frames[start_idx:end_idx]) / (end_idx - start_idx)
            avg_crop_y = sum(f.cropY for f in frames[start_idx:end_idx]) / (end_idx - start_idx)
            
            # Create smoothed frame
            smoothed_frame = ReframingFrame(
                timestamp=frame.timestamp,
                cropX=int(avg_crop_x),
                cropY=int(avg_crop_y),
                cropWidth=frame.cropWidth,
                cropHeight=frame.cropHeight,
                confidence=frame.confidence,
                faceCenter=frame.faceCenter
            )
            
            smoothed_frames.append(smoothed_frame)
        
        return smoothed_frames
    
    def _fallback_reframing(self, video_path: str, sample_interval: float) -> List[ReframingFrame]:
        """Fallback reframing when MediaPipe is not available"""
        logger.info("Using fallback center-crop reframing")
        
        frames = []
        
        try:
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Generate center-crop frames at sample intervals
            target_width = int(height * 9 / 16)
            crop_x = (width - target_width) // 2
            
            sample_count = int(frame_count / fps / sample_interval)
            
            for i in range(sample_count):
                timestamp = i * sample_interval
                
                frame = ReframingFrame(
                    timestamp=timestamp,
                    cropX=crop_x,
                    cropY=0,
                    cropWidth=target_width,
                    cropHeight=height,
                    confidence=0.5,  # Default confidence for center crop
                    faceCenter={'x': width // 2, 'y': height // 2}
                )
                
                frames.append(frame)
            
            cap.release()
            
        except Exception as e:
            logger.error(f"Error in fallback reframing: {e}")
        
        return frames
    
    async def validate_face_tracking_quality(
        self, 
        reframing_frames: List[ReframingFrame]
    ) -> Dict[str, Any]:
        """Validate the quality of face tracking for the video"""
        if not reframing_frames:
            return {'quality': 'poor', 'score': 0.0, 'issues': ['No reframing data']}
        
        # Calculate quality metrics
        high_confidence_frames = sum(1 for f in reframing_frames if f.confidence > 0.8)
        face_detected_frames = sum(1 for f in reframing_frames if f.faceCenter is not None)
        
        confidence_score = high_confidence_frames / len(reframing_frames)
        detection_score = face_detected_frames / len(reframing_frames)
        
        # Calculate position stability
        positions = [(f.cropX, f.cropY) for f in reframing_frames]
        if len(positions) > 1:
            position_variance = np.var([p[0] for p in positions]) + np.var([p[1] for p in positions])
            stability_score = max(0, 1 - position_variance / 10000)  # Normalize variance
        else:
            stability_score = 1.0
        
        overall_score = (confidence_score + detection_score + stability_score) / 3
        
        # Determine quality level
        if overall_score > 0.8:
            quality = 'excellent'
        elif overall_score > 0.6:
            quality = 'good'
        elif overall_score > 0.4:
            quality = 'fair'
        else:
            quality = 'poor'
        
        # Identify issues
        issues = []
        if confidence_score < 0.5:
            issues.append('Low face detection confidence')
        if detection_score < 0.7:
            issues.append('Inconsistent face detection')
        if stability_score < 0.5:
            issues.append('Unstable face tracking')
        
        return {
            'quality': quality,
            'score': overall_score,
            'confidence_score': confidence_score,
            'detection_score': detection_score,
            'stability_score': stability_score,
            'issues': issues,
            'total_frames': len(reframing_frames),
            'face_detected_frames': face_detected_frames
        }


# Global processor instance
_processor_instance: Optional[MediaPipeProcessor] = None


def get_mediapipe_processor() -> MediaPipeProcessor:
    """Get or create global MediaPipe processor instance"""
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = MediaPipeProcessor()
    return _processor_instance


async def process_video_reframing(video_path: str, sample_interval: float = 1.0) -> List[ReframingFrame]:
    """
    Convenience function for video reframing processing
    
    Args:
        video_path: Path to input video
        sample_interval: Seconds between samples
        
    Returns:
        List of reframing frames
    """
    processor = get_mediapipe_processor()
    return await processor.process_video_for_reframing(video_path, sample_interval)