#!/usr/bin/env python3
"""
Detailed Diagnostics Test - Shows ALL processing info
"""

import json
import requests
import time

def test_detailed_diagnostics():
    """Enhanced test with maximum detail output"""
    
    endpoint_id = "nmj1bq1l8kvikn"
    api_key = "rpa_K6XRK8UUYECAOWUKD2ZAMWE08D6856C9YX611W0P0hnv8w"
    
    # Enhanced payload for maximum debugging
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
    
    print("🔍 DETAILED DIAGNOSTICS TEST")
    print("=" * 60)
    print(f"📹 Video: {test_payload['input']['video_url']}")
    print(f"🎯 Clips requested: {test_payload['input']['num_clips']}")
    print(f"⏱️ Duration range: {test_payload['input']['min_duration']}-{test_payload['input']['max_duration']}s")
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
            
            for i in range(90):  # Extended timeout for diagnostics
                try:
                    status_response = requests.get(status_url, headers=headers, timeout=30)
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        status = status_data.get('status', 'unknown')
                        
                        print(f"Poll {i+1}: {status}")
                        
                        if status == 'COMPLETED':
                            print("\n🎉 PROCESSING COMPLETED!")
                            output = status_data.get('output', {})
                            
                            # COMPREHENSIVE RESULTS ANALYSIS
                            print("\n" + "="*60)
                            print("📊 COMPREHENSIVE DIAGNOSTIC RESULTS")
                            print("="*60)
                            
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
                            print(f"   Source Duration: {metadata.get('duration', 'N/A')}s ({metadata.get('duration', 0)/60:.1f} minutes)")
                            print(f"   Processing Time: {metadata.get('processing_time', 'N/A')}s")
                            print(f"   Language: {metadata.get('language', 'N/A')}")
                            print(f"   Clips Requested: {metadata.get('clips_requested', 'N/A')}")
                            print(f"   Clips Generated: {metadata.get('clips_generated', 'N/A')}")
                            print(f"   Quality Level: {metadata.get('quality_level', 'N/A')}")
                            print(f"   Vertical Format: {metadata.get('vertical_format', 'N/A')}")
                            print(f"   Subtitles: {metadata.get('subtitles_enabled', 'N/A')}")
                            
                            # 4. SYSTEM INFO
                            sys_info = output.get('system_info', {})
                            print(f"\n💻 SYSTEM INFO:")
                            print(f"   GPU Used: {sys_info.get('gpu_used', 'N/A')}")
                            print(f"   CUDA Device: {sys_info.get('cuda_device', 'N/A')}")
                            phases = sys_info.get('phases_completed', [])
                            print(f"   Phases Completed: {', '.join(phases) if phases else 'N/A'}")
                            
                            # 5. DEBUG INFO (if available)
                            debug_info = output.get('debug_info', {})
                            if debug_info:
                                print(f"\n🐛 DEBUG INFORMATION:")
                                
                                # Audio analysis
                                audio_debug = debug_info.get('audio_analysis', {})
                                if audio_debug:
                                    print(f"   🎵 AUDIO ANALYSIS:")
                                    print(f"      Segments detected: {len(audio_debug.get('segments', []))}")
                                    print(f"      Filler words: {len(audio_debug.get('filler_words', []))}")
                                    print(f"      Sample rate: {audio_debug.get('sample_rate', 'N/A')}")
                                
                                # Visual analysis
                                visual_debug = debug_info.get('visual_analysis', {})
                                if visual_debug:
                                    print(f"   👁️ VISUAL ANALYSIS:")
                                    print(f"      Scenes detected: {visual_debug.get('scene_count', 'N/A')}")
                                    print(f"      Total frames: {visual_debug.get('total_frames', 'N/A')}")
                                    print(f"      FPS: {visual_debug.get('fps', 'N/A')}")
                                
                                # Transcript info
                                transcript_debug = debug_info.get('transcript', {})
                                if transcript_debug:
                                    print(f"   📝 TRANSCRIPT:")
                                    segments = transcript_debug.get('segments', [])
                                    print(f"      Segments: {len(segments)}")
                                    if segments:
                                        print(f"      First segment: {segments[0].get('text', 'N/A')[:50]}...")
                                        print(f"      Last segment: {segments[-1].get('text', 'N/A')[:50]}...")
                                
                                # EDL generation
                                edl_debug = debug_info.get('edl_generation', {})
                                if edl_debug:
                                    print(f"   ⚙️ EDL GENERATION:")
                                    print(f"      Candidate clips: {edl_debug.get('candidate_clips', 'N/A')}")
                                    print(f"      Clips after filtering: {edl_debug.get('filtered_clips', 'N/A')}")
                                    print(f"      Clips after validation: {edl_debug.get('validated_clips', 'N/A')}")
                                
                                # Rendering info
                                rendering_debug = debug_info.get('rendering', {})
                                if rendering_debug:
                                    print(f"   🎬 RENDERING:")
                                    print(f"      Clips attempted: {rendering_debug.get('clips_attempted', 'N/A')}")
                                    print(f"      Clips successful: {rendering_debug.get('clips_successful', 'N/A')}")
                                    print(f"      FFmpeg commands: {rendering_debug.get('ffmpeg_commands', 'N/A')}")
                            
                            # 6. FAILURE ANALYSIS
                            if len(clips) == 0:
                                print(f"\n❌ FAILURE ANALYSIS:")
                                print(f"   🔍 Why no clips were generated:")
                                print(f"      1. Check if transcript segments exist")
                                print(f"      2. Verify duration filters (15-90s range)")
                                print(f"      3. Check AI scoring thresholds")
                                print(f"      4. Verify FFmpeg rendering success")
                                print(f"      5. Look for file path issues")
                            
                            # 7. RAW OUTPUT (for debugging)
                            print(f"\n🔧 RAW OUTPUT (first 500 chars):")
                            print(json.dumps(output, indent=2)[:500] + "...")
                            
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
                            if i % 3 == 0:  # Show progress every 3rd poll
                                print(f"   ⏳ Processing... ({i*10}s elapsed)")
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
    result = test_detailed_diagnostics()
    
    if result and result.get('clips'):
        print("\n🎉 SUCCESS! Clips generated successfully!")
    elif result:
        print("\n⚠️ PARTIAL SUCCESS: Processing completed but no clips generated")
        print("   Check the failure analysis above for reasons")
    else:
        print("\n❌ FAILED: No results returned")