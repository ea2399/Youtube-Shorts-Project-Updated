#!/usr/bin/env python3
"""
Convert existing SRT to mock WhisperX JSON format for testing pause-based segmentation.
"""

import json
import re
from pathlib import Path

def parse_srt_time(time_str):
    """Convert SRT timestamp to seconds."""
    # Format: HH:MM:SS,mmm
    hours, minutes, seconds = time_str.split(':')
    seconds, milliseconds = seconds.split(',')
    
    total_seconds = (
        int(hours) * 3600 + 
        int(minutes) * 60 + 
        int(seconds) + 
        int(milliseconds) / 1000
    )
    return total_seconds

def estimate_word_timings(text, start_time, end_time):
    """Estimate word-level timings within a segment."""
    words = text.split()
    if not words:
        return []
    
    duration = end_time - start_time
    word_duration = duration / len(words)
    
    word_timings = []
    current_time = start_time
    
    for word in words:
        word_end = current_time + word_duration
        word_timings.append({
            "word": word,
            "start": current_time,
            "end": word_end
        })
        current_time = word_end
    
    return word_timings

def convert_srt_to_whisperx_json(srt_path, output_path):
    """Convert SRT file to WhisperX-like JSON format."""
    
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse SRT entries
    entries = []
    blocks = content.strip().split('\n\n')
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            # Skip the subtitle number (first line)
            time_line = lines[1]
            text_lines = lines[2:]
            text = ' '.join(text_lines)
            
            # Parse time range
            if ' --> ' in time_line:
                start_str, end_str = time_line.split(' --> ')
                start_time = parse_srt_time(start_str)
                end_time = parse_srt_time(end_str)
                
                # Estimate word timings
                word_timings = estimate_word_timings(text, start_time, end_time)
                
                entries.append({
                    "start": start_time,
                    "end": end_time,
                    "text": text,
                    "words": word_timings
                })
    
    # Create WhisperX-like structure
    whisperx_data = {
        "segments": entries,
        "language": "en"  # Mixed Hebrew/English, but mostly English in this section
    }
    
    # Save to JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(whisperx_data, f, indent=2, ensure_ascii=False)
    
    print(f"Converted {len(entries)} SRT entries to WhisperX JSON format")
    print(f"Saved to: {output_path}")
    
    return whisperx_data

def create_realistic_test_data():
    """Create more realistic test data with natural pauses."""
    
    # Create a mock transcript with realistic Torah lecture content and timing
    segments = [
        {
            "start": 0.0,
            "end": 8.5,
            "text": "So we're speaking about the names of God. Now this is a big topic.",
            "words": [
                {"word": "So", "start": 0.0, "end": 0.3},
                {"word": "we're", "start": 0.4, "end": 0.7},
                {"word": "speaking", "start": 0.8, "end": 1.3},
                {"word": "about", "start": 1.4, "end": 1.7},
                {"word": "the", "start": 1.8, "end": 2.0},
                {"word": "names", "start": 2.1, "end": 2.5},
                {"word": "of", "start": 2.6, "end": 2.7},
                {"word": "God", "start": 2.8, "end": 3.2},
                # Natural pause here (1.3 seconds)
                {"word": "Now", "start": 4.5, "end": 4.8},
                {"word": "this", "start": 4.9, "end": 5.1},
                {"word": "is", "start": 5.2, "end": 5.4},
                {"word": "a", "start": 5.5, "end": 5.6},
                {"word": "big", "start": 5.7, "end": 6.0},
                {"word": "topic", "start": 6.1, "end": 6.5}
            ]
        },
        {
            "start": 8.5,
            "end": 18.0,
            "text": "Because essentially we're saying that if we understand how to use God's names, we can move the entire system.",
            "words": [
                {"word": "Because", "start": 8.5, "end": 9.0},
                {"word": "essentially", "start": 9.1, "end": 9.8},
                {"word": "we're", "start": 9.9, "end": 10.2},
                {"word": "saying", "start": 10.3, "end": 10.7},
                {"word": "that", "start": 10.8, "end": 11.0},
                {"word": "if", "start": 11.1, "end": 11.3},
                {"word": "we", "start": 11.4, "end": 11.5},
                {"word": "understand", "start": 11.6, "end": 12.3},
                # Short pause (0.7s)
                {"word": "how", "start": 13.0, "end": 13.2},
                {"word": "to", "start": 13.3, "end": 13.4},
                {"word": "use", "start": 13.5, "end": 13.8},
                {"word": "God's", "start": 13.9, "end": 14.3},
                {"word": "names", "start": 14.4, "end": 14.8},
                {"word": "we", "start": 15.4, "end": 15.6},  # 0.6s pause
                {"word": "can", "start": 15.7, "end": 15.9},
                {"word": "move", "start": 16.0, "end": 16.3},
                {"word": "the", "start": 16.4, "end": 16.5},
                {"word": "entire", "start": 16.6, "end": 17.1},
                {"word": "system", "start": 17.2, "end": 17.7}
            ]
        },
        {
            "start": 18.0,
            "end": 35.0,
            "text": "But it's not simple. It requires tremendous purity of thought, speech, and action. Every word must be precise, every intention must be pure.",
            "words": [
                {"word": "But", "start": 18.0, "end": 18.2},
                {"word": "it's", "start": 18.3, "end": 18.5},
                {"word": "not", "start": 18.6, "end": 18.8},
                {"word": "simple", "start": 18.9, "end": 19.4},
                # 1.1 second pause
                {"word": "It", "start": 20.5, "end": 20.7},
                {"word": "requires", "start": 20.8, "end": 21.4},
                {"word": "tremendous", "start": 21.5, "end": 22.3},
                {"word": "purity", "start": 22.4, "end": 22.9},
                {"word": "of", "start": 23.0, "end": 23.1},
                {"word": "thought", "start": 23.2, "end": 23.7},
                {"word": "speech", "start": 24.2, "end": 24.7},  # 0.5s pause
                {"word": "and", "start": 24.8, "end": 25.0},
                {"word": "action", "start": 25.1, "end": 25.6},
                # 0.8 second pause
                {"word": "Every", "start": 26.4, "end": 26.8},
                {"word": "word", "start": 26.9, "end": 27.2},
                {"word": "must", "start": 27.3, "end": 27.6},
                {"word": "be", "start": 27.7, "end": 27.9},
                {"word": "precise", "start": 28.0, "end": 28.6},
                {"word": "every", "start": 29.1, "end": 29.4},  # 0.5s pause
                {"word": "intention", "start": 29.5, "end": 30.2},
                {"word": "must", "start": 30.3, "end": 30.6},
                {"word": "be", "start": 30.7, "end": 30.9},
                {"word": "pure", "start": 31.0, "end": 31.4}
            ]
        }
    ]
    
    return {
        "segments": segments,
        "language": "en"
    }

if __name__ == "__main__":
    # Create realistic test data
    print("Creating realistic test data...")
    test_data = create_realistic_test_data()
    
    output_path = Path("/mnt/c/Users/User/Youtube short project/test_realistic_transcript.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Created realistic test transcript: {output_path}")
    
    # Also try to convert existing SRT if available
    srt_path = Path("/mnt/c/Users/User/Youtube short project/25-05-04_mjBqV8e1DRs/transcripts/full.srt")
    if srt_path.exists():
        print("\nConverting existing SRT file...")
        json_output = Path("/mnt/c/Users/User/Youtube short project/test_from_srt.json")
        convert_srt_to_whisperx_json(srt_path, json_output)
    else:
        print("No SRT file found to convert")