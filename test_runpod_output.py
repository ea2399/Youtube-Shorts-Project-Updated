#!/usr/bin/env python3
"""
Test RunPod YouTube Shorts Generator Output
Tests the complete Phase 1-5 implementation
"""

import json
import requests
import time
from typing import Dict, Any
import os

# Configuration
RUNPOD_ENDPOINT = "YOUR_RUNPOD_ENDPOINT_HERE"  # Replace with your actual endpoint
API_BASE = f"https://{RUNPOD_ENDPOINT}.runpod.ai"

def test_health_check():
    """Test if the service is running"""
    print("🏥 Testing health check...")
    try:
        response = requests.get(f"{API_BASE}/health", timeout=30)
        if response.status_code == 200:
            print("✅ Service is healthy")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_legacy_endpoint(video_url: str, num_clips: int = 3):
    """Test the legacy endpoint for backward compatibility"""
    print("🎬 Testing legacy processing endpoint...")
    
    payload = {
        "video_url": video_url,
        "num_clips": num_clips,
        "language": "he",
        "vertical": True,
        "subtitles": True
    }
    
    try:
        print(f"Sending request to: {API_BASE}/legacy/process")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            f"{API_BASE}/legacy/process",
            json=payload,
            timeout=300  # 5 minutes
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Legacy processing successful!")
            print(f"Result keys: {list(result.keys())}")
            
            # Check for expected outputs
            if 'clips' in result:
                print(f"📹 Generated {len(result['clips'])} clips")
                for i, clip in enumerate(result['clips']):
                    print(f"  Clip {i+1}: {clip.get('duration', 'N/A')}s - {clip.get('reasoning', {}).get('explanation', 'No explanation')[:100]}...")
            
            if 'quality_metrics' in result:
                print(f"📊 Quality metrics: {result['quality_metrics']}")
            
            return result
        else:
            print(f"❌ Legacy processing failed: {response.status_code}")
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Legacy processing error: {e}")
        return None

def test_modern_api_workflow():
    """Test the modern Phase 1-5 API workflow"""
    print("🚀 Testing modern API workflow...")
    
    # Step 1: Create project
    print("1️⃣ Creating project...")
    project_data = {
        "name": "Test Torah Lecture",
        "description": "Testing Phase 1-5 implementation"
    }
    
    try:
        response = requests.post(f"{API_BASE}/projects", json=project_data, timeout=30)
        if response.status_code == 200:
            project = response.json()
            project_id = project['id']
            print(f"✅ Project created: {project_id}")
        else:
            print(f"❌ Project creation failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Project creation error: {e}")
        return None
    
    # Step 2: Process video
    print("2️⃣ Processing video...")
    process_data = {
        "video_url": "https://example.com/test-video.mp4",  # You'll need a real URL
        "num_clips": 3,
        "language": "he",
        "vertical": True
    }
    
    try:
        response = requests.post(f"{API_BASE}/process", json=process_data, timeout=30)
        if response.status_code == 200:
            process_result = response.json()
            print(f"✅ Processing started: {process_result}")
            return project_id, process_result
        else:
            print(f"❌ Processing failed: {response.status_code}")
            print(f"Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Processing error: {e}")
        return None

def test_system_metrics():
    """Test system monitoring"""
    print("📊 Testing system metrics...")
    
    try:
        response = requests.get(f"{API_BASE}/metrics/system", timeout=30)
        if response.status_code == 200:
            metrics = response.json()
            print("✅ System metrics retrieved")
            print(f"GPU info: {metrics.get('gpu', 'N/A')}")
            print(f"Memory: {metrics.get('memory', 'N/A')}")
            print(f"Services: {metrics.get('services', 'N/A')}")
            return metrics
        else:
            print(f"❌ Metrics failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Metrics error: {e}")
        return None

def run_complete_test():
    """Run all tests"""
    print("🧪 Running Complete YouTube Shorts Generator Test Suite")
    print("=" * 60)
    
    # Check if endpoint is configured
    if RUNPOD_ENDPOINT == "YOUR_RUNPOD_ENDPOINT_HERE":
        print("❌ Please update RUNPOD_ENDPOINT in the script with your actual endpoint")
        print("   Find it in your RunPod dashboard under 'Endpoint URL'")
        return
    
    # Test 1: Health check
    if not test_health_check():
        print("❌ Health check failed - service may not be running")
        return
    
    print()
    
    # Test 2: System metrics
    test_system_metrics()
    print()
    
    # Test 3: Legacy endpoint (if you have a test video URL)
    test_video_url = input("Enter test video URL (or press Enter to skip): ").strip()
    if test_video_url:
        test_legacy_endpoint(test_video_url)
    else:
        print("⏭️ Skipping legacy endpoint test (no video URL provided)")
    
    print()
    
    # Test 4: Modern API workflow
    test_modern_api_workflow()
    
    print()
    print("🎯 Test Summary:")
    print("- Health check: Tests if service is running")
    print("- System metrics: Tests monitoring and GPU status")
    print("- Legacy endpoint: Tests backward compatibility")
    print("- Modern API: Tests Phase 1-5 architecture")
    print()
    print("Next steps:")
    print("1. If health check passes, your build is working!")
    print("2. Test with real video URLs to generate shorts")
    print("3. Check RunPod logs for any processing errors")

if __name__ == "__main__":
    run_complete_test()