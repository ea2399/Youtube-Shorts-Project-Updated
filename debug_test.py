#!/usr/bin/env python3
"""
Debug test for pause-based segmentation.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pause_based_segmentation import PauseBasedSegmenter

def debug_segmentation():
    """Debug the segmentation process step by step."""
    
    # Simple mock data
    mock_data = {
        "segments": [
            {
                "start": 0.0,
                "end": 25.0,
                "text": "This is a test. After a pause, we continue talking about important topics. Finally we conclude with wisdom.",
                "words": [
                    {"word": "This", "start": 0.0, "end": 0.4},
                    {"word": "is", "start": 0.5, "end": 0.7},
                    {"word": "a", "start": 0.8, "end": 0.9},
                    {"word": "test", "start": 1.0, "end": 1.4},
                    
                    # 1 second pause here
                    {"word": "After", "start": 2.5, "end": 2.9},
                    {"word": "a", "start": 3.0, "end": 3.1},
                    {"word": "pause", "start": 3.2, "end": 3.6},
                    {"word": "we", "start": 3.7, "end": 3.8},
                    {"word": "continue", "start": 3.9, "end": 4.5},
                    {"word": "talking", "start": 4.6, "end": 5.1},
                    {"word": "about", "start": 5.2, "end": 5.5},
                    {"word": "important", "start": 5.6, "end": 6.3},
                    {"word": "topics", "start": 6.4, "end": 6.9},
                    
                    # Another pause
                    {"word": "Finally", "start": 8.0, "end": 8.5},
                    {"word": "we", "start": 8.6, "end": 8.7},
                    {"word": "conclude", "start": 8.8, "end": 9.4},
                    {"word": "with", "start": 9.5, "end": 9.7},
                    {"word": "wisdom", "start": 9.8, "end": 10.3},
                ]
            }
        ]
    }
    
    # Very permissive settings for testing
    segmenter = PauseBasedSegmenter(
        min_pause_duration=0.5,
        max_pause_duration=5.0,
        min_segment_duration=3.0,  # Very short for testing
        max_segment_duration=15.0,
        min_words_per_segment=3    # Very few words for testing
    )
    
    print("Debug: Extracting word timings...")
    word_timings = segmenter.extract_word_timings(mock_data)
    print(f"Words: {len(word_timings)}")
    for i, word in enumerate(word_timings):
        print(f"  {i}: '{word.word}' {word.start:.1f}s-{word.end:.1f}s")
    
    print("\nDebug: Detecting pauses...")
    pauses = segmenter.detect_pauses(word_timings)
    print(f"Pauses: {len(pauses)}")
    for i, pause in enumerate(pauses):
        print(f"  {i}: {pause.start:.1f}s-{pause.end:.1f}s ({pause.duration:.1f}s)")
    
    print("\nDebug: Creating segments...")
    segments = segmenter.create_natural_segments(word_timings, pauses)
    
    print(f"Raw segments created: {len(segments)}")
    for i, segment in enumerate(segments):
        print(f"  {i}: {segment.start:.1f}s-{segment.end:.1f}s ({segment.duration:.1f}s) - {segment.word_count} words")
        print(f"      Text: {segment.text}")
        print(f"      Viable: {segmenter._is_viable_segment(segment)}")
    
    print("\nDebug: Merging short segments...")
    final_segments = segmenter.merge_short_segments(segments)
    print(f"Final segments: {len(final_segments)}")
    
    return final_segments

if __name__ == "__main__":
    segments = debug_segmentation()