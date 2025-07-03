from pathlib import Path
from typing import List

from config import VERTICAL_WIDTH, VERTICAL_HEIGHT
from utils.ffmpeg_helpers import run_ffmpeg_command, get_video_dimensions

def reframe_to_vertical(video_path: Path, project_path: Path) -> Path:
    """
    Convert video to vertical format (9:16) using FFmpeg.
    
    Args:
        video_path: Path to input video
        project_path: Path to project directory
        
    Returns:
        Path to vertical video
    """
    # Get input dimensions
    width, height = get_video_dimensions(video_path)
    
    # Calculate crop parameters
    if width / height > 16/9:  # Wider than 16:9
        # Center crop to 16:9 first
        crop_width = height * 16/9
        crop_x = (width - crop_width) / 2
        crop_filter = f"crop={crop_width}:{height}:{crop_x}:0"
    else:
        # Already 16:9 or taller
        crop_filter = "null"
    
    # Build FFmpeg filter chain
    filter_chain = [
        crop_filter,
        f"scale={VERTICAL_WIDTH}:-2",
        f"crop={VERTICAL_WIDTH}:{VERTICAL_HEIGHT}",
        f"pad={VERTICAL_WIDTH}:{VERTICAL_HEIGHT}:(ow-iw)/2:(oh-ih)/2",
        "boxblur=luma_radius=min(h\\,w)/20"
    ]
    
    # Remove null filters
    filter_chain = [f for f in filter_chain if f != "null"]
    
    # Prepare output path
    output_path = project_path / "vertical" / f"{video_path.stem}_vertical.mp4"
    
    # Build FFmpeg command
    args = [
        "-vf", ",".join(filter_chain),
        "-c:a", "copy",
        str(output_path)
    ]
    
    run_ffmpeg_command(args, video_path)
    return output_path 