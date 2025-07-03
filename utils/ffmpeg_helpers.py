import subprocess
from pathlib import Path
from typing import Optional, Tuple

from config import FFMPEG_PATH

def check_ffmpeg_installed() -> None:
    """Verify FFmpeg is installed and accessible."""
    try:
        subprocess.run([FFMPEG_PATH, "-version"], 
                      check=True, 
                      capture_output=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        raise RuntimeError(
            "FFmpeg not found. Please install FFmpeg and ensure it's in your PATH "
            "or set FFMPEG_PATH in your .env file."
        )

def run_ffmpeg_command(args: list, input_file: Optional[Path] = None) -> None:
    """Run an FFmpeg command with proper error handling."""
    try:
        cmd = [FFMPEG_PATH] + args
        if input_file:
            cmd.extend(["-i", str(input_file)])
        
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        return result
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg command failed: {e.stderr}")

def get_video_dimensions(video_path: Path) -> Tuple[int, int]:
    """Get video width and height using FFprobe."""
    cmd = [
        FFMPEG_PATH.replace("ffmpeg", "ffprobe"),
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json",
        str(video_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to get video dimensions: {result.stderr}")
    
    # TODO: Parse JSON output and return width, height
    return (1920, 1080)  # Placeholder

def get_video_duration(video_path: Path) -> float:
    """Get video duration in seconds using FFprobe."""
    cmd = [
        FFMPEG_PATH.replace("ffmpeg", "ffprobe"),
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to get video duration: {result.stderr}")
    
    return float(result.stdout.strip()) 