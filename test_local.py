#!/usr/bin/env python3
"""
Local testing script for YouTube Shorts Generator handler.

This script tests the handler function locally before deploying to RunPod.
"""

import json
import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

# Test different configurations
TEST_CONFIGS = {
    "basic": {
        "input": {
            "video_url": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4",
            "language": "en",
            "num_clips": 2,
            "min_duration": 15,
            "max_duration": 30,
            "vertical": False,
            "subtitles": False,
            "model_size": "tiny"
        }
    },
    
    "torah_mock": {
        "input": {
            "video_url": "https://example.com/torah-lecture.mp4",
            "language": "he",
            "num_clips": 3,
            "min_duration": 20,
            "max_duration": 60,
            "vertical": True,
            "subtitles": True,
            "model_size": "small"
        }
    }
}

def test_handler_import():
    """Test if handler can be imported successfully."""
    try:
        from handler import handler
        print("✅ Handler imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import handler: {e}")
        return False
    except Exception as e:
        print(f"❌ Error importing handler: {e}")
        return False

def test_dependencies():
    """Test if all dependencies are available."""
    dependencies = [
        "whisperx",
        "openai", 
        "torch",
        "ffmpeg",
        "requests",
        "python-dotenv"
    ]
    
    missing = []
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"✅ {dep}")
        except ImportError:
            print(f"❌ {dep} - missing")
            missing.append(dep)
    
    if missing:
        print(f"\n⚠️ Missing dependencies: {', '.join(missing)}")
        print("Install with: pip install -r requirements-runpod.txt")
        return False
    
    print("✅ All dependencies available")
    return True

def test_environment():
    """Test environment setup."""
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = ["OPENAI_API_KEY"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
            print(f"❌ {var} - not set")
        else:
            print(f"✅ {var} - configured")
    
    if missing_vars:
        print(f"\n⚠️ Missing environment variables: {', '.join(missing_vars)}")
        print("Create a .env file with required variables")
        return False
    
    return True

def test_handler_execution(config_name="basic"):
    """Test handler execution with mock data."""
    if config_name not in TEST_CONFIGS:
        print(f"❌ Unknown config: {config_name}")
        return False
    
    config = TEST_CONFIGS[config_name]
    
    try:
        from handler import handler
        
        print(f"🧪 Testing handler with {config_name} configuration...")
        print(f"Config: {json.dumps(config, indent=2)}")
        
        # Note: This will fail with actual URLs unless you have real videos
        # It's mainly to test the handler structure and error handling
        result = handler(config)
        
        print("📊 Handler result structure:")
        if "output" in result:
            print("✅ Success response format")
            output = result["output"]
            for key in output.keys():
                print(f"  - {key}: {type(output[key])}")
        elif "error" in result:
            print("⚠️ Error response (expected for mock URLs)")
            print(f"Error: {result['error']}")
        else:
            print("❌ Unexpected response format")
        
        return True
        
    except Exception as e:
        print(f"❌ Handler execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_model_availability():
    """Test if WhisperX models can be loaded."""
    try:
        import whisperx
        import torch
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🔧 Testing device: {device}")
        
        # Test tiny model (should be fast)
        print("🧠 Testing WhisperX model loading...")
        model = whisperx.load_model("tiny", device)
        print("✅ WhisperX model loaded successfully")
        
        del model
        torch.cuda.empty_cache() if device == "cuda" else None
        
        return True
        
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 YouTube Shorts Generator - Local Testing")
    print("=" * 50)
    
    tests = [
        ("Dependencies", test_dependencies),
        ("Environment", test_environment),
        ("Handler Import", test_handler_import),
        ("Model Availability", test_model_availability),
        ("Handler Execution", lambda: test_handler_execution("basic"))
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n📋 Testing {test_name}...")
        print("-" * 30)
        
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ Test {test_name} crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Ready for RunPod deployment.")
    else:
        print("⚠️ Some tests failed. Fix issues before deploying.")
        
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)