#!/usr/bin/env python3
"""
Download and Save Clips from RunPod Response
Decodes base64 video data and saves as MP4 files
"""

import json
import requests
import time
import base64
import os
from pathlib import Path

def download_and_save_clips():
    """Test RunPod and save all generated clips locally"""
    
    endpoint_id = "nmj1bq1l8kvikn"
    api_key = "rpa_K6XRK8UUYECAOWUKD2ZAMWE08D6856C9YX611W0P0hnv8w"
    
    # Enhanced payload for video generation
    test_payload = {
        "input": {
            "video_url": "https://pub-df98462245734d62b0041de219b0d8bd.r2.dev/videos/susUUninSWE.mp4",
            "num_clips": 5,
            "language": "en",
            "vertical": True,
            "subtitles": True,
            "quality_level": "high",
            "debug_mode": True,
            "min_duration": 15,
            "max_duration": 90
        }
    }
    
    print("🎬 DOWNLOADING CLIPS FROM RUNPOD")
    print("=" * 50)
    print(f"📹 Video: {test_payload['input']['video_url']}")
    print(f"🎯 Clips: {test_payload['input']['num_clips']}")
    print()
    
    # Create local downloads directory
    downloads_dir = Path("downloads")
    downloads_dir.mkdir(exist_ok=True)
    print(f"📁 Download directory: {downloads_dir.absolute()}")
    
    # Send request
    api_url = f"https://api.runpod.ai/v2/{endpoint_id}/run"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        print("📤 Sending request to RunPod...")
        response = requests.post(api_url, headers=headers, json=test_payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            job_id = result.get('id')
            print(f"✅ Job started: {job_id}")
            print()
            
            # Poll for completion
            print("⏳ Waiting for processing...")
            status_url = f"https://api.runpod.ai/v2/{endpoint_id}/status/{job_id}"
            
            for i in range(120):  # 20 minutes max
                try:
                    status_response = requests.get(status_url, headers=headers, timeout=30)
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        status = status_data.get('status', 'unknown')
                        
                        if i % 6 == 0:  # Show progress every minute
                            print(f"Poll {i+1}: {status} ({i*10}s elapsed)")
                        
                        if status == 'COMPLETED':
                            print("\n🎉 PROCESSING COMPLETED!")
                            output = status_data.get('output', {})
                            
                            # Download and save clips
                            clips = output.get('clips', [])
                            print(f"\n📥 DOWNLOADING {len(clips)} CLIPS:")
                            print("-" * 40)
                            
                            saved_files = []
                            total_size = 0
                            
                            for i, clip in enumerate(clips, 1):
                                try:
                                    video_data_b64 = clip.get('video_data')
                                    filename = clip.get('download_filename', f'clip_{i:03d}.mp4')
                                    file_size = clip.get('file_size', 0)
                                    
                                    if video_data_b64:
                                        # Decode base64 video data
                                        video_data = base64.b64decode(video_data_b64)
                                        
                                        # Save to local file
                                        file_path = downloads_dir / filename
                                        with open(file_path, 'wb') as f:
                                            f.write(video_data)
                                        
                                        # Verify file
                                        actual_size = os.path.getsize(file_path)
                                        saved_files.append(str(file_path))
                                        total_size += actual_size
                                        
                                        print(f"   ✅ {filename}")
                                        print(f"      Duration: {clip.get('duration', 'N/A')}s")
                                        print(f"      Size: {actual_size/1024/1024:.1f}MB")
                                        print(f"      Path: {file_path}")
                                        
                                        # Show AI analysis
                                        reasoning = clip.get('reasoning', {})
                                        if reasoning:
                                            print(f"      AI Score: {reasoning.get('audio_confidence', 'N/A')}")
                                        print()
                                        
                                    else:
                                        print(f"   ❌ {filename} - No video data")
                                        error = clip.get('error', 'Unknown error')
                                        print(f"      Error: {error}")
                                        print()
                                        
                                except Exception as e:
                                    print(f"   ❌ Error saving clip {i}: {e}")
                                    print()
                            
                            # Summary
                            print("=" * 50)
                            print("📊 DOWNLOAD SUMMARY:")
                            print(f"   Files saved: {len(saved_files)}")
                            print(f"   Total size: {total_size/1024/1024:.1f}MB")
                            print(f"   Directory: {downloads_dir.absolute()}")
                            
                            if saved_files:
                                print(f"\n🎬 SAVED FILES:")
                                for file_path in saved_files:
                                    print(f"   📹 {file_path}")
                                
                                print(f"\n🎉 SUCCESS! All clips downloaded!")
                                print(f"📂 Open folder: {downloads_dir.absolute()}")
                                
                                # Show system info
                                sys_info = output.get('system_info', {})
                                if sys_info:
                                    print(f"\n💻 PROCESSING INFO:")
                                    print(f"   GPU: {sys_info.get('cuda_device', 'N/A')}")
                                    processing_time = sys_info.get('phase_timings', {}).get('total', 'N/A')
                                    print(f"   Total time: {processing_time}s")
                                    phases = sys_info.get('phases_completed', [])
                                    print(f"   Phases: {', '.join(phases)}")
                                
                                return saved_files
                            else:
                                print(f"\n❌ No files saved - check for errors above")
                                return []
                            
                        elif status == 'FAILED':
                            print(f"\n❌ JOB FAILED")
                            error = status_data.get('error', 'Unknown error')
                            print(f"Error: {error}")
                            return []
                            
                        elif status in ['IN_PROGRESS', 'IN_QUEUE']:
                            time.sleep(10)
                            
                        else:
                            print(f"   Status: {status}")
                            time.sleep(5)
                    else:
                        print(f"❌ Status check failed: {status_response.status_code}")
                        return []
                        
                except Exception as e:
                    print(f"❌ Polling error: {e}")
                    time.sleep(5)
            
            print("⏰ Polling timeout")
            return []
            
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return []
            
    except Exception as e:
        print(f"❌ Request error: {e}")
        return []

if __name__ == "__main__":
    saved_files = download_and_save_clips()
    
    if saved_files:
        print(f"\n🎊 COMPLETE! {len(saved_files)} video files ready to use!")
        
        # Optional: Open the downloads folder
        import platform
        import subprocess
        
        try:
            downloads_dir = Path("downloads").absolute()
            if platform.system() == "Windows":
                subprocess.run(["explorer", str(downloads_dir)], check=False)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(downloads_dir)], check=False)
            print(f"📂 Opened folder: {downloads_dir}")
        except:
            pass
    else:
        print(f"\n❌ No files downloaded - check errors above")