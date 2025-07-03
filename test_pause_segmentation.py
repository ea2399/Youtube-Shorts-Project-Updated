#!/usr/bin/env python3
"""
Test script for the new pause-based segmentation functionality.

This script creates mock WhisperX data to test the pause detection and segmentation logic.
"""

import json
from pathlib import Path
from pause_based_segmentation import PauseBasedSegmenter

def create_mock_whisperx_data():
    """Create mock WhisperX data with realistic word timing for testing."""
    return {
        "segments": [
            {
                "start": 0.0,
                "end": 12.5,
                "text": "Today I want to talk about faith and trust in difficult times",
                "words": [
                    {"word": "Today", "start": 0.0, "end": 0.5},
                    {"word": "I", "start": 0.6, "end": 0.7},
                    {"word": "want", "start": 0.8, "end": 1.1},
                    {"word": "to", "start": 1.2, "end": 1.3},
                    {"word": "talk", "start": 1.4, "end": 1.8},
                    {"word": "about", "start": 1.9, "end": 2.3},
                    {"word": "faith", "start": 2.4, "end": 2.8},
                    {"word": "and", "start": 3.5, "end": 3.7},  # 0.7s pause before "and"
                    {"word": "trust", "start": 3.8, "end": 4.2},
                    {"word": "in", "start": 4.3, "end": 4.4},
                    {"word": "difficult", "start": 4.5, "end": 5.1},
                    {"word": "times", "start": 5.2, "end": 5.8}
                ]
            },
            {
                "start": 12.5,
                "end": 25.0,
                "text": "When we face challenges we must remember that everything happens for a reason",
                "words": [
                    {"word": "When", "start": 12.5, "end": 12.8},
                    {"word": "we", "start": 12.9, "end": 13.0},
                    {"word": "face", "start": 13.1, "end": 13.5},
                    {"word": "challenges", "start": 13.6, "end": 14.4},
                    # Long pause here (1.1 seconds)
                    {"word": "we", "start": 15.5, "end": 15.7},
                    {"word": "must", "start": 15.8, "end": 16.1},
                    {"word": "remember", "start": 16.2, "end": 16.9},
                    {"word": "that", "start": 17.0, "end": 17.2},
                    {"word": "everything", "start": 17.3, "end": 18.0},
                    {"word": "happens", "start": 18.1, "end": 18.6},
                    {"word": "for", "start": 18.7, "end": 18.9},
                    {"word": "a", "start": 19.0, "end": 19.1},
                    {"word": "reason", "start": 19.2, "end": 19.8}
                ]
            },
            {
                "start": 25.0,
                "end": 45.0,
                "text": "The Talmud teaches us that even in our darkest moments there is light waiting to be discovered",
                "words": [
                    {"word": "The", "start": 25.0, "end": 25.2},
                    {"word": "Talmud", "start": 25.3, "end": 25.8},
                    {"word": "teaches", "start": 25.9, "end": 26.4},
                    {"word": "us", "start": 26.5, "end": 26.7},
                    {"word": "that", "start": 26.8, "end": 27.0},
                    {"word": "even", "start": 27.1, "end": 27.4},
                    {"word": "in", "start": 27.5, "end": 27.6},
                    {"word": "our", "start": 27.7, "end": 27.9},
                    {"word": "darkest", "start": 28.0, "end": 28.6},
                    {"word": "moments", "start": 28.7, "end": 29.3},
                    # Medium pause here (0.8 seconds)
                    {"word": "there", "start": 30.1, "end": 30.4},
                    {"word": "is", "start": 30.5, "end": 30.7},
                    {"word": "light", "start": 30.8, "end": 31.2},
                    {"word": "waiting", "start": 31.3, "end": 31.8},
                    {"word": "to", "start": 31.9, "end": 32.0},
                    {"word": "be", "start": 32.1, "end": 32.3},
                    {"word": "discovered", "start": 32.4, "end": 33.2}
                ]
            }
        ]
    }

def test_pause_detection():
    """Test the pause detection functionality."""
    print("=== Testing Pause Detection ===")
    
    # Create mock data
    mock_data = create_mock_whisperx_data()
    
    # Initialize segmenter
    segmenter = PauseBasedSegmenter(
        min_pause_duration=0.5,
        max_pause_duration=3.0,
        min_segment_duration=15.0,
        max_segment_duration=60.0,
        min_words_per_segment=8
    )
    
    # Extract word timings
    word_timings = segmenter.extract_word_timings(mock_data)
    print(f"Extracted {len(word_timings)} words")
    
    # Detect pauses
    pauses = segmenter.detect_pauses(word_timings)
    print(f"Detected {len(pauses)} pauses:")
    
    for i, pause in enumerate(pauses, 1):
        print(f"  {i}. {pause.start:.1f}s - {pause.end:.1f}s ({pause.duration:.1f}s)")
    
    # Create segments
    segments = segmenter.segment_transcript(mock_data)
    print(f"\nCreated {len(segments)} natural segments:")
    
    for i, segment in enumerate(segments, 1):
        print(f"\n{i}. Duration: {segment.duration:.1f}s ({segment.start:.1f}s - {segment.end:.1f}s)")
        print(f"   Words: {segment.word_count}")
        print(f"   Text: {segment.text[:80]}..." if len(segment.text) > 80 else f"   Text: {segment.text}")
    
    return segments

def test_with_extract_shorts():
    """Test integration with extract_shorts.py functionality."""
    print("\n=== Testing Integration with extract_shorts.py ===")
    
    # Import the new function
    from extract_shorts import create_pause_based_segments
    
    mock_data = create_mock_whisperx_data()
    
    # Test the new function
    potential_clips = create_pause_based_segments(
        transcript=mock_data,
        min_duration=15,
        max_duration=60
    )
    
    print(f"Created {len(potential_clips)} potential clips:")
    
    for i, clip in enumerate(potential_clips, 1):
        print(f"\n{i}. Duration: {clip['duration']:.1f}s")
        print(f"   Method: {clip.get('segmentation_method', 'unknown')}")
        print(f"   Words: {clip.get('word_count', 'N/A')}")
        print(f"   Text: {clip['text'][:80]}..." if len(clip['text']) > 80 else f"   Text: {clip['text']}")

def create_test_json_file():
    """Create a test JSON file for manual testing."""
    print("\n=== Creating Test JSON File ===")
    
    mock_data = create_mock_whisperx_data()
    test_file_path = Path("test_transcript.json")
    
    with open(test_file_path, 'w', encoding='utf-8') as f:
        json.dump(mock_data, f, indent=2, ensure_ascii=False)
    
    print(f"Created test file: {test_file_path}")
    print("You can now test with: python extract_shorts.py test_transcript.json")

if __name__ == "__main__":
    print("Testing Pause-Based Segmentation\n")
    
    # Run tests
    segments = test_pause_detection()
    test_with_extract_shorts()
    create_test_json_file()
    
    print("\n✅ All tests completed successfully!")
    print("\nTo test with real data:")
    print("1. Run transcribe.py on a video to create WhisperX JSON")
    print("2. Run extract_shorts.py (it will use pause-based segmentation by default)")
    print("3. Compare results with the old method using --use_overlapping flag")