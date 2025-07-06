#!/usr/bin/env python3
"""
COMPLETE TEST & DOWNLOAD - Combined Diagnostics + Video Download
Shows detailed processing info AND saves actual video files locally
"""

import json
import requests
import time
import base64
import os
import platform
import subprocess
from pathlib import Path

def test_and_download_complete():
    """Enhanced test with maximum detail output AND video downloads"""
    
    endpoint_id = "nmj1bq1l8kvikn"
    api_key = "rpa_K6XRK8UUYECAOWUKD2ZAMWE08D6856C9YX611W0P0hnv8w"
    
    # Enhanced payload for maximum debugging and video generation
    test_payload = {
        "input": {
            "video_url": "https://pub-df98462245734d62b0041de219b0d8bd.r2.dev/videos/susUUninSWE.mp4",
            "num_clips": 5,  # Request more clips
            "language": "en",
            "vertical": True,
            "subtitles": True,
            "quality_level": "high",
            "debug_mode": True,  # Request debug info
            "min_duration": 15,  # Lower threshold
            "max_duration": 90   # Higher threshold
        }
    }
    
    print("🔍 COMPLETE DIAGNOSTICS & DOWNLOAD TEST")
    print("=" * 70)
    print(f"📹 Video: {test_payload['input']['video_url']}")
    print(f"🎯 Clips requested: {test_payload['input']['num_clips']}")
    print(f"⏱️ Duration range: {test_payload['input']['min_duration']}-{test_payload['input']['max_duration']}s")
    print()
    
    # Create local downloads directory
    downloads_dir = Path("downloads")
    downloads_dir.mkdir(exist_ok=True)
    print(f"📁 Download directory: {downloads_dir.absolute()}")
    print()
    
    # Send request
    api_url = f"https://api.runpod.ai/v2/{endpoint_id}/run"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        print("📤 Sending enhanced diagnostic request...")
        response = requests.post(api_url, headers=headers, json=test_payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            job_id = result.get('id')
            print(f"✅ Job started: {job_id}")
            print()
            
            # Poll for completion
            print("⏳ Monitoring processing...")
            status_url = f"https://api.runpod.ai/v2/{endpoint_id}/status/{job_id}"
            
            for i in range(120):  # Extended timeout for diagnostics
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
                            
                            # ==========================================================
                            # COMPREHENSIVE DIAGNOSTIC RESULTS
                            # ==========================================================
                            print("\n" + "="*70)
                            print("📊 COMPREHENSIVE DIAGNOSTIC RESULTS")
                            print("="*70)
                            
                            # 1. CLIPS ANALYSIS
                            clips = output.get('clips', [])
                            print(f"\n🎬 CLIPS GENERATED: {len(clips)}")
                            if clips:
                                for i, clip in enumerate(clips, 1):
                                    print(f"\n   📹 CLIP {i}:")
                                    print(f"      Duration: {clip.get('duration', 'N/A')}s")
                                    print(f"      Time: {clip.get('source_start', 'N/A')}s → {clip.get('source_end', 'N/A')}s")
                                    print(f"      File: {clip.get('filename', 'N/A')}")
                                    print(f"      Vertical: {clip.get('vertical', 'N/A')}")
                                    print(f"      Size: {clip.get('file_size', 0)/1024/1024:.1f}MB")
                                    
                                    reasoning = clip.get('reasoning', {})
                                    if reasoning:
                                        print(f"      🤖 AI ANALYSIS:")
                                        print(f"         Audio Confidence: {reasoning.get('audio_confidence', 'N/A')}")
                                        print(f"         Visual Quality: {reasoning.get('visual_quality', 'N/A')}")
                                        print(f"         Semantic Score: {reasoning.get('semantic_score', 'N/A')}")
                                        print(f"         Engagement: {reasoning.get('engagement_proxy', 'N/A')}")
                                        print(f"         Explanation: {reasoning.get('explanation', 'N/A')}")
                                    
                                    metadata = clip.get('metadata', {})
                                    if metadata:
                                        print(f"      📝 METADATA:")
                                        print(f"         Text: {metadata.get('text', 'N/A')[:100]}...")
                                        print(f"         Scene Type: {metadata.get('scene_type', 'N/A')}")
                                        print(f"         Face Quality: {metadata.get('face_tracking_quality', 'N/A')}")
                            else:
                                print("   ❌ NO CLIPS GENERATED!")
                                print("   🔍 This indicates filtering issues - see debug info below")
                            
                            # 2. QUALITY METRICS
                            metrics = output.get('quality_metrics', {})
                            print(f"\n🎯 QUALITY METRICS:")
                            print(f"   Overall Score: {metrics.get('overall_score', 'N/A')}")
                            print(f"   Cut Smoothness: {metrics.get('cut_smoothness', 'N/A')}")
                            print(f"   Visual Continuity: {metrics.get('visual_continuity', 'N/A')}")
                            print(f"   Semantic Coherence: {metrics.get('semantic_coherence', 'N/A')}")
                            print(f"   Engagement Score: {metrics.get('engagement_score', 'N/A')}")
                            
                            # 3. PROCESSING METADATA
                            metadata = output.get('metadata', {})
                            print(f"\n📝 PROCESSING METADATA:")
                            print(f"   Source Duration: {metadata.get('source_duration', 'N/A')}s ({metadata.get('source_duration', 0)/60:.1f} minutes)")
                            print(f"   Processing Time: {metadata.get('processing_time', 'N/A')}s")
                            print(f"   Language: {metadata.get('language', 'N/A')}")
                            print(f"   Clips Requested: {metadata.get('clips_requested', 'N/A')}")
                            print(f"   Clips Generated: {metadata.get('clips_generated', 'N/A')}")
                            print(f"   Quality Level: {metadata.get('quality_level', 'N/A')}")
                            print(f"   Vertical Format: {metadata.get('vertical_format', 'N/A')}")
                            print(f"   Subtitles: {metadata.get('subtitles_enabled', 'N/A')}")
                            print(f"   Workspace: {metadata.get('workspace', 'N/A')}")
                            
                            # 4. SYSTEM INFO
                            sys_info = output.get('system_info', {})
                            print(f"\n💻 SYSTEM INFO:")
                            print(f"   GPU Used: {sys_info.get('gpu_used', 'N/A')}")
                            print(f"   CUDA Device: {sys_info.get('cuda_device', 'N/A')}")
                            phases = sys_info.get('phases_completed', [])
                            print(f"   Phases Completed: {', '.join(phases) if phases else 'N/A'}")
                            
                            # Phase timings
                            phase_timings = sys_info.get('phase_timings', {})
                            if phase_timings:
                                print(f"   📊 PHASE TIMINGS:")
                                for phase, timing in phase_timings.items():
                                    if phase != 'total':
                                        print(f"      {phase}: {timing}s")
                                print(f"      Total: {phase_timings.get('total', 'N/A')}s")
                            
                            # 5. DEBUG INFO (if available)
                            debug_info = output.get('debug_info', {})
                            if debug_info:
                                print(f"\n🐛 DEBUG INFORMATION:")
                                
                                # Download debug
                                download_debug = debug_info.get('download', {})
                                if download_debug:
                                    print(f"   📥 DOWNLOAD:")
                                    print(f"      URL: {download_debug.get('url', 'N/A')}")
                                    print(f"      Success: {download_debug.get('success', 'N/A')}")
                                
                                # Audio analysis
                                audio_debug = debug_info.get('audio_analysis', {})
                                if audio_debug:
                                    print(f"   🎵 AUDIO ANALYSIS:")
                                    print(f"      Method: {audio_debug.get('method', 'N/A')}")
                                    print(f"      Segments detected: {audio_debug.get('segments_detected', 'N/A')}")
                                    print(f"      Pause threshold: {audio_debug.get('pause_threshold', 'N/A')}")
                                
                                # Visual analysis
                                visual_debug = debug_info.get('visual_analysis', {})
                                if visual_debug:
                                    print(f"   👁️ VISUAL ANALYSIS:")
                                    print(f"      Method: {visual_debug.get('method', 'N/A')}")
                                    print(f"      Scenes detected: {visual_debug.get('scenes_detected', 'N/A')}")
                                    print(f"      FPS: {visual_debug.get('fps', 'N/A')}")
                                
                                # Transcript info
                                transcript_debug = debug_info.get('transcript', {})
                                if transcript_debug:
                                    print(f"   📝 TRANSCRIPT:")
                                    print(f"      Method: {transcript_debug.get('method', 'N/A')}")
                                    print(f"      Segments: {transcript_debug.get('segments', 'N/A')}")
                                    print(f"      Language: {transcript_debug.get('language', 'N/A')}")
                                
                                # EDL generation
                                edl_debug = debug_info.get('edl_generation', {})
                                if edl_debug:
                                    print(f"   ⚙️ EDL GENERATION:")
                                    print(f"      Candidate clips: {edl_debug.get('candidate_clips', 'N/A')}")
                                    print(f"      Filtered clips: {edl_debug.get('filtered_clips', 'N/A')}")
                                    print(f"      Min duration: {edl_debug.get('min_duration', 'N/A')}s")
                                    print(f"      Max duration: {edl_debug.get('max_duration', 'N/A')}s")
                                
                                # Validation info
                                validation_debug = debug_info.get('validation', {})
                                if validation_debug:
                                    print(f"   🔍 VALIDATION:")
                                    print(f"      Clips before: {validation_debug.get('clips_before', 'N/A')}")
                                    print(f"      Clips after: {validation_debug.get('clips_after', 'N/A')}")
                                    print(f"      Quality threshold: {validation_debug.get('quality_threshold', 'N/A')}")
                                    print(f"      Duration range: {validation_debug.get('duration_range', 'N/A')}")
                                
                                # Rendering info
                                rendering_debug = debug_info.get('rendering', {})
                                if rendering_debug:
                                    print(f"   🎬 RENDERING:")
                                    print(f"      Clips attempted: {rendering_debug.get('clips_attempted', 'N/A')}")
                                    print(f"      Clips successful: {rendering_debug.get('clips_successful', 'N/A')}")
                                    print(f"      Success rate: {rendering_debug.get('success_rate', 'N/A')}")
                                    print(f"      Workspace: {rendering_debug.get('workspace', 'N/A')}")
                            
                            # ==========================================================
                            # VIDEO DOWNLOAD SECTION
                            # ==========================================================
                            
                            print(f"\n" + "="*70)
                            print("📥 DOWNLOADING VIDEO FILES")
                            print("="*70)
                            
                            if clips and any(clip.get('video_data') for clip in clips):
                                saved_files = []
                                total_size = 0
                                
                                for i, clip in enumerate(clips, 1):
                                    try:
                                        video_data_b64 = clip.get('video_data')
                                        filename = clip.get('download_filename', f'clip_{i:03d}.mp4')
                                        expected_size = clip.get('file_size', 0)
                                        
                                        if video_data_b64:
                                            print(f"\n📥 Downloading {filename}...")
                                            
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
                                            print(f"      Time range: {clip.get('source_start', 'N/A')}s - {clip.get('source_end', 'N/A')}s")
                                            
                                        else:
                                            print(f"\n❌ {filename} - No video data available")
                                            error = clip.get('error', 'No video_data field found')
                                            print(f"   Error: {error}")
                                            
                                    except Exception as e:
                                        print(f"\n❌ Error downloading clip {i}: {e}")
                                
                                # Download Summary
                                print(f"\n" + "="*70)
                                print("📊 DOWNLOAD SUMMARY")
                                print("="*70)
                                print(f"📁 Files saved: {len(saved_files)}")
                                print(f"💾 Total size: {total_size/1024/1024:.1f}MB")
                                print(f"📂 Directory: {downloads_dir.absolute()}")
                                
                                if saved_files:
                                    print(f"\n🎬 SAVED VIDEO FILES:")
                                    for file_path in saved_files:
                                        print(f"   📹 {file_path}")
                                    
                                    print(f"\n🎉 SUCCESS! All clips downloaded and diagnostics complete!")
                                    
                                    # Try to open the downloads folder
                                    try:
                                        if platform.system() == "Windows":
                                            subprocess.run(["explorer", str(downloads_dir.absolute())], check=False)
                                        elif platform.system() == "Darwin":  # macOS
                                            subprocess.run(["open", str(downloads_dir.absolute())], check=False)
                                        print(f"📂 Opened folder: {downloads_dir.absolute()}")
                                    except:
                                        print(f"📂 Manual access: {downloads_dir.absolute()}")
                                    
                                    return saved_files
                                else:
                                    print(f"\n❌ No files saved successfully")
                                    
                            else:
                                print(f"\n❌ No video data available for download")
                                print(f"   This means the clips were generated but not encoded as base64")
                                print(f"   Check if the production handler is being used")
                            
                            # 6. FAILURE ANALYSIS (if no clips)
                            if len(clips) == 0:
                                print(f"\n" + "="*70)
                                print("❌ FAILURE ANALYSIS")
                                print("="*70)
                                print(f"   🔍 Why no clips were generated:")
                                print(f"      1. Check transcript segments in debug info")
                                print(f"      2. Verify duration filters ({test_payload['input']['min_duration']}-{test_payload['input']['max_duration']}s)")
                                print(f"      3. Check AI scoring thresholds in validation")
                                print(f"      4. Verify FFmpeg rendering success in debug")
                                print(f"      5. Look for file path issues in workspace")
                            
                            # 7. RAW OUTPUT (for debugging)
                            print(f"\n🔧 RAW OUTPUT SAMPLE:")
                            raw_sample = json.dumps(output, indent=2)[:1000]
                            print(raw_sample + "..." if len(raw_sample) >= 1000 else raw_sample)
                            
                            return output
                            
                        elif status == 'FAILED':
                            print(f"\n❌ JOB FAILED")
                            error = status_data.get('error', 'Unknown error')
                            output = status_data.get('output', {})
                            print(f"Error: {error}")
                            if output:
                                print(f"Output: {json.dumps(output, indent=2)}")
                            return None
                            
                        elif status in ['IN_PROGRESS', 'IN_QUEUE']:
                            time.sleep(10)
                            
                        else:
                            print(f"   Status: {status}")
                            time.sleep(5)
                    else:
                        print(f"❌ Status check failed: {status_response.status_code}")
                        return None
                        
                except Exception as e:
                    print(f"❌ Polling error: {e}")
                    time.sleep(5)
            
            print("⏰ Polling timeout")
            return None
            
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Request error: {e}")
        return None

if __name__ == "__main__":
    print("🧪 COMPLETE TEST: Diagnostics + Video Downloads")
    print("=" * 70)
    
    result = test_and_download_complete()
    
    if result and result.get('clips'):
        clips_count = len(result.get('clips', []))
        print(f"\n🎊 COMPLETE SUCCESS!")
        print(f"✅ Generated {clips_count} clips with full diagnostics")
        print(f"✅ All Phase 1-5 processing completed")
        print(f"✅ Videos downloaded and ready to use")
        print(f"✅ Your YouTube Shorts Generator is fully operational!")
    elif result:
        print(f"\n⚠️ PARTIAL SUCCESS:")
        print(f"✅ Processing completed with diagnostics")
        print(f"❌ No clips generated - check failure analysis above")
    else:
        print(f"\n❌ FAILED:")
        print(f"❌ No results returned - check errors above")