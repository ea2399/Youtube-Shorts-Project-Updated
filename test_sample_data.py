#!/usr/bin/env python3
"""
Test with Sample Data - No external URLs needed
Uses the test payloads from your payloads/ directory
"""

import json
import requests
import os
from pathlib import Path

def load_test_payload():
    """Load a test payload from payloads directory"""
    payload_dir = Path("payloads")
    
    # Try to find a good test payload
    test_files = [
        "torah_lecture_basic.json",
        "english_shiur_quality.json", 
        "fast_processing.json"
    ]
    
    for filename in test_files:
        filepath = payload_dir / filename
        if filepath.exists():
            print(f"📄 Loading test payload: {filename}")
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    print("❌ No test payloads found in payloads/ directory")
    return None

def test_with_sample_data(endpoint_url: str):
    """Test the shorts generator with sample data"""
    print("🧪 Testing YouTube Shorts Generator with Sample Data")
    print("=" * 55)
    
    # Load test payload
    payload = load_test_payload()
    if not payload:
        return
    
    print(f"🎯 Test configuration:")
    print(f"   Language: {payload.get('language', 'N/A')}")
    print(f"   Clips requested: {payload.get('num_clips', 'N/A')}")
    print(f"   Vertical format: {payload.get('vertical', 'N/A')}")
    print()
    
    # Test health first
    print("1️⃣ Testing health endpoint...")
    try:
        health_response = requests.get(f"{endpoint_url}/health", timeout=30)
        if health_response.status_code == 200:
            print("✅ Service is healthy")
            health_data = health_response.json()
            print(f"   Status: {health_data.get('status', 'N/A')}")
            print(f"   Services: {health_data.get('services', 'N/A')}")
        else:
            print(f"❌ Health check failed: {health_response.status_code}")
            return
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return
    
    print()
    
    # Test processing
    print("2️⃣ Testing shorts generation...")
    try:
        print(f"Sending request to: {endpoint_url}/legacy/process")
        print("Request payload:")
        print(json.dumps(payload, indent=2)[:500] + "..." if len(json.dumps(payload)) > 500 else json.dumps(payload, indent=2))
        print()
        
        response = requests.post(
            f"{endpoint_url}/legacy/process",
            json=payload,
            timeout=600  # 10 minutes for processing
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("🎉 SUCCESS! Shorts generation completed!")
            print()
            
            # Analyze results
            print("📊 RESULTS ANALYSIS:")
            print("-" * 20)
            
            if 'clips' in result:
                clips = result['clips']
                print(f"📹 Generated clips: {len(clips)}")
                
                for i, clip in enumerate(clips):
                    print(f"   Clip {i+1}:")
                    print(f"     Duration: {clip.get('duration', 'N/A')} seconds")
                    print(f"     Start: {clip.get('source_start', 'N/A')}s")
                    print(f"     End: {clip.get('source_end', 'N/A')}s")
                    
                    reasoning = clip.get('reasoning', {})
                    if reasoning:
                        print(f"     AI Score: {reasoning.get('audio_confidence', 'N/A')}")
                        print(f"     Explanation: {reasoning.get('explanation', 'N/A')[:100]}...")
                    print()
            
            if 'quality_metrics' in result:
                metrics = result['quality_metrics']
                print(f"🎯 Quality Metrics:")
                print(f"   Overall Score: {metrics.get('overall_score', 'N/A')}")
                print(f"   Cut Smoothness: {metrics.get('cut_smoothness', 'N/A')}")
                print(f"   Visual Continuity: {metrics.get('visual_continuity', 'N/A')}")
                print()
            
            if 'metadata' in result:
                metadata = result['metadata']
                print(f"📝 Metadata:")
                print(f"   Source Duration: {metadata.get('duration', 'N/A')}s")
                print(f"   Language: {metadata.get('language', 'N/A')}")
                print(f"   Processing Time: {metadata.get('processing_time', 'N/A')}s")
                print()
            
            # Check for output files/URLs
            if 'output_files' in result:
                files = result['output_files']
                print(f"📁 Output Files: {len(files)} generated")
                for file_info in files:
                    print(f"   {file_info.get('type', 'Unknown')}: {file_info.get('path', 'N/A')}")
            
            return result
            
        else:
            print(f"❌ Processing failed: {response.status_code}")
            print("Error details:")
            print(response.text[:1000])
            return None
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out - processing may take longer than expected")
        print("Check RunPod logs for processing status")
        return None
    except Exception as e:
        print(f"❌ Processing error: {e}")
        return None

def main():
    """Main test function"""
    print("Enter your RunPod endpoint URL")
    print("(Format: https://your-endpoint-id.runpod.ai)")
    
    endpoint = input("Endpoint URL: ").strip()
    
    if not endpoint:
        print("❌ No endpoint provided")
        return
    
    if not endpoint.startswith('http'):
        endpoint = f"https://{endpoint}"
    
    if endpoint.endswith('.runpod.ai'):
        pass  # Already correct format
    elif '.runpod.ai' not in endpoint:
        # Assume it's just the endpoint ID
        endpoint = f"https://{endpoint}.runpod.ai"
    
    print(f"🎯 Testing endpoint: {endpoint}")
    print()
    
    test_with_sample_data(endpoint)

if __name__ == "__main__":
    main()