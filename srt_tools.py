import pysrt
from pathlib import Path
from typing import List, Dict
from datetime import timedelta, datetime, time

def parse_timestamp(timestamp: str) -> timedelta:
    """Convert SRT timestamp string to timedelta."""
    hours, minutes, seconds = timestamp.split(":")
    # Handle both comma and period as decimal separators
    seconds = seconds.replace(',', '.')
    
    # Split seconds and milliseconds
    if '.' in seconds:
        seconds, milliseconds = seconds.split('.')
        milliseconds = milliseconds.ljust(3, '0')[:3]  # Ensure 3 digits for milliseconds
    else:
        milliseconds = '0'
    
    return timedelta(
        hours=int(hours),
        minutes=int(minutes),
        seconds=int(seconds),
        milliseconds=int(milliseconds)
    )

def format_timestamp(delta: timedelta) -> str:
    """Convert timedelta to SRT timestamp string."""
    total_seconds = int(delta.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    milliseconds = int(delta.microseconds / 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def time_to_timedelta(t: time) -> timedelta:
    """Convert datetime.time to timedelta for comparison."""
    return timedelta(hours=t.hour, minutes=t.minute, seconds=t.second, microseconds=t.microsecond)

def create_txt_from_srt(srt_path: Path) -> Path:
    """Create a plain text version of the SRT file with just the subtitles."""
    subs = pysrt.open(str(srt_path))
    
    # Extract text from SRT
    text_lines = []
    for sub in subs:
        text_lines.append(sub.text)
    
    # Create a matching TXT file
    txt_path = srt_path.with_suffix('.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(text_lines))
    
    print(f"  ✓ Created text file: {txt_path.name}")
    return txt_path

def create_clip_srts(transcript_path: Path, highlights: List[Dict], project_path: Path) -> List[Path]:
    """
    Create SRT files for each highlight clip.
    
    Args:
        transcript_path: Path to full transcript
        highlights: List of highlight segments
        project_path: Path to project directory
        
    Returns:
        List of paths to created SRT files
    """
    # Load full transcript
    subs = pysrt.open(str(transcript_path))
    
    clip_srts = []
    for i, highlight in enumerate(highlights):
        try:
            # Parse timestamps
            start_time = parse_timestamp(highlight["start"])
            end_time = parse_timestamp(highlight["end"])
            
            print(f"Processing clip {i+1}/{len(highlights)}: {start_time} to {end_time}")
            
            # Filter subtitles within time range
            clip_subs = pysrt.SubRipFile()
            for sub in subs:
                # Convert pysrt.SubRipTime to timedelta for proper comparison
                sub_start_delta = time_to_timedelta(sub.start.to_time())
                sub_end_delta = time_to_timedelta(sub.end.to_time())
                
                # Check if subtitle overlaps with highlight
                if (start_time <= sub_end_delta and end_time >= sub_start_delta):
                    # Adjust timestamps to start at 00:00:00
                    new_start_delta = max(timedelta(0), sub_start_delta - start_time)
                    new_end_delta = min(end_time - start_time, sub_end_delta - start_time)
                    
                    # Create new subtitle with adjusted times
                    new_sub = pysrt.SubRipItem(
                        index=len(clip_subs) + 1,
                        start=pysrt.SubRipTime.from_string(format_timestamp(new_start_delta)),
                        end=pysrt.SubRipTime.from_string(format_timestamp(new_end_delta)),
                        text=sub.text
                    )
                    clip_subs.append(new_sub)
            
            # Output path for the clip SRT
            slug = highlight.get('slug', f"clip_{i:02d}")
            output_path = project_path / "clips" / f"{i:02d}_{slug}.srt"
            
            # Save clip SRT
            if clip_subs:
                clip_subs.save(str(output_path), encoding='utf-8')
                print(f"  ✓ Created SRT with {len(clip_subs)} subtitles: {output_path.name}")
                
                # Create matching TXT file
                txt_path = create_txt_from_srt(output_path)
                
            else:
                # Create empty SRT with at least one entry if no subtitles found
                empty_sub = pysrt.SubRipFile()
                empty_sub.append(pysrt.SubRipItem(
                    index=1,
                    start=pysrt.SubRipTime.from_string("00:00:00,000"),
                    end=pysrt.SubRipTime.from_string("00:00:05,000"),
                    text=highlight.get('hook', "Highlight from the lecture")
                ))
                empty_sub.save(str(output_path), encoding='utf-8')
                print(f"  ⚠️ No matching subtitles found. Created placeholder: {output_path.name}")
                
                # Create matching TXT file for placeholder
                txt_path = output_path.with_suffix('.txt')
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(highlight.get('hook', "Highlight from the lecture"))
                print(f"  ✓ Created text file: {txt_path.name}")
            
            clip_srts.append(output_path)
            
        except Exception as e:
            print(f"  ⚠️ Error processing clip {i+1}: {str(e)}")
            # Create a simple fallback SRT
            fallback_path = project_path / "clips" / f"{i:02d}_fallback.srt"
            with open(fallback_path, "w", encoding="utf-8") as f:
                f.write("1\n00:00:00,000 --> 00:00:05,000\n")
                f.write(highlight.get('hook', "Highlight from the lecture"))
            clip_srts.append(fallback_path)
            print(f"  ✓ Created fallback SRT: {fallback_path.name}")
            
            # Create matching TXT file for fallback
            txt_path = fallback_path.with_suffix('.txt')
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(highlight.get('hook', "Highlight from the lecture"))
            print(f"  ✓ Created text file: {txt_path.name}")
    
    return clip_srts 