#!/usr/bin/env python3
"""
Simple test for pause-based segmentation without external dependencies.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pause_based_segmentation import PauseBasedSegmenter

def create_mock_data():
    """Create realistic mock data for testing."""
    return {
        "segments": [
            {
                "start": 0.0,
                "end": 35.0,
                "text": "Today I want to talk about faith. When we face challenges, we must remember that everything happens for a reason. The Talmud teaches us that even in our darkest moments, there is light waiting to be discovered.",
                "words": [
                    {"word": "Today", "start": 0.0, "end": 0.5},
                    {"word": "I", "start": 0.6, "end": 0.7},
                    {"word": "want", "start": 0.8, "end": 1.1},
                    {"word": "to", "start": 1.2, "end": 1.3},
                    {"word": "talk", "start": 1.4, "end": 1.8},
                    {"word": "about", "start": 1.9, "end": 2.3},
                    {"word": "faith", "start": 2.4, "end": 3.0},
                    
                    # 1 second pause here
                    {"word": "When", "start": 4.0, "end": 4.3},
                    {"word": "we", "start": 4.4, "end": 4.5},
                    {"word": "face", "start": 4.6, "end": 5.0},
                    {"word": "challenges", "start": 5.1, "end": 5.8},
                    {"word": "we", "start": 6.4, "end": 6.6},  # 0.6s pause
                    {"word": "must", "start": 6.7, "end": 7.0},
                    {"word": "remember", "start": 7.1, "end": 7.7},
                    {"word": "that", "start": 7.8, "end": 8.0},
                    {"word": "everything", "start": 8.1, "end": 8.7},
                    {"word": "happens", "start": 8.8, "end": 9.3},
                    {"word": "for", "start": 9.4, "end": 9.6},
                    {"word": "a", "start": 9.7, "end": 9.8},
                    {"word": "reason", "start": 9.9, "end": 10.5},
                    
                    # 1.5 second pause here
                    {"word": "The", "start": 12.0, "end": 12.2},
                    {"word": "Talmud", "start": 12.3, "end": 12.8},
                    {"word": "teaches", "start": 12.9, "end": 13.4},
                    {"word": "us", "start": 13.5, "end": 13.7},
                    {"word": "that", "start": 13.8, "end": 14.0},
                    {"word": "even", "start": 14.1, "end": 14.4},
                    {"word": "in", "start": 14.5, "end": 14.6},
                    {"word": "our", "start": 14.7, "end": 14.9},
                    {"word": "darkest", "start": 15.0, "end": 15.6},
                    {"word": "moments", "start": 15.7, "end": 16.3},
                    {"word": "there", "start": 16.9, "end": 17.2},  # 0.6s pause
                    {"word": "is", "start": 17.3, "end": 17.5},
                    {"word": "light", "start": 17.6, "end": 18.0},
                    {"word": "waiting", "start": 18.1, "end": 18.6},
                    {"word": "to", "start": 18.7, "end": 18.8},
                    {"word": "be", "start": 18.9, "end": 19.1},
                    {"word": "discovered", "start": 19.2, "end": 20.0}
                ]
            }
        ]
    }

def test_segmentation():
    """Test the pause-based segmentation."""
    print("Testing Pause-Based Segmentation")
    print("=" * 40)
    
    # Create segmenter with more permissive settings for testing
    segmenter = PauseBasedSegmenter(
        min_pause_duration=0.5,    # 500ms minimum pause
        max_pause_duration=5.0,    # 5 second maximum pause
        min_segment_duration=8.0,  # 8 seconds minimum (reduced for testing)
        max_segment_duration=25.0, # 25 seconds maximum
        min_words_per_segment=5    # 5 words minimum (reduced for testing)
    )
    
    mock_data = create_mock_data()
    
    # Extract word timings
    word_timings = segmenter.extract_word_timings(mock_data)
    print(f"✓ Extracted {len(word_timings)} words")
    
    # Detect pauses
    pauses = segmenter.detect_pauses(word_timings)
    print(f"✓ Detected {len(pauses)} pauses:")
    for i, pause in enumerate(pauses, 1):
        print(f"    {i}. {pause.start:.1f}s → {pause.end:.1f}s ({pause.duration:.1f}s)")
    
    # Create segments
    segments = segmenter.segment_transcript(mock_data)
    print(f"\n✓ Created {len(segments)} natural segments:")
    
    for i, segment in enumerate(segments, 1):
        print(f"\n  Segment {i}:")
        print(f"    Time: {segment.start:.1f}s → {segment.end:.1f}s ({segment.duration:.1f}s)")
        print(f"    Words: {segment.word_count}")
        print(f"    Text: {segment.text}")
    
    # Test the conversion to dict format
    segments_dict = segmenter.segments_to_dict(segments)
    print(f"\n✓ Converted to {len(segments_dict)} dictionary segments")
    
    return segments

if __name__ == "__main__":
    segments = test_segmentation()
    
    if segments:
        print(f"\n🎉 Success! Created {len(segments)} natural segments")
    else:
        print("\n⚠️  No segments created - check parameters")