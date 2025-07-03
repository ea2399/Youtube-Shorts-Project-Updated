import json
import argparse
import subprocess
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import re

from config import FFMPEG_PATH, VERTICAL_WIDTH, VERTICAL_HEIGHT

# Optional tkinter import for GUI file dialogs (only needed for local use)
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False

def select_video_file() -> Optional[Path]:
    """
    Prompt the user to select a video file using a file dialog.
    
    Returns:
        Path to the selected video file, or None if cancelled
    """
    if not TKINTER_AVAILABLE:
        raise RuntimeError("GUI file selection not available in serverless environment. Please provide file path directly.")
    
    # Hide the main tkinter window
    root = tk.Tk()
    root.withdraw()
    
    # Show the file dialog
    file_path = filedialog.askopenfilename(
        title="Select Video File",
        filetypes=[
            ("Video Files", "*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm"),
            ("All Files", "*.*")
        ]
    )
    
    # Return the selected file path, or None if cancelled
    return Path(file_path) if file_path else None

def select_clips_json_file() -> Optional[Path]:
    """
    Prompt the user to select a clips JSON file using a file dialog.
    
    Returns:
        Path to the selected clips file, or None if cancelled
    """
    if not TKINTER_AVAILABLE:
        raise RuntimeError("GUI file selection not available in serverless environment. Please provide file path directly.")
    
    # Hide the main tkinter window
    root = tk.Tk()
    root.withdraw()
    
    # Show the file dialog
    file_path = filedialog.askopenfilename(
        title="Select Clips JSON File",
        filetypes=[
            ("JSON Files", "*.json"),
            ("All Files", "*.*")
        ]
    )
    
    # Return the selected file path, or None if cancelled
    return Path(file_path) if file_path else None

def select_project_directory() -> Optional[Path]:
    """
    Prompt the user to select a project directory.
    
    Returns:
        Path to the selected directory, or None if cancelled
    """
    if not TKINTER_AVAILABLE:
        raise RuntimeError("GUI file selection not available in serverless environment. Please provide file path directly.")
    
    # Hide the main tkinter window
    root = tk.Tk()
    root.withdraw()
    
    # Show the directory dialog
    dir_path = filedialog.askdirectory(
        title="Select Project Directory"
    )
    
    # Return the selected directory path, or None if cancelled
    return Path(dir_path) if dir_path else None

def sanitize_filename(text: str) -> str:
    """Convert text to a safe filename."""
    # Remove non-alphanumeric characters and replace with underscores
    s = re.sub(r'[^\w\s-]', '', text.lower())
    # Replace spaces with underscores
    s = re.sub(r'[-\s]+', '_', s)
    # Remove leading/trailing underscores
    return s.strip('_')

def cut_clip(video_path: Path, 
             output_dir: Path, 
             start_time: float, 
             end_time: float, 
             clip_name: str, 
             vertical: bool = False) -> Path:
    """
    Cut a clip from the video using ffmpeg.
    
    Args:
        video_path: Path to the input video
        output_dir: Directory to save the output
        start_time: Start time in seconds
        end_time: End time in seconds
        clip_name: Name for the output file
        vertical: Whether to create a vertical (9:16) version
        
    Returns:
        Path to the output clip
    """
    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Format start and end times for ffmpeg (HH:MM:SS.mmm)
    start_str = format_time_ffmpeg(start_time)
    end_str = format_time_ffmpeg(end_time)
    
    # Sanitize clip name for filename
    safe_name = sanitize_filename(clip_name)
    if not safe_name:
        safe_name = f"clip_{start_str.replace(':', '_')}"
    
    # Calculate duration
    duration = end_time - start_time
    duration_str = format_time_ffmpeg(duration)
    
    # Regular horizontal clip
    output_path = output_dir / f"{safe_name}.mp4"
    
    cmd = [
        FFMPEG_PATH,
        "-y",  # Overwrite output files
        "-i", str(video_path),
        "-ss", start_str,  # Start time
        "-t", duration_str,  # Duration
        "-c:v", "libx264",  # Video codec
        "-c:a", "aac",  # Audio codec
        "-b:a", "192k",  # Audio bitrate
        "-movflags", "+faststart",  # Web optimization
        str(output_path)
    ]
    
    print(f"Cutting clip: {start_str} to {end_str} ({duration_str})")
    subprocess.run(cmd, check=True)
    
    # Create vertical version if requested
    if vertical:
        vertical_path = output_dir.parent / "vertical" / f"{safe_name}.mp4"
        vertical_path.parent.mkdir(exist_ok=True, parents=True)
        
        # Vertical crop command
        cmd = [
            FFMPEG_PATH,
            "-y",
            "-i", str(output_path),
            "-vf", f"scale={VERTICAL_WIDTH}:{VERTICAL_HEIGHT}:force_original_aspect_ratio=decrease,pad={VERTICAL_WIDTH}:{VERTICAL_HEIGHT}:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264",
            "-c:a", "copy",
            "-movflags", "+faststart",
            str(vertical_path)
        ]
        
        print(f"Creating vertical version")
        subprocess.run(cmd, check=True)
    
    return output_path

def format_time_ffmpeg(seconds: float) -> str:
    """Format seconds to HH:MM:SS.mmm format for ffmpeg."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

def create_subtitle_file(clip: Dict[str, Any], output_dir: Path) -> Path:
    """
    Create a subtitle file (.srt) for the clip.
    
    Args:
        clip: Clip data with text and timing
        output_dir: Directory to save the subtitle
        
    Returns:
        Path to the subtitle file
    """
    safe_name = sanitize_filename(clip["title"])
    if not safe_name:
        start_str = format_time_ffmpeg(clip["start"]).replace(':', '_')
        safe_name = f"clip_{start_str}"
    
    output_path = output_dir / f"{safe_name}.srt"
    
    # Create a simple SRT with the entire text as one entry
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("1\n")
        f.write(f"00:00:00,000 --> {format_time_srt(clip['duration'])}\n")
        f.write(clip["text"] + "\n")
    
    return output_path

def format_time_srt(seconds: float) -> str:
    """Format seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    msecs = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{msecs:03d}"

def main():
    parser = argparse.ArgumentParser(description="Cut selected clips from video")
    parser.add_argument("video_path", nargs="?", help="Path to the original video file", default=None)
    parser.add_argument("clips_json", nargs="?", help="Path to the JSON file with selected clips", default=None)
    parser.add_argument("--project_dir", help="Project directory", default=None)
    parser.add_argument("--vertical", action="store_true", help="Create vertical (9:16) versions as well")
    parser.add_argument("--subtitles", action="store_true", help="Create subtitle files for each clip")
    
    args = parser.parse_args()
    
    # Prompt for video file if not provided
    video_path = Path(args.video_path) if args.video_path else select_video_file()
    if not video_path:
        print("No video file selected. Exiting.")
        return
    
    if not video_path.exists():
        print(f"Video file not found: {video_path}")
        return
    
    # Prompt for clips JSON file if not provided
    clips_json_path = Path(args.clips_json) if args.clips_json else select_clips_json_file()
    if not clips_json_path:
        print("No clips JSON file selected. Exiting.")
        return
    
    if not clips_json_path.exists():
        print(f"Clips JSON file not found: {clips_json_path}")
        return
    
    # Prompt for project directory if not provided
    project_dir = None
    if args.project_dir:
        project_dir = Path(args.project_dir)
    else:
        # Ask user if they want to select a project directory
        if TKINTER_AVAILABLE:
            root = tk.Tk()
            root.withdraw()
            use_custom_dir = messagebox.askyesno("Project Directory", 
                                                 "Do you want to select a custom output directory?\n\n"
                                                 "If 'No', clips will be saved in the video's directory.")
            if use_custom_dir:
                project_dir = select_project_directory()
        else:
            # In serverless environment, use default project directory
            print("Using video directory as project directory (GUI not available)")
        
        # If still None, use video path's parent directory
        if not project_dir:
            project_dir = video_path.parent
            print(f"Using video directory as project directory: {project_dir}")
    
    # Create output directories
    clips_dir = project_dir / "clips"
    clips_dir.mkdir(exist_ok=True, parents=True)
    
    if args.vertical:
        vertical_dir = project_dir / "vertical"
        vertical_dir.mkdir(exist_ok=True, parents=True)
    
    # Ask for vertical option if not provided
    if not args.vertical:
        if TKINTER_AVAILABLE:
            root = tk.Tk()
            root.withdraw()
            vertical = messagebox.askyesno("Vertical Format", 
                                          "Do you want to create vertical (9:16) versions for mobile?")
        else:
            # Default to False in serverless environment
            vertical = False
            print("Vertical format disabled (GUI not available)")
    else:
        vertical = args.vertical
    
    # Ask for subtitles option if not provided
    if not args.subtitles:
        if TKINTER_AVAILABLE:
            root = tk.Tk()
            root.withdraw()
            subtitles = messagebox.askyesno("Subtitles", 
                                           "Do you want to generate subtitle files for each clip?")
        else:
            # Default to False in serverless environment
            subtitles = False
            print("Subtitles disabled (GUI not available)")
    else:
        subtitles = args.subtitles
    
    # Load clips data
    with open(clips_json_path, 'r', encoding='utf-8') as f:
        clips_data = json.load(f)
    
    clips = clips_data.get("clips", [])
    if not clips:
        print("No clips found in the JSON file.")
        return
    
    # Process each clip
    for i, clip in enumerate(clips, 1):
        print(f"\nProcessing clip {i}/{len(clips)}: {clip['title']}")
        
        try:
            # Cut the clip
            output_path = cut_clip(
                video_path=video_path,
                output_dir=clips_dir,
                start_time=clip["start"],
                end_time=clip["end"],
                clip_name=clip["title"],
                vertical=vertical
            )
            
            # Create subtitle file if requested
            if subtitles:
                subtitle_path = create_subtitle_file(clip, clips_dir)
                print(f"Created subtitle file: {subtitle_path}")
            
            print(f"✓ Clip created: {output_path}")
        
        except Exception as e:
            print(f"Error processing clip: {str(e)}")
    
    print(f"\nDone! {len(clips)} clips created in {clips_dir}")
    if vertical:
        print(f"Vertical versions saved in {project_dir / 'vertical'}")

if __name__ == "__main__":
    main() 