#!/usr/bin/env python3
import argparse
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, parse_qs

from dotenv import load_dotenv

from download import download_video
from transcribe import transcribe_video
from highlights import extract_highlights
from srt_tools import create_clip_srts
from cut_video import cut_video_segments
from reframe import reframe_to_vertical
from normalize import normalize_audio
from utils.ffmpeg_helpers import check_ffmpeg_installed

def extract_youtube_id(url: str) -> str:
    """Extract the YouTube video ID from a URL."""
    # Clean URL first
    url = url.strip().strip('"\'')
    
    # Try to get video ID from query parameter
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    video_id = query_params.get('v', [None])[0]
    
    # If not found in query, try from path
    if not video_id:
        path = parsed_url.path
        if '/watch/' in path:
            video_id = path.split('/watch/')[1][:11]
        elif 'youtu.be' in parsed_url.netloc:
            video_id = path.strip('/').split('/')[0][:11]
    
    # Ensure video ID doesn't have spaces or special characters
    if video_id:
        video_id = video_id.strip()
    
    return video_id or "unknown"

def create_project_folder(url: str) -> Path:
    """Create project folder with timestamp and URL slug."""
    timestamp = datetime.now().strftime("%y-%m-%d")
    
    # Extract video ID from URL
    video_id = extract_youtube_id(url)
    
    # Use video ID as part of folder name, ensure it's safe for filesystems
    # Remove any characters that could cause issues in folder names
    safe_video_id = re.sub(r'[\\/*?:"<>|]', '', video_id)
    
    folder_name = f"{timestamp}_{safe_video_id}"
    
    print(f"Creating project folder for video ID: {video_id}")
    
    # Create the project directory first
    project_path = Path(folder_name)
    project_path.mkdir(exist_ok=True)
    
    # Create subdirectories
    for subdir in ["downloads", "transcripts", "clips", "vertical"]:
        (project_path / subdir).mkdir(exist_ok=True)
    
    return project_path

def main():
    parser = argparse.ArgumentParser(description="Process Torah lectures into Shorts")
    parser.add_argument("--url", required=True, help="YouTube video URL")
    parser.add_argument("--language", default="he", help="Video language code (default: he)")
    parser.add_argument("--clips", type=int, default=3, help="Number of clips to extract")
    parser.add_argument("--vertical", action="store_true", help="Convert to vertical format")
    parser.add_argument("--normalize", action="store_true", help="Normalize audio levels")
    parser.add_argument("--cookies", help="Path to cookies file for private videos")
    parser.add_argument("--dry-run", action="store_true", help="Show planned actions without executing")
    
    args = parser.parse_args()
    
    print("\n=== Torah Shorts Generator ===")
    print(f"Processing video: {args.url}")
    print(f"Language: {args.language}")
    print(f"Number of clips: {args.clips}")
    if args.vertical:
        print("Will convert to vertical format")
    if args.normalize:
        print("Will normalize audio levels")
    print("============================\n")
    
    # Load environment variables
    print("Loading environment variables...")
    load_dotenv()
    
    # Check prerequisites
    print("Checking prerequisites...")
    check_ffmpeg_installed()
    
    # Create project structure
    print("Creating project structure...")
    project_path = create_project_folder(args.url)
    print(f"Project folder: {project_path}")
    
    if args.dry_run:
        print("\n=== DRY RUN ===")
        print(f"Would process video from {args.url}")
        print(f"Project folder: {project_path}")
        return
    
    # Core pipeline
    try:
        # 1. Download video
        print("\n=== Step 1: Downloading Video ===")
        video_path = download_video(args.url, project_path, args.cookies)
        print(f"✓ Video downloaded to: {video_path}")
        
        # 2. Transcribe
        print("\n=== Step 2: Transcribing Audio ===")
        print("This may take a few minutes depending on video length...")
        transcript_path = transcribe_video(video_path, project_path, args.language)
        print(f"✓ Transcript saved to: {transcript_path}")
        
        # 3. Extract highlights
        print("\n=== Step 3: Extracting Highlights ===")
        print("Using GPT-4.1 to find engaging segments...")
        highlights = extract_highlights(transcript_path, args.clips)
        print(f"✓ Found {len(highlights)} highlight segments")
        for i, h in enumerate(highlights):
            print(f"  {i+1}. {h['hook']} ({h['start']} - {h['end']})")
        
        # 4. Create clip SRTs
        print("\n=== Step 4: Creating Subtitles ===")
        clip_srts = create_clip_srts(transcript_path, highlights, project_path)
        print(f"✓ Created {len(clip_srts)} subtitle files")
        
        # 5. Cut video segments
        print("\n=== Step 5: Cutting Video Segments ===")
        clip_paths = cut_video_segments(video_path, highlights, project_path)
        print(f"✓ Created {len(clip_paths)} video clips")
        
        # 6. Optional: Normalize audio
        if args.normalize:
            print("\n=== Step 6: Normalizing Audio ===")
            print("Adjusting audio levels to target LUFS...")
            clip_paths = [normalize_audio(clip, project_path) for clip in clip_paths]
            print("✓ Audio normalization complete")
        
        # 7. Optional: Convert to vertical
        if args.vertical:
            print("\n=== Step 7: Converting to Vertical ===")
            print("Reframing videos for vertical format...")
            vertical_paths = [reframe_to_vertical(clip, project_path) for clip in clip_paths]
            print(f"✓ Created {len(vertical_paths)} vertical videos")
        
        print("\n=== Processing Complete! ===")
        print(f"All files are available in: {project_path}")
        print("\nOutput files:")
        print(f"- Full video: {video_path}")
        print(f"- Transcript: {transcript_path}")
        print(f"- Video clips: {len(clip_paths)} files")
        if args.vertical:
            print(f"- Vertical clips: {len(vertical_paths)} files")
        print("\nThank you for using Torah Shorts Generator!")
        
    except Exception as e:
        print("\n=== Error ===")
        print(f"An error occurred during processing: {str(e)}")
        raise

if __name__ == "__main__":
    main() 