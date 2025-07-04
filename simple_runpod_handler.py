#!/usr/bin/env python3
"""
Simplified RunPod Handler - No Database Dependencies
For quick testing without PostgreSQL/Redis complexity
"""

import json
import os
import sys
import traceback
from typing import Dict, Any, Optional

# Add app to Python path
sys.path.insert(0, '/app')

def runpod_handler(event):
    """Simplified serverless handler"""
    try:
        print("🚀 Simplified YouTube Shorts Generator")
        print("=" * 40)
        
        # Get input data
        input_data = event.get('input', {})
        
        # Extract parameters
        video_url = input_data.get('video_url', '')
        num_clips = input_data.get('num_clips', 3)
        language = input_data.get('language', 'he')
        vertical = input_data.get('vertical', True)
        subtitles = input_data.get('subtitles', True)
        
        print(f"📹 Video URL: {video_url}")
        print(f"🎯 Clips requested: {num_clips}")
        print(f"🌐 Language: {language}")
        print(f"📱 Vertical: {vertical}")
        print(f"📝 Subtitles: {subtitles}")
        
        # For now, return a success response showing the system works
        # In a real implementation, this would call your video processing pipeline
        
        result = {
            "status": "success",
            "message": "YouTube Shorts Generator is operational!",
            "clips": [
                {
                    "id": f"clip_{i:03d}",
                    "duration": 45.2,
                    "source_start": 120.5 + (i * 50),
                    "source_end": 165.7 + (i * 50),
                    "reasoning": {
                        "audio_confidence": 0.92,
                        "visual_quality": 0.88,
                        "semantic_score": 0.85,
                        "engagement_proxy": 0.91,
                        "explanation": f"Test clip {i+1} - High engagement segment with good audio quality and visual continuity"
                    },
                    "metadata": {
                        "filler_words_removed": ["um", "uh"],
                        "scene_type": "talking_head",
                        "face_tracking_quality": 0.94
                    }
                } for i in range(num_clips)
            ],
            "quality_metrics": {
                "overall_score": 8.7,
                "cut_smoothness": 0.94,
                "visual_continuity": 0.89,
                "semantic_coherence": 0.91,
                "engagement_score": 0.87
            },
            "metadata": {
                "duration": 1800.5,
                "language": language,
                "quality_score": 8.7,
                "processing_time": 12.3,
                "vertical_format": vertical,
                "subtitles_enabled": subtitles
            },
            "system_info": {
                "gpu_available": check_gpu(),
                "dependencies_loaded": check_dependencies(),
                "models_ready": check_models()
            }
        }
        
        print("✅ Processing completed successfully!")
        return result
        
    except Exception as e:
        error_msg = f"Error in simplified handler: {str(e)}"
        print(f"❌ {error_msg}")
        traceback.print_exc()
        
        return {
            "status": "error",
            "error": error_msg,
            "traceback": traceback.format_exc()
        }

def check_gpu():
    """Check if GPU is available"""
    try:
        import torch
        return {
            "available": torch.cuda.is_available(),
            "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        }
    except Exception as e:
        return {"error": str(e)}

def check_dependencies():
    """Check if core dependencies are available"""
    deps = {}
    
    try:
        import torch
        deps["torch"] = torch.__version__
    except Exception as e:
        deps["torch"] = f"Error: {e}"
    
    try:
        import cv2
        deps["opencv"] = cv2.__version__
    except Exception as e:
        deps["opencv"] = f"Error: {e}"
    
    try:
        import mediapipe as mp
        deps["mediapipe"] = mp.__version__
    except Exception as e:
        deps["mediapipe"] = f"Error: {e}"
    
    try:
        import webrtcvad
        deps["webrtcvad"] = "available"
    except Exception as e:
        deps["webrtcvad"] = f"Error: {e}"
    
    try:
        import scenedetect
        deps["scenedetect"] = "available"
    except Exception as e:
        deps["scenedetect"] = f"Error: {e}"
    
    return deps

def check_models():
    """Check if MediaPipe models are available"""
    model_paths = {
        "face_detector": "/models/mediapipe/face_detector.tflite",
        "face_landmarker": "/models/mediapipe/face_landmarker.task"
    }
    
    models = {}
    for name, path in model_paths.items():
        models[name] = {
            "path": path,
            "exists": os.path.exists(path),
            "size": os.path.getsize(path) if os.path.exists(path) else 0
        }
    
    return models

# RunPod serverless entry point
if __name__ == "__main__":
    import runpod
    runpod.serverless.start({"handler": runpod_handler})