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
        print(f"✓ fastapi imported successfully (version: {fastapi.__version__})")
    except ImportError as e:
        print(f"✗ fastapi failed: {e}")
        
    try:
        import anyio
        print(f"✓ anyio imported successfully (version: {anyio.__version__})")
    except ImportError as e:
        print(f"✗ anyio failed: {e}")
        
    try:
        import celery
        print(f"✓ celery imported successfully (version: {celery.__version__})")
    except ImportError as e:
        print(f"✗ celery failed: {e}")
        
    try:
        import redis
        print(f"✓ redis imported successfully (version: {redis.__version__})")
        
        # Test redis connection capability
        client = redis.Redis(host='localhost', port=6379, decode_responses=True, socket_connect_timeout=1)
        print("✓ redis client created successfully")
    except ImportError as e:
        print(f"✗ redis failed: {e}")
    except Exception as e:
        print(f"ℹ redis import ok, connection test failed (expected): {e}")
        
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
        
    try:
        import rich
        print(f"✓ rich imported successfully (version: {rich.__version__})")
        
        # Test norfair compatibility
        import norfair
        print(f"✓ norfair imported successfully (version: {norfair.__version__})")
    except ImportError as e:
        print(f"✗ rich/norfair failed: {e}")
        
    try:
        import pydantic
        print(f"✓ pydantic imported successfully (version: {pydantic.__version__})")
        
        # Test pydantic v1 compatibility if available
        try:
            from pydantic.v1 import BaseModel as V1BaseModel
            print("✓ pydantic v1 compatibility available")
        except ImportError:
            print("ℹ pydantic v1 compatibility not available (v2 only)")
            
    except ImportError as e:
        print(f"✗ pydantic failed: {e}")

if __name__ == "__main__":
    test_imports()