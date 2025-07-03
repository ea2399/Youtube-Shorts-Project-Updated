from pathlib import Path

from config import TARGET_LUFS
from utils.ffmpeg_helpers import run_ffmpeg_command

def normalize_audio(video_path: Path, project_path: Path) -> Path:
    """
    Normalize audio to target LUFS using FFmpeg's loudnorm filter.
    
    Args:
        video_path: Path to input video
        project_path: Path to project directory
        
    Returns:
        Path to normalized video
    """
    # First pass: analyze audio
    args = [
        "-af", f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11:print_format=json",
        "-f", "null",
        "-"
    ]
    
    result = run_ffmpeg_command(args, video_path)
    
    # Parse loudnorm stats
    # TODO: Extract measured_i, measured_tp, measured_lra, measured_thresh
    # from the JSON output
    
    # Second pass: apply normalization
    output_path = project_path / "clips" / f"{video_path.stem}_norm.mp4"
    
    args = [
        "-af", f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11",
        "-c:v", "copy",
        str(output_path)
    ]
    
    run_ffmpeg_command(args, video_path)
    return output_path 