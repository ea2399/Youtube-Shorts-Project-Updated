from pathlib import Path
from typing import List

from pydub import AudioSegment

def split_audio(audio_path: Path, chunk_duration_minutes: int = 6, overlap_seconds: int = 5) -> List[Path]:
    """
    Split audio file into chunks for processing.
    
    Args:
        audio_path: Path to audio file
        chunk_duration_minutes: Duration of each chunk in minutes
        overlap_seconds: Overlap between chunks in seconds
        
    Returns:
        List of paths to chunk files
    """
    print(f"🔪 Splitting {audio_path.name} into chunks...")
    
    # Convert durations to milliseconds
    chunk_ms = chunk_duration_minutes * 60 * 1000
    overlap_ms = overlap_seconds * 1000
    
    # Load audio file
    audio = AudioSegment.from_file(audio_path)
    
    # Calculate step size (chunk size minus overlap)
    step = chunk_ms - overlap_ms
    
    # Create chunks directory
    chunks_dir = audio_path.parent / "chunks"
    chunks_dir.mkdir(exist_ok=True)
    
    # Split audio into chunks
    chunk_paths = []
    for i, start in enumerate(range(0, len(audio), step)):
        end = min(start + chunk_ms, len(audio))
        chunk_path = chunks_dir / f"{audio_path.stem}_chunk_{i:03d}.mp3"
        
        # Extract and save chunk
        chunk = audio[start:end]
        chunk.export(chunk_path, format="mp3")
        
        # Print progress
        start_min = start / 60000
        end_min = end / 60000
        print(f"   • {chunk_path.name} ({start_min:.1f}–{end_min:.1f} min)")
        
        chunk_paths.append(chunk_path)
    
    print(f"✓ Split into {len(chunk_paths)} chunks")
    return chunk_paths 