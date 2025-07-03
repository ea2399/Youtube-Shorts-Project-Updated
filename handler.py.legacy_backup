#!/usr/bin/env python3
"""
RunPod Handler for YouTube Shorts Generator

This handler processes video URLs and WhisperX JSON transcripts to generate Torah lecture shorts using:
1. Pre-transcribed WhisperX JSON with word-level timing
2. Pause-based segmentation for natural boundaries  
3. Context-aware GPT prompting for clip evaluation
4. FFmpeg for video processing

Input format:
{
    "input": {
        "video_url": "https://example.com/video.mp4",
        "transcript_json": {...},  # WhisperX JSON transcript
        "language": "he",          # Optional: Hebrew/English
        "num_clips": 3,            # Number of clips to generate
        "min_duration": 20,        # Minimum clip duration
        "max_duration": 60,        # Maximum clip duration
        "vertical": true,          # Create vertical versions
        "subtitles": true          # Generate subtitle files
    }
}

Output format:
{
    "output": {
        "clips": [...],
        "analysis": {...},
        "files": [...]
    }
}
"""

import os
import json
import tempfile
import traceback
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import requests
import shutil

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import our project modules
from extract_shorts import create_pause_based_segments, create_multi_pass_analysis
from cut_clips import cut_clip, create_subtitle_file
from reframe import reframe_to_vertical
from config import OPENAI_API_KEY
import openai
import runpod

def download_video_from_url(url: str, output_dir: Path) -> Path:
    """Download video from URL to local storage."""
    try:
        print(f"📥 Downloading video from: {url}")
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        
        # Determine file extension
        file_ext = ".mp4"  # Default
        if url.endswith(('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.webm')):
            file_ext = "." + url.split('.')[-1]
        
        output_path = output_dir / f"input_video{file_ext}"
        
        with open(output_path, 'wb') as f:
            shutil.copyfileobj(response.raw, f)
        
        print(f"✓ Video downloaded: {output_path}")
        return output_path
        
    except Exception as e:
        raise RuntimeError(f"Failed to download video: {str(e)}")

def create_project_structure(base_dir: Path) -> Dict[str, Path]:
    """Create project directory structure."""
    dirs = {
        "base": base_dir,
        "downloads": base_dir / "downloads",
        "clips": base_dir / "clips",
        "vertical": base_dir / "vertical"
    }
    
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    
    return dirs

def handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """Main RunPod handler function."""
    try:
        # Extract input parameters
        input_data = event.get("input", {})
        
        # Required parameters
        video_url = input_data.get("video_url")
        if not video_url:
            return {"error": "video_url is required"}
            
        transcript_json = input_data.get("transcript_json")
        if not transcript_json:
            return {"error": "transcript_json is required"}
        
        # Optional parameters with defaults
        language = input_data.get("language", "he")
        num_clips = input_data.get("num_clips", 3)
        min_duration = input_data.get("min_duration", 20)
        max_duration = input_data.get("max_duration", 60)
        vertical = input_data.get("vertical", True)
        subtitles = input_data.get("subtitles", True)
        
        print(f"🚀 Starting YouTube Shorts generation")
        print(f"📹 Video URL: {video_url}")
        print(f"📋 Transcript segments: {len(transcript_json.get('segments', []))}")
        print(f"🌐 Language: {language}")
        print(f"🎬 Clips requested: {num_clips}")
        print(f"⏱️ Duration: {min_duration}-{max_duration}s")
        print(f"📱 Vertical: {vertical}")
        print(f"📝 Subtitles: {subtitles}")
        
        # Create temporary working directory
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            dirs = create_project_structure(work_dir)
            
            print(f"📁 Working directory: {work_dir}")
            
            # Step 1: Download video
            print("\n=== Step 1: Downloading Video ===")
            video_path = download_video_from_url(video_url, dirs["downloads"])
            
            # Step 2: Use provided transcript
            print("\n=== Step 2: Using Provided Transcript ===")
            transcript_data = transcript_json
            print(f"✓ Transcript loaded: {len(transcript_data.get('segments', []))} segments")
            
            # Step 3: Create pause-based segments
            print("\n=== Step 3: Creating Natural Segments ===")
            potential_clips = create_pause_based_segments(
                transcript=transcript_data,
                min_duration=min_duration,
                max_duration=max_duration
            )
            
            print(f"✓ Created {len(potential_clips)} natural segments")
            
            # Step 4: Context-aware GPT analysis
            print("\n=== Step 4: Context-Aware Analysis ===")
            if not OPENAI_API_KEY:
                return {"error": "OpenAI API key not configured"}
            
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            
            analysis_results = create_multi_pass_analysis(
                all_segments=transcript_data["segments"],
                potential_clips=potential_clips,
                client=client
            )
            
            evaluations = analysis_results["clip_evaluations"]
            print(f"✓ Analyzed {len(evaluations)} clips")
            
            # Step 5: Select top clips
            print("\n=== Step 5: Selecting Top Clips ===")
            from extract_shorts import filter_context_aware_clips
            
            top_clips = filter_context_aware_clips(evaluations, top_n=num_clips)
            print(f"✓ Selected {len(top_clips)} top clips")
            
            # Step 6: Cut video clips
            print("\n=== Step 6: Cutting Video Clips ===")
            generated_files = []
            clip_results = []
            
            for i, clip in enumerate(top_clips, 1):
                print(f"Processing clip {i}/{len(top_clips)}: {clip['title']}")
                
                try:
                    # Cut the main clip
                    clip_path = cut_clip(
                        video_path=video_path,
                        output_dir=dirs["clips"],
                        start_time=clip["start"],
                        end_time=clip["end"],
                        clip_name=f"{i:02d}_{clip['title'][:30]}",
                        vertical=False  # We'll do vertical separately
                    )
                    generated_files.append(clip_path)
                    
                    # Create vertical version if requested
                    vertical_path = None
                    if vertical:
                        vertical_path = reframe_to_vertical(clip_path, dirs["base"])
                        generated_files.append(vertical_path)
                    
                    # Create subtitles if requested
                    subtitle_path = None
                    if subtitles:
                        subtitle_path = create_subtitle_file(clip, dirs["clips"])
                        generated_files.append(subtitle_path)
                    
                    clip_result = {
                        "index": i,
                        "title": clip["title"],
                        "start": clip["start"],
                        "end": clip["end"],
                        "duration": clip["duration"],
                        "score": clip["overall_score"],
                        "context_dependency": clip.get("context_dependency", "Unknown"),
                        "reasoning": clip["reasoning"],
                        "tags": clip["tags"],
                        "files": {
                            "horizontal": str(clip_path),
                            "vertical": str(vertical_path) if vertical_path else None,
                            "subtitle": str(subtitle_path) if subtitle_path else None
                        }
                    }
                    clip_results.append(clip_result)
                    
                    print(f"✓ Clip {i} processed successfully")
                    
                except Exception as e:
                    print(f"❌ Error processing clip {i}: {str(e)}")
                    clip_results.append({
                        "index": i,
                        "title": clip["title"],
                        "error": str(e)
                    })
            
            # Step 7: Prepare response
            print("\n=== Step 7: Preparing Response ===")
            
            # Note: Files remain in container for RunPod to handle
            file_paths = [str(f) for f in generated_files]
            
            response = {
                "output": {
                    "success": True,
                    "clips_generated": len(clip_results),
                    "clips": clip_results,
                    "transcription": {
                        "segments": len(transcript_data.get("segments", [])),
                        "language": transcript_data.get("language", language)
                    },
                    "analysis": {
                        "method": "context_aware_multi_pass",
                        "themes": analysis_results["theme_analysis"]["main_themes"],
                        "overall_topic": analysis_results["theme_analysis"]["overall_topic"],
                        "total_clips_analyzed": len(evaluations)
                    },
                    "processing_info": {
                        "language": language,
                        "vertical_created": vertical,
                        "subtitles_created": subtitles,
                        "video_url": video_url
                    },
                    "files": file_paths
                }
            }
            
            print(f"✅ Processing complete! Generated {len(clip_results)} clips")
            return response
            
    except Exception as e:
        error_msg = f"Processing failed: {str(e)}"
        print(f"❌ {error_msg}")
        print("📋 Full traceback:")
        traceback.print_exc()
        
        return {
            "error": error_msg,
            "traceback": traceback.format_exc()
        }

# For local testing and RunPod integration
if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})