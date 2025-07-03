"""
Visual Intelligence System - Phase 2
Modern computer vision pipeline with RT-DETR v2, MediaPipe face tracking, and scene detection
"""

import cv2
import numpy as np
import torch
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
import structlog
import tempfile
from skimage.metrics import structural_similarity as ssim
import scenedetect
from scenedetect.detectors import ContentDetector, AdaptiveDetector
from scenedetect.video_splitter import split_video_ffmpeg
from scenedetect.scene_manager import SceneManager

# MediaPipe imports
try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    mp = None

# RT-DETR imports (via ultralytics)
try:
    from ultralytics import RTDETR
    RTDETR_AVAILABLE = True
except ImportError:
    RTDETR_AVAILABLE = False

# Norfair tracker
try:
    import norfair
    from norfair import Detection, Tracker
    NORFAIR_AVAILABLE = True
except ImportError:
    NORFAIR_AVAILABLE = False

logger = structlog.get_logger()


@dataclass
class FaceLandmarks:
    """6-point facial landmarks (eyes, nose, mouth, ears)"""
    left_eye: Tuple[float, float]
    right_eye: Tuple[float, float] 
    nose_tip: Tuple[float, float]
    mouth_center: Tuple[float, float]
    left_ear: Tuple[float, float]
    right_ear: Tuple[float, float]
    confidence: float


@dataclass
class FaceTrack:
    """Face tracking data with landmarks over time"""
    track_id: int
    bounding_boxes: List[Tuple[float, float, float, float]]  # (x, y, w, h)
    landmarks: List[FaceLandmarks]
    confidence_scores: List[float]
    frame_indices: List[int]


@dataclass
class SceneBoundary:
    """Scene change detection result"""
    start_frame: int
    end_frame: int
    start_time: float
    end_time: float
    scene_type: str  # content, adaptive, or manual
    confidence: float


@dataclass
class VisualAnalysis:
    """Complete visual analysis results"""
    face_tracks: List[FaceTrack]
    object_detections: List[Dict[str, Any]]
    scene_boundaries: List[SceneBoundary]
    quality_metrics: Dict[str, float]
    motion_analysis: Dict[str, Any]
    reframing_data: Dict[str, Any]


class VisualProcessor:
    """
    Visual Intelligence System for Phase 2
    Provides face detection/tracking, object detection, and scene analysis
    """
    
    def __init__(self):
        """Initialize visual processor with models"""
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Model paths (will be downloaded if not exists)
        self.face_detector_path = None
        self.face_landmarker_path = None
        
        # Lazy-loaded models
        self._face_detector = None
        self._face_landmarker = None
        self._rtdetr_model = None
        self._tracker = None
        
        logger.info("VisualProcessor initialized", 
                   device=str(self.device),
                   mediapipe_available=MEDIAPIPE_AVAILABLE,
                   rtdetr_available=RTDETR_AVAILABLE,
                   norfair_available=NORFAIR_AVAILABLE)
    
    def _get_face_detector(self):
        """Lazy load MediaPipe Face Detector"""
        if not MEDIAPIPE_AVAILABLE:
            logger.warning("MediaPipe not available, skipping face detection")
            return None
            
        if self._face_detector is None:
            try:
                # Initialize MediaPipe Face Detector
                base_options = python.BaseOptions(
                    model_asset_path=self.face_detector_path or 'face_detector.task'
                )
                options = vision.FaceDetectorOptions(
                    base_options=base_options,
                    min_detection_confidence=0.5
                )
                self._face_detector = vision.FaceDetector.create_from_options(options)
                logger.info("MediaPipe Face Detector loaded")
            except Exception as e:
                logger.warning("Failed to load MediaPipe Face Detector", error=str(e))
                self._face_detector = None
                
        return self._face_detector
    
    def _get_face_landmarker(self):
        """Lazy load MediaPipe Face Landmarker"""
        if not MEDIAPIPE_AVAILABLE:
            return None
            
        if self._face_landmarker is None:
            try:
                base_options = python.BaseOptions(
                    model_asset_path=self.face_landmarker_path or 'face_landmarker.task'
                )
                options = vision.FaceLandmarkerOptions(
                    base_options=base_options,
                    num_faces=1,  # Track primary speaker
                    min_face_detection_confidence=0.5,
                    min_face_presence_confidence=0.5,
                    min_tracking_confidence=0.5
                )
                self._face_landmarker = vision.FaceLandmarker.create_from_options(options)
                logger.info("MediaPipe Face Landmarker loaded")
            except Exception as e:
                logger.warning("Failed to load MediaPipe Face Landmarker", error=str(e))
                self._face_landmarker = None
                
        return self._face_landmarker
    
    def _get_rtdetr_model(self):
        """Lazy load RT-DETR v2 model"""
        if not RTDETR_AVAILABLE:
            logger.warning("RT-DETR not available, skipping object detection")
            return None
            
        if self._rtdetr_model is None:
            try:
                # Load RT-DETR model (will download if not cached)
                self._rtdetr_model = RTDETR('rtdetr-l.pt')  # Large model for best accuracy
                logger.info("RT-DETR v2 model loaded")
            except Exception as e:
                logger.warning("Failed to load RT-DETR model", error=str(e))
                self._rtdetr_model = None
                
        return self._rtdetr_model
    
    def _get_tracker(self):
        """Initialize Norfair tracker for stability"""
        if not NORFAIR_AVAILABLE:
            return None
            
        if self._tracker is None:
            try:
                # Configure tracker for face tracking
                self._tracker = Tracker(
                    distance_function=norfair.distances.euclidean_distance,
                    distance_threshold=50,  # Adjust based on face size
                    hit_counter_max=30,     # Keep tracks for 30 frames
                    initialization_delay=3   # Confirm tracks after 3 frames
                )
                logger.info("Norfair tracker initialized")
            except Exception as e:
                logger.warning("Failed to initialize Norfair tracker", error=str(e))
                self._tracker = None
                
        return self._tracker
    
    def detect_faces_in_video(self, video_path: Path) -> List[FaceTrack]:
        """
        Detect and track faces throughout video with landmarks
        Returns stable face tracks with 6-point landmarks
        """
        face_detector = self._get_face_detector()
        face_landmarker = self._get_face_landmarker()
        tracker = self._get_tracker()
        
        if not face_detector or not face_landmarker:
            logger.warning("Face detection models not available")
            return []
        
        face_tracks = []
        cap = cv2.VideoCapture(str(video_path))
        
        if not cap.isOpened():
            logger.error("Failed to open video file", video_path=str(video_path))
            return []
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Track data per detection
        raw_detections = []
        frame_idx = 0
        
        logger.info("Starting face detection", 
                   total_frames=frame_count, 
                   fps=fps)
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Convert BGR to RGB for MediaPipe
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                
                # Face detection
                detection_result = face_detector.detect(mp_image)
                
                # Face landmark detection
                landmark_result = face_landmarker.detect(mp_image)
                
                # Process detections
                if detection_result.detections:
                    for i, detection in enumerate(detection_result.detections):
                        bbox = detection.bounding_box
                        confidence = detection.categories[0].score if detection.categories else 0.0
                        
                        # Extract landmarks if available
                        landmarks = None
                        if (landmark_result.face_landmarks and 
                            i < len(landmark_result.face_landmarks)):
                            landmarks = self._extract_key_landmarks(
                                landmark_result.face_landmarks[i],
                                frame.shape
                            )
                        
                        raw_detections.append({
                            'frame': frame_idx,
                            'bbox': (bbox.origin_x, bbox.origin_y, bbox.width, bbox.height),
                            'confidence': confidence,
                            'landmarks': landmarks,
                            'timestamp': frame_idx / fps
                        })
                
                frame_idx += 1
                
                # Progress logging
                if frame_idx % 100 == 0:
                    logger.info("Face detection progress", 
                               frames_processed=frame_idx,
                               detections_found=len(raw_detections))
        
        finally:
            cap.release()
        
        # Convert raw detections to stable tracks using Norfair if available
        if tracker and raw_detections:
            face_tracks = self._create_stable_tracks(raw_detections, tracker)
        else:
            # Fallback: simple grouping by temporal proximity
            face_tracks = self._simple_track_grouping(raw_detections)
        
        logger.info("Face detection completed", 
                   total_tracks=len(face_tracks),
                   total_detections=len(raw_detections))
        
        return face_tracks
    
    def _extract_key_landmarks(self, face_landmarks, frame_shape) -> FaceLandmarks:
        """Extract 6 key landmarks from MediaPipe 468-point landmarks"""
        height, width = frame_shape[:2]
        
        # MediaPipe landmark indices for key points
        # These are approximate - adjust based on MediaPipe Face Mesh topology
        LEFT_EYE_IDX = 33      # Left eye center
        RIGHT_EYE_IDX = 263    # Right eye center  
        NOSE_TIP_IDX = 1       # Nose tip
        MOUTH_CENTER_IDX = 13  # Mouth center
        LEFT_EAR_IDX = 234     # Left ear (approximate)
        RIGHT_EAR_IDX = 454    # Right ear (approximate)
        
        def get_landmark_coord(idx):
            if idx < len(face_landmarks):
                landmark = face_landmarks[idx]
                return (landmark.x * width, landmark.y * height)
            return (0.0, 0.0)
        
        # Calculate confidence as average of all landmark visibility scores
        confidences = [lm.visibility for lm in face_landmarks if hasattr(lm, 'visibility')]
        avg_confidence = np.mean(confidences) if confidences else 0.8
        
        return FaceLandmarks(
            left_eye=get_landmark_coord(LEFT_EYE_IDX),
            right_eye=get_landmark_coord(RIGHT_EYE_IDX),
            nose_tip=get_landmark_coord(NOSE_TIP_IDX),
            mouth_center=get_landmark_coord(MOUTH_CENTER_IDX),
            left_ear=get_landmark_coord(LEFT_EAR_IDX),
            right_ear=get_landmark_coord(RIGHT_EAR_IDX),
            confidence=avg_confidence
        )
    
    def _create_stable_tracks(self, raw_detections: List[Dict], tracker) -> List[FaceTrack]:
        """Use Norfair to create stable face tracks"""
        # Group detections by frame
        frame_detections = {}
        for det in raw_detections:
            frame_idx = det['frame']
            if frame_idx not in frame_detections:
                frame_detections[frame_idx] = []
            frame_detections[frame_idx].append(det)
        
        # Process each frame through tracker
        all_tracked_objects = {}
        
        for frame_idx in sorted(frame_detections.keys()):
            detections = frame_detections[frame_idx]
            
            # Convert to Norfair Detection objects
            norfair_detections = []
            for det in detections:
                bbox = det['bbox']
                center_x = bbox[0] + bbox[2] / 2
                center_y = bbox[1] + bbox[3] / 2
                
                norfair_det = Detection(
                    points=np.array([[center_x, center_y]]),
                    scores=np.array([det['confidence']])
                )
                norfair_det.original_detection = det  # Store original data
                norfair_detections.append(norfair_det)
            
            # Update tracker
            tracked_objects = tracker.update(detections=norfair_detections)
            
            # Store tracked objects
            for obj in tracked_objects:
                track_id = obj.id
                if track_id not in all_tracked_objects:
                    all_tracked_objects[track_id] = []
                
                if hasattr(obj, 'last_detection') and obj.last_detection:
                    original_det = obj.last_detection.original_detection
                    all_tracked_objects[track_id].append(original_det)
        
        # Convert to FaceTrack objects
        face_tracks = []
        for track_id, detections in all_tracked_objects.items():
            if len(detections) < 5:  # Filter short tracks
                continue
            
            track = FaceTrack(
                track_id=track_id,
                bounding_boxes=[det['bbox'] for det in detections],
                landmarks=[det['landmarks'] for det in detections if det['landmarks']],
                confidence_scores=[det['confidence'] for det in detections],
                frame_indices=[det['frame'] for det in detections]
            )
            face_tracks.append(track)
        
        return face_tracks
    
    def _simple_track_grouping(self, raw_detections: List[Dict]) -> List[FaceTrack]:
        """Fallback track grouping when Norfair is not available"""
        if not raw_detections:
            return []
        
        # Simple temporal grouping
        tracks = []
        current_track = []
        
        for detection in sorted(raw_detections, key=lambda x: x['frame']):
            if (not current_track or 
                detection['frame'] - current_track[-1]['frame'] <= 5):  # 5 frame gap tolerance
                current_track.append(detection)
            else:
                # Start new track
                if len(current_track) >= 5:  # Minimum track length
                    track = FaceTrack(
                        track_id=len(tracks),
                        bounding_boxes=[det['bbox'] for det in current_track],
                        landmarks=[det['landmarks'] for det in current_track if det['landmarks']],
                        confidence_scores=[det['confidence'] for det in current_track],
                        frame_indices=[det['frame'] for det in current_track]
                    )
                    tracks.append(track)
                current_track = [detection]
        
        # Add final track
        if len(current_track) >= 5:
            track = FaceTrack(
                track_id=len(tracks),
                bounding_boxes=[det['bbox'] for det in current_track],
                landmarks=[det['landmarks'] for det in current_track if det['landmarks']],
                confidence_scores=[det['confidence'] for det in current_track],
                frame_indices=[det['frame'] for det in current_track]
            )
            tracks.append(track)
        
        return tracks
    
    def detect_objects(self, video_path: Path) -> List[Dict[str, Any]]:
        """Detect objects using RT-DETR v2"""
        rtdetr_model = self._get_rtdetr_model()
        
        if not rtdetr_model:
            logger.warning("RT-DETR model not available")
            return []
        
        try:
            # Run RT-DETR on video
            results = rtdetr_model(str(video_path), save=False, verbose=False)
            
            object_detections = []
            for result in results:
                frame_detections = []
                
                if result.boxes is not None:
                    boxes = result.boxes.xyxy.cpu().numpy()  # x1, y1, x2, y2
                    scores = result.boxes.conf.cpu().numpy()
                    classes = result.boxes.cls.cpu().numpy()
                    
                    for box, score, cls in zip(boxes, scores, classes):
                        detection = {
                            "bbox": box.tolist(),  # [x1, y1, x2, y2]
                            "confidence": float(score),
                            "class_id": int(cls),
                            "class_name": rtdetr_model.names[int(cls)]
                        }
                        frame_detections.append(detection)
                
                object_detections.append({
                    "frame_index": len(object_detections),
                    "detections": frame_detections
                })
            
            logger.info("Object detection completed", 
                       total_frames=len(object_detections))
            
            return object_detections
            
        except Exception as e:
            logger.error("Object detection failed", error=str(e))
            return []
    
    def detect_scene_boundaries(self, video_path: Path) -> List[SceneBoundary]:
        """Detect scene boundaries using PySceneDetect"""
        try:
            # Create SceneManager and add detectors
            scene_manager = SceneManager()
            scene_manager.add_detector(ContentDetector(threshold=27.0))
            scene_manager.add_detector(AdaptiveDetector())
            
            # Perform scene detection
            scene_manager.detect_scenes(str(video_path), show_progress=False)
            scene_list = scene_manager.get_scene_list()
            
            # Convert to SceneBoundary objects
            boundaries = []
            for i, (start_time, end_time) in enumerate(scene_list):
                boundary = SceneBoundary(
                    start_frame=int(start_time.get_frames()),
                    end_frame=int(end_time.get_frames()),
                    start_time=start_time.get_seconds(),
                    end_time=end_time.get_seconds(),
                    scene_type="content",
                    confidence=0.8  # Default confidence for PySceneDetect
                )
                boundaries.append(boundary)
            
            logger.info("Scene detection completed", 
                       scenes_found=len(boundaries))
            
            return boundaries
            
        except Exception as e:
            logger.error("Scene detection failed", error=str(e))
            return []
    
    def calculate_visual_quality_metrics(self, video_path: Path, 
                                       face_tracks: List[FaceTrack]) -> Dict[str, float]:
        """Calculate visual quality metrics including SSIM"""
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                return {}
            
            metrics = {}
            
            # Sample frames for SSIM analysis
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            sample_indices = np.linspace(0, frame_count-1, min(50, frame_count), dtype=int)
            
            frames = []
            for idx in sample_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if ret:
                    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    frames.append(gray_frame)
            
            cap.release()
            
            if len(frames) < 2:
                return {}
            
            # Calculate SSIM between consecutive frames
            ssim_scores = []
            for i in range(len(frames) - 1):
                score = ssim(frames[i], frames[i+1])
                ssim_scores.append(score)
            
            metrics["ssim_mean"] = np.mean(ssim_scores)
            metrics["ssim_std"] = np.std(ssim_scores)
            metrics["ssim_min"] = np.min(ssim_scores)
            
            # Motion intensity analysis
            motion_scores = []
            for i in range(len(frames) - 1):
                diff = cv2.absdiff(frames[i], frames[i+1])
                motion_intensity = np.mean(diff) / 255.0
                motion_scores.append(motion_intensity)
            
            metrics["motion_intensity_mean"] = np.mean(motion_scores)
            metrics["motion_intensity_max"] = np.max(motion_scores)
            
            # Face tracking quality metrics
            if face_tracks:
                # Calculate average confidence across all tracks
                all_confidences = []
                for track in face_tracks:
                    all_confidences.extend(track.confidence_scores)
                
                metrics["face_tracking_quality"] = np.mean(all_confidences) if all_confidences else 0.0
                metrics["face_tracks_count"] = len(face_tracks)
                
                # Stability metric: consistency of face positions
                if face_tracks[0].bounding_boxes:
                    positions = []
                    for bbox in face_tracks[0].bounding_boxes:
                        center_x = bbox[0] + bbox[2] / 2
                        center_y = bbox[1] + bbox[3] / 2
                        positions.append((center_x, center_y))
                    
                    if len(positions) > 1:
                        position_changes = []
                        for i in range(len(positions) - 1):
                            dx = positions[i+1][0] - positions[i][0]
                            dy = positions[i+1][1] - positions[i][1]
                            change = np.sqrt(dx*dx + dy*dy)
                            position_changes.append(change)
                        
                        metrics["face_stability"] = 1.0 / (1.0 + np.mean(position_changes))
                    else:
                        metrics["face_stability"] = 1.0
                else:
                    metrics["face_stability"] = 0.0
            else:
                metrics["face_tracking_quality"] = 0.0
                metrics["face_tracks_count"] = 0
                metrics["face_stability"] = 0.0
            
            logger.info("Visual quality metrics calculated",
                       ssim_mean=round(metrics.get("ssim_mean", 0), 3),
                       motion_intensity=round(metrics.get("motion_intensity_mean", 0), 3),
                       face_quality=round(metrics.get("face_tracking_quality", 0), 3))
            
            return metrics
            
        except Exception as e:
            logger.error("Visual quality metrics calculation failed", error=str(e))
            return {}
    
    def process_video(self, video_path: Path) -> VisualAnalysis:
        """
        Complete visual processing pipeline
        Returns comprehensive visual analysis
        """
        logger.info("Starting visual intelligence processing", video_path=str(video_path))
        
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
        valid_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv'}
        if video_path.suffix.lower() not in valid_extensions:
            raise ValueError(f"Unsupported video format: {video_path.suffix}")
        
        try:
            # Step 1: Face detection and tracking
            face_tracks = self.detect_faces_in_video(video_path)
            
            # Step 2: Object detection
            object_detections = self.detect_objects(video_path)
            
            # Step 3: Scene boundary detection
            scene_boundaries = self.detect_scene_boundaries(video_path)
            
            # Step 4: Quality metrics calculation
            quality_metrics = self.calculate_visual_quality_metrics(video_path, face_tracks)
            
            # Step 5: Motion analysis (based on quality metrics)
            motion_analysis = {
                "intensity_mean": quality_metrics.get("motion_intensity_mean", 0.0),
                "intensity_max": quality_metrics.get("motion_intensity_max", 0.0),
                "stability_score": quality_metrics.get("face_stability", 0.0)
            }
            
            # Step 6: Reframing data (face-centered)
            reframing_data = self._calculate_reframing_data(face_tracks)
            
            analysis = VisualAnalysis(
                face_tracks=face_tracks,
                object_detections=object_detections,
                scene_boundaries=scene_boundaries,
                quality_metrics=quality_metrics,
                motion_analysis=motion_analysis,
                reframing_data=reframing_data
            )
            
            logger.info("Visual intelligence processing completed",
                       face_tracks=len(face_tracks),
                       object_detections=len(object_detections),
                       scene_boundaries=len(scene_boundaries))
            
            return analysis
            
        except Exception as e:
            logger.error("Visual processing failed", error=str(e))
            raise
    
    def _calculate_reframing_data(self, face_tracks: List[FaceTrack]) -> Dict[str, Any]:
        """Calculate face-centered reframing data for vertical crops"""
        if not face_tracks:
            return {"method": "center_crop", "confidence": 0.0}
        
        # Use the primary (longest) face track
        primary_track = max(face_tracks, key=lambda t: len(t.bounding_boxes))
        
        # Calculate optimal crop centers based on face positions
        crop_centers = []
        confidences = []
        
        for bbox, landmarks, confidence in zip(
            primary_track.bounding_boxes, 
            primary_track.landmarks, 
            primary_track.confidence_scores
        ):
            if landmarks and landmarks.confidence > 0.5:
                # Use landmark-based center (more accurate)
                eye_center_x = (landmarks.left_eye[0] + landmarks.right_eye[0]) / 2
                eye_center_y = (landmarks.left_eye[1] + landmarks.right_eye[1]) / 2
                mouth_y = landmarks.mouth_center[1]
                
                # Optimal head center for vertical crop
                head_center_x = eye_center_x
                head_center_y = (eye_center_y + mouth_y) / 2
                
                crop_centers.append((head_center_x, head_center_y))
                confidences.append(landmarks.confidence)
            else:
                # Fallback to bounding box center
                center_x = bbox[0] + bbox[2] / 2
                center_y = bbox[1] + bbox[3] / 2
                crop_centers.append((center_x, center_y))
                confidences.append(confidence * 0.7)  # Lower confidence for bbox-only
        
        if not crop_centers:
            return {"method": "center_crop", "confidence": 0.0}
        
        # Smooth crop centers to avoid jitter
        smoothed_centers = self._smooth_crop_centers(crop_centers)
        avg_confidence = np.mean(confidences)
        
        return {
            "method": "face_centered",
            "crop_centers": smoothed_centers,
            "confidence": avg_confidence,
            "tracking_quality": len(crop_centers) / len(primary_track.bounding_boxes),
            "recommended_aspect_ratio": "9:16"  # Standard vertical
        }
    
    def _smooth_crop_centers(self, centers: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Apply temporal smoothing to crop centers to reduce jitter"""
        if len(centers) < 3:
            return centers
        
        smoothed = []
        window_size = min(5, len(centers))
        
        for i in range(len(centers)):
            start_idx = max(0, i - window_size // 2)
            end_idx = min(len(centers), i + window_size // 2 + 1)
            
            window_centers = centers[start_idx:end_idx]
            avg_x = np.mean([c[0] for c in window_centers])
            avg_y = np.mean([c[1] for c in window_centers])
            
            smoothed.append((avg_x, avg_y))
        
        return smoothed