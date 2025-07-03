import json
import re
import gc
import torch
import os
from pathlib import Path
from typing import List, Optional, Dict, Any

import whisperx
from config import DEFAULT_LANGUAGE, OPENAI_API_KEY

# Available model sizes from smallest to largest
AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large-v2"]
DEFAULT_MODEL = "small"  # Changed from large-v2 to small

def format_timestamp(seconds: float) -> str:
    """Format seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    msecs = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{msecs:03d}"

def convert_segments_to_srt(segments: List[Dict[str, Any]]) -> str:
    """
    Convert WhisperX segments to SRT format.
    
    Args:
        segments: List of segments with start, end times and text
        
    Returns:
        SRT formatted string
    """
    srt_lines = []
    for i, segment in enumerate(segments, 1):
        start = format_timestamp(segment["start"])
        end = format_timestamp(segment["end"])
        
        srt_lines.append(str(i))
        srt_lines.append(f"{start} --> {end}")
        srt_lines.append(segment["text"])
        srt_lines.append("")  # Empty line between subtitle blocks
    
    return "\n".join(srt_lines)

def select_video_file() -> Optional[Path]:
    """
    Stub function for CLI usage - GUI dialogs not available in RunPod.
    
    Returns:
        None (CLI usage should provide video path directly)
    """
    print("Error: GUI file selection not available in RunPod environment")
    print("Please provide video_path directly to the transcribe function")
    return None

def select_project_directory() -> Optional[Path]:
    """
    Stub function for CLI usage - GUI dialogs not available in RunPod.
    
    Returns:
        None (CLI usage should provide project_path directly)
    """
    print("Error: GUI directory selection not available in RunPod environment")
    print("Please provide project_path directly to the transcribe function")
    return None

def select_model_size() -> str:
    """
    Return default model size for CLI usage - GUI dialogs not available in RunPod.
    
    Returns:
        Default model size
    """
    print(f"Using default model size: {DEFAULT_MODEL}")
    if torch.cuda.is_available():
        print("GPU detected: You can use larger models if needed")
    else:
        print("CPU mode: Recommended to use 'tiny', 'base', or 'small'")
    
    return DEFAULT_MODEL

def transcribe_with_whisperx(video_path: Path, project_path: Path, model_size: str = DEFAULT_MODEL, language: str = DEFAULT_LANGUAGE) -> Path:
    """
    Transcribe video using WhisperX for accurate word-level timestamps.
    
    Args:
        video_path: Path to video file
        project_path: Path to project directory
        model_size: WhisperX model size to use
        language: Language code (default: Hebrew)
        
    Returns:
        Path to transcript file in SRT format
    """
    # Prepare output paths
    output_srt_path = project_path / "transcripts" / "full.srt"
    output_json_path = project_path / "transcripts" / "full.json"
    
    try:
        # Determine device (CUDA if available, otherwise CPU)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Adjust compute type and batch size based on model size and device
        if device == "cuda":
            compute_type = "float16"
            batch_size = 16 if model_size in ["tiny", "base", "small"] else 8
        else:
            compute_type = "int8"
            # Reduce batch size on CPU for larger models to save memory
            if model_size in ["tiny", "base"]:
                batch_size = 8
            elif model_size == "small":
                batch_size = 4
            else:
                batch_size = 1  # Very small batch for medium/large on CPU
        
        print("Starting transcription with WhisperX...")
        print(f"Using device: {device}, model: {model_size}, compute type: {compute_type}, batch size: {batch_size}")
        print("This may take a few minutes depending on video length.")
        
        # 1. Load audio
        audio = whisperx.load_audio(str(video_path))
        
        # 2. Load WhisperX model
        print("Loading WhisperX model...")
        model = whisperx.load_model(model_size, device, compute_type=compute_type)
        
        # 3. Transcribe with batch processing
        print("Transcribing audio...")
        result = model.transcribe(audio, batch_size=batch_size, language=language)
        
        # Free up GPU memory after transcription
        del model
        gc.collect()
        torch.cuda.empty_cache() if device == "cuda" else None
        
        # 4. Align word-level timestamps
        print("Aligning for word-level timestamps...")
        model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
        result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)
        
        # Free up more GPU memory
        del model_a
        gc.collect()
        torch.cuda.empty_cache() if device == "cuda" else None
        
        # 5. Save JSON with detailed timestamps (for processing)
        print("Saving JSON transcript with detailed timestamps...")
        os.makedirs(output_json_path.parent, exist_ok=True)
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # 6. Convert to SRT format and save
        print("Generating SRT format...")
        srt_content = convert_segments_to_srt(result["segments"])
        
        with open(output_srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)
        
        # Count subtitle entries
        entry_count = len(result["segments"])
        print(f"✓ Transcription complete! ({entry_count} subtitle entries)")
        print(f"✓ Word-level timestamps saved to {output_json_path}")
        
        return output_srt_path
    
    except Exception as e:
        # More detailed error message
        error_message = str(e)
        if "memory" in error_message.lower():
            error_message += "\n\nTIP: Try using a smaller model size, such as 'tiny' or 'base'"
        raise RuntimeError(f"Failed to transcribe video: {error_message}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Transcribe video using WhisperX")
    parser.add_argument("video_path", nargs="?", help="Path to video file", default=None)
    parser.add_argument("project_path", nargs="?", help="Path to project directory", default=None)
    parser.add_argument("--language", help=f"Language code (default: {DEFAULT_LANGUAGE})", default=DEFAULT_LANGUAGE)
    parser.add_argument("--model", help=f"WhisperX model size (default: {DEFAULT_MODEL})", 
                      choices=AVAILABLE_MODELS, default=None)
    
    args = parser.parse_args()
    
    # Prompt for video file if not provided
    video_path = Path(args.video_path) if args.video_path else select_video_file()
    if not video_path:
        print("No video file selected. Exiting.")
        return
    
    if not video_path.exists():
        print(f"Video file not found: {video_path}")
        return
    
    # Prompt for project directory if not provided
    project_path = Path(args.project_path) if args.project_path else select_project_directory()
    if not project_path:
        # Use video path's parent directory as default
        project_path = video_path.parent
        print(f"Using video directory as project directory: {project_path}")
    
    # Create project directory if it doesn't exist
    project_path.mkdir(exist_ok=True, parents=True)
    
    # Ensure transcripts directory exists
    transcripts_dir = project_path / "transcripts"
    transcripts_dir.mkdir(exist_ok=True, parents=True)
    
    # Prompt for model size if not provided
    model_size = args.model if args.model else select_model_size()
    
    # Transcribe the video
    try:
        output_path = transcribe_with_whisperx(video_path, project_path, model_size, args.language)
        print(f"\nTranscription saved to: {output_path}")
        print(f"JSON data saved to: {project_path / 'transcripts' / 'full.json'}")
        
        # Display next steps
        print("\nNext steps:")
        print("1. Run extract_shorts.py to find potential short clips")
        print("2. Run cut_clips.py to extract the selected clips")
    except Exception as e:
        print(f"Error: {str(e)}")

# For backward compatibility, rename the function
transcribe_video = transcribe_with_whisperx

if __name__ == "__main__":
    main() 