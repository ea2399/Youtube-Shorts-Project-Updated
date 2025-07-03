#!/usr/bin/env python3
"""
Test script to verify critical packages can be imported
"""

def test_imports():
    print("Testing critical package imports...")
    
    try:
        import webrtcvad
        print("✓ webrtcvad imported successfully")
    except ImportError as e:
        print(f"✗ webrtcvad failed: {e}")
    
    try:
        import mediapipe as mp
        print("✓ mediapipe imported successfully")
        
        # Test MediaPipe Tasks API
        from mediapipe.tasks.python import vision
        print("✓ mediapipe.tasks.python.vision imported successfully")
        
        # Check if face detection is available
        if hasattr(vision, 'FaceDetector'):
            print("✓ FaceDetector available in MediaPipe Tasks")
        else:
            print("✗ FaceDetector not found in MediaPipe Tasks")
            
        if hasattr(vision, 'FaceLandmarker'):
            print("✓ FaceLandmarker available in MediaPipe Tasks")
        else:
            print("✗ FaceLandmarker not found in MediaPipe Tasks")
            
    except ImportError as e:
        print(f"✗ mediapipe failed: {e}")
    
    try:
        import fastapi
        print("✓ fastapi imported successfully")
    except ImportError as e:
        print(f"✗ fastapi failed: {e}")
        
    try:
        import celery
        print("✓ celery imported successfully")
    except ImportError as e:
        print(f"✗ celery failed: {e}")
        
    try:
        import cv2
        print("✓ opencv-python imported successfully")
    except ImportError as e:
        print(f"✗ opencv-python failed: {e}")
        
    try:
        import torch
        print(f"✓ torch imported successfully (version: {torch.__version__})")
        print(f"✓ CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"✓ CUDA device count: {torch.cuda.device_count()}")
    except ImportError as e:
        print(f"✗ torch failed: {e}")
        
    try:
        import scenedetect
        print("✓ scenedetect imported successfully")
    except ImportError as e:
        print(f"✗ scenedetect failed: {e}")

if __name__ == "__main__":
    test_imports()