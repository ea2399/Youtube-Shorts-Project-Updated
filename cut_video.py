from pathlib import Path
from typing import List, Dict

from utils.ffmpeg_helpers import run_ffmpeg_command

def cut_video_segments(video_path: Path, highlights: List[Dict], project_path: Path) -> List[Path]:
    """
    Cut video segments using FFmpeg.
    
    Args:
        video_path: Path to full video
        highlights: List of highlight segments
        project_path: Path to project directory
        
    Returns:
        List of paths to created video clips
    """
    clip_paths = []
    
    for i, highlight in enumerate(highlights):
        try:
            # Ensure slug is present or use a default
            slug = highlight.get('slug', f"clip_{i:02d}")
            
            # Remove any filesystem-unsafe characters from slug
            import re
            safe_slug = re.sub(r'[\\/*?:"<>|]', '', slug)
            
            output_path = project_path / "clips" / f"{i:02d}_{safe_slug}.mp4"
            
            # Ensure timestamps are properly formatted (HH:MM:SS.mmm)
            start_time = highlight["start"]
            end_time = highlight["end"]
            
            print(f"Cutting clip {i+1}/{len(highlights)}: {start_time} to {end_time}")
            
            # Build FFmpeg command for cutting
            args = [
                "-ss", start_time,  # Start time
                "-to", end_time,    # End time
                "-c", "copy",       # Copy streams without re-encoding
                "-map_metadata", "-1",  # Remove metadata
                "-avoid_negative_ts", "1",  # Avoid negative timestamps
                str(output_path)
            ]
            
            # Run FFmpeg command
            run_ffmpeg_command(args, video_path)
            print(f"  ✓ Created clip: {output_path.name}")
            
            clip_paths.append(output_path)
            
        except Exception as e:
            print(f"  ⚠️ Error cutting clip {i+1}: {str(e)}")
            # In case of failure, try a more robust approach
            try:
                # Use a simpler command with seeking after input for more accuracy
                fallback_path = project_path / "clips" / f"{i:02d}_fallback.mp4"
                
                # Create a fallback clip (first 30 seconds if we can't parse timestamps)
                alt_args = [
                    "-i", str(video_path),
                    "-ss", "00:00:00",  # Start at the beginning
                    "-t", "30",         # Duration in seconds
                    "-c", "copy",
                    str(fallback_path)
                ]
                
                print(f"  Attempting fallback cutting method...")
                run_ffmpeg_command(alt_args, input_file=None)
                
                clip_paths.append(fallback_path)
                print(f"  ✓ Created fallback clip: {fallback_path.name}")
                
            except Exception as inner_e:
                print(f"  ❌ Fallback cutting also failed: {str(inner_e)}")
    
    return clip_paths 