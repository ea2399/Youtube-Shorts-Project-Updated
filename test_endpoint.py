#!/usr/bin/env python3
"""
Terminal testing script for YouTube Shorts Generator RunPod endpoint.

Usage:
    python test_endpoint.py --endpoint YOUR_ENDPOINT_ID --config payloads/torah_lecture_basic.json
    python test_endpoint.py --endpoint YOUR_ENDPOINT_ID --url "https://video.com/lecture.mp4" --clips 3
"""

import argparse
import json
import requests
import time
import os
from pathlib import Path

def load_config_file(config_path: str) -> dict:
    """Load configuration from JSON file."""
    with open(config_path, 'r') as f:
        return json.load(f)

def create_config_from_args(args) -> dict:
    """Create configuration from command line arguments."""
    return {
        "input": {
            "video_url": args.url,
            "language": args.language,
            "num_clips": args.clips,
            "min_duration": args.min_duration,
            "max_duration": args.max_duration,
            "vertical": args.vertical,
            "subtitles": args.subtitles,
            "model_size": args.model
        }
    }

def call_runpod_endpoint(endpoint_id: str, config: dict, api_key: str, async_mode: bool = False, timeout: int = 600) -> dict:
    """Call RunPod endpoint with configuration."""
    
    # Construct URL
    base_url = f"https://api.runpod.ai/v2/{endpoint_id}/run"
    if async_mode:
        base_url += "Async"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    print(f"🚀 Calling RunPod endpoint: {endpoint_id}")
    print(f"📋 Configuration: {json.dumps(config, indent=2)}")
    print(f"🔗 URL: {base_url}")
    print(f"⚡ Async mode: {async_mode}")
    
    # Make initial request
    start_time = time.time()
    response = requests.post(base_url, headers=headers, json=config, timeout=60)
    response.raise_for_status()
    
    result = response.json()
    
    if async_mode:
        # Handle async response
        job_id = result.get("id")
        if not job_id:
            raise RuntimeError(f"No job ID returned: {result}")
        
        print(f"✅ Job submitted: {job_id}")
        print("⏳ Polling for results...")
        
        # Poll for completion
        status_url = f"https://api.runpod.ai/v2/{endpoint_id}/status/{job_id}"
        
        while True:
            status_response = requests.get(status_url, headers=headers, timeout=30)
            status_response.raise_for_status()
            status_result = status_response.json()
            
            status = status_result.get("status", "UNKNOWN")
            print(f"📊 Status: {status}")
            
            if status in ["COMPLETED", "FAILED"]:
                result = status_result
                break
            elif status in ["IN_QUEUE", "IN_PROGRESS"]:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    raise TimeoutError(f"Request timed out after {timeout} seconds")
                time.sleep(5)
            else:
                raise RuntimeError(f"Unknown status: {status}")
    
    elapsed_time = time.time() - start_time
    print(f"⏱️ Total time: {elapsed_time:.1f} seconds")
    
    return result

def display_results(result: dict):
    """Display results in a user-friendly format."""
    if "output" in result:
        output = result["output"]
        print("\n🎉 SUCCESS!")
        print("=" * 50)
        
        # Basic info
        print(f"📊 Clips generated: {output.get('clips_generated', 0)}")
        print(f"🎬 Transcription: {output.get('transcription', {}).get('segments', 0)} segments")
        print(f"🌐 Language: {output.get('transcription', {}).get('language', 'Unknown')}")
        print(f"🧠 Analysis method: {output.get('analysis', {}).get('method', 'Unknown')}")
        
        # Themes
        themes = output.get('analysis', {}).get('themes', [])
        if themes:
            print(f"📋 Main themes: {', '.join(themes[:3])}")
        
        topic = output.get('analysis', {}).get('overall_topic', '')
        if topic:
            print(f"🎯 Topic: {topic}")
        
        # Clips
        clips = output.get('clips', [])
        if clips:
            print(f"\n🎬 Generated Clips:")
            print("-" * 30)
            
            for clip in clips:
                if 'error' not in clip:
                    print(f"{clip['index']}. {clip['title']}")
                    print(f"   ⏱️  {clip['duration']:.1f}s ({clip['start']:.1f}s - {clip['end']:.1f}s)")
                    print(f"   📊 Score: {clip['score']:.1f}/10")
                    print(f"   🎯 Context: {clip['context_dependency']}")
                    print(f"   🏷️  Tags: {', '.join(clip['tags'])}")
                    
                    # Files
                    files = clip.get('files', {})
                    if files.get('horizontal'):
                        print(f"   📁 Horizontal: {files['horizontal']}")
                    if files.get('vertical'):
                        print(f"   📱 Vertical: {files['vertical']}")
                    if files.get('subtitle'):
                        print(f"   📝 Subtitle: {files['subtitle']}")
                    print()
                else:
                    print(f"{clip['index']}. ❌ Error: {clip['error']}")
        
        # Processing info
        processing = output.get('processing_info', {})
        if processing:
            print("⚙️ Processing Details:")
            print(f"   Model: {processing.get('model_size', 'Unknown')}")
            print(f"   Language: {processing.get('language', 'Unknown')}")
            print(f"   Vertical created: {processing.get('vertical_created', False)}")
            print(f"   Subtitles created: {processing.get('subtitles_created', False)}")
    
    elif "error" in result:
        print("\n❌ ERROR!")
        print("=" * 50)
        print(f"Error: {result['error']}")
        
        if "traceback" in result:
            print("\nTraceback:")
            print(result['traceback'])
    
    else:
        print("\n⚠️ UNEXPECTED RESPONSE")
        print("=" * 50)
        print(json.dumps(result, indent=2))

def main():
    parser = argparse.ArgumentParser(description="Test YouTube Shorts Generator RunPod endpoint")
    
    # Required
    parser.add_argument("--endpoint", required=True, help="RunPod endpoint ID")
    
    # Configuration options (either config file or individual params)
    parser.add_argument("--config", help="Path to JSON configuration file")
    parser.add_argument("--url", help="Video URL (if not using config file)")
    
    # Optional parameters
    parser.add_argument("--language", default="he", choices=["he", "en"], help="Language (default: he)")
    parser.add_argument("--clips", type=int, default=3, help="Number of clips (default: 3)")
    parser.add_argument("--min-duration", type=int, default=20, help="Min duration (default: 20)")
    parser.add_argument("--max-duration", type=int, default=60, help="Max duration (default: 60)")
    parser.add_argument("--model", default="small", choices=["tiny", "base", "small", "medium", "large-v2"], 
                       help="Model size (default: small)")
    parser.add_argument("--vertical", action="store_true", help="Create vertical versions")
    parser.add_argument("--subtitles", action="store_true", help="Create subtitle files")
    
    # API options
    parser.add_argument("--api-key", help="RunPod API key (or use RUNPOD_API_KEY env var)")
    parser.add_argument("--async", action="store_true", help="Use async mode")
    parser.add_argument("--timeout", type=int, default=600, help="Timeout in seconds (default: 600)")
    
    # Output
    parser.add_argument("--save-response", help="Save full response to JSON file")
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key or os.getenv("RUNPOD_API_KEY")
    if not api_key:
        print("❌ RunPod API key required. Use --api-key or set RUNPOD_API_KEY environment variable.")
        return 1
    
    # Load configuration
    try:
        if args.config:
            config = load_config_file(args.config)
            print(f"✅ Loaded config from: {args.config}")
        elif args.url:
            config = create_config_from_args(args)
            print("✅ Created config from arguments")
        else:
            print("❌ Either --config or --url is required")
            return 1
        
        # Call endpoint
        result = call_runpod_endpoint(
            endpoint_id=args.endpoint,
            config=config,
            api_key=api_key,
            async_mode=args.async,
            timeout=args.timeout
        )
        
        # Display results
        display_results(result)
        
        # Save response if requested
        if args.save_response:
            with open(args.save_response, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\n💾 Response saved to: {args.save_response}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())