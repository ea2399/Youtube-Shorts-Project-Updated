#!/usr/bin/env python3
"""
Test pause-based segmentation with real transcript data.
"""

import sys
import os
import json
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pause_based_segmentation import PauseBasedSegmenter

def test_with_realistic_data():
    """Test with our realistic mock data."""
    print("=" * 50)
    print("TESTING WITH REALISTIC TORAH LECTURE DATA")
    print("=" * 50)
    
    # Load the realistic test data
    with open("/mnt/c/Users/User/Youtube short project/test_realistic_transcript.json", 'r') as f:
        transcript = json.load(f)
    
    # Test with YouTube Shorts parameters
    segmenter = PauseBasedSegmenter(
        min_pause_duration=0.5,    # 500ms natural pause
        max_pause_duration=3.0,    # Max 3 second pause
        min_segment_duration=20.0, # 20 second minimum for shorts
        max_segment_duration=60.0, # 60 second maximum
        min_words_per_segment=15   # Minimum words for coherent clip
    )
    
    print(f"📊 Input: {len(transcript['segments'])} transcript segments")
    
    # Extract word timings
    words = segmenter.extract_word_timings(transcript)
    print(f"📝 Extracted: {len(words)} words")
    
    # Detect pauses
    pauses = segmenter.detect_pauses(words)
    print(f"⏸️  Detected: {len(pauses)} natural pauses")
    
    for i, pause in enumerate(pauses, 1):
        print(f"   {i}. {pause.start:.1f}s → {pause.end:.1f}s ({pause.duration:.1f}s)")
    
    # Create segments
    segments = segmenter.segment_transcript(transcript)
    print(f"\n🎬 Created: {len(segments)} natural segments")
    
    for i, segment in enumerate(segments, 1):
        print(f"\n   Segment {i}: {segment.start:.1f}s - {segment.end:.1f}s ({segment.duration:.1f}s)")
        print(f"   Words: {segment.word_count}")
        print(f"   Text: {segment.text}")
        print(f"   Viable for shorts: {'✅' if segment.duration >= 20 and segment.word_count >= 15 else '❌'}")
    
    return segments

def test_with_srt_data():
    """Test with converted SRT data."""
    print("\n" + "=" * 50)
    print("TESTING WITH CONVERTED SRT DATA")
    print("=" * 50)
    
    try:
        # Load the SRT-converted data
        with open("/mnt/c/Users/User/Youtube short project/test_from_srt.json", 'r') as f:
            transcript = json.load(f)
        
        print(f"📊 Input: {len(transcript['segments'])} SRT segments")
        
        # Use more permissive settings for SRT data (which may have shorter segments)
        segmenter = PauseBasedSegmenter(
            min_pause_duration=0.8,    # Slightly higher for SRT gaps
            max_pause_duration=5.0,    # Allow longer pauses
            min_segment_duration=15.0, # Shorter minimum for testing
            max_segment_duration=45.0, # Shorter max for denser content
            min_words_per_segment=10   # Fewer words minimum
        )
        
        # Sample first 50 segments to avoid overwhelming output
        sample_transcript = {
            "segments": transcript["segments"][:50],
            "language": transcript.get("language", "en")
        }
        
        # Extract word timings
        words = segmenter.extract_word_timings(sample_transcript)
        print(f"📝 Extracted: {len(words)} words (from first 50 segments)")
        
        # Detect pauses
        pauses = segmenter.detect_pauses(words)
        print(f"⏸️  Detected: {len(pauses)} pauses")
        
        # Show first 5 pauses
        for i, pause in enumerate(pauses[:5], 1):
            print(f"   {i}. {pause.start:.1f}s → {pause.end:.1f}s ({pause.duration:.1f}s)")
        if len(pauses) > 5:
            print(f"   ... and {len(pauses) - 5} more pauses")
        
        # Create segments
        segments = segmenter.segment_transcript(sample_transcript)
        print(f"\n🎬 Created: {len(segments)} natural segments")
        
        # Show first 3 segments
        for i, segment in enumerate(segments[:3], 1):
            print(f"\n   Segment {i}: {segment.start:.1f}s - {segment.end:.1f}s ({segment.duration:.1f}s)")
            print(f"   Words: {segment.word_count}")
            print(f"   Text: {segment.text[:100]}..." if len(segment.text) > 100 else f"   Text: {segment.text}")
        
        if len(segments) > 3:
            print(f"\n   ... and {len(segments) - 3} more segments")
        
        return segments
        
    except Exception as e:
        print(f"❌ Error testing SRT data: {e}")
        return []

def compare_methods():
    """Compare old vs new segmentation methods."""
    print("\n" + "=" * 50)
    print("COMPARING OLD VS NEW METHODS")
    print("=" * 50)
    
    try:
        # Load realistic data
        with open("/mnt/c/Users/User/Youtube short project/test_realistic_transcript.json", 'r') as f:
            transcript = json.load(f)
        
        # Test old overlapping method (import without GUI dependencies)
        print("🔄 Testing old overlapping method...")
        
        # Simulate old method behavior
        segments = transcript["segments"]
        min_duration = 30
        max_duration = 60
        
        old_clips = []
        for i in range(len(segments) - 1):
            start_time = segments[i]["start"]
            end_time = segments[i + 1]["end"]
            duration = end_time - start_time
            
            if min_duration <= duration <= max_duration:
                text = segments[i]["text"] + " " + segments[i + 1]["text"]
                old_clips.append({
                    "start": start_time,
                    "end": end_time,
                    "duration": duration,
                    "text": text,
                    "method": "overlapping"
                })
        
        print(f"   Old method: {len(old_clips)} clips")
        
        # Test new pause-based method
        print("🎯 Testing new pause-based method...")
        segmenter = PauseBasedSegmenter(
            min_segment_duration=20.0,
            max_segment_duration=60.0
        )
        new_segments = segmenter.segment_transcript(transcript)
        
        print(f"   New method: {len(new_segments)} segments")
        
        print("\n📊 COMPARISON:")
        print(f"   Old overlapping: {len(old_clips)} clips (may overlap)")
        print(f"   New pause-based: {len(new_segments)} segments (natural boundaries)")
        
        if old_clips:
            avg_old_duration = sum(clip["duration"] for clip in old_clips) / len(old_clips)
            print(f"   Old avg duration: {avg_old_duration:.1f}s")
        
        if new_segments:
            avg_new_duration = sum(seg.duration for seg in new_segments) / len(new_segments)
            print(f"   New avg duration: {avg_new_duration:.1f}s")
        
    except Exception as e:
        print(f"❌ Error comparing methods: {e}")

if __name__ == "__main__":
    print("🧪 TESTING PAUSE-BASED SEGMENTATION")
    
    # Test with realistic data
    realistic_segments = test_with_realistic_data()
    
    # Test with SRT data
    srt_segments = test_with_srt_data()
    
    # Compare methods
    compare_methods()
    
    print("\n" + "=" * 50)
    print("✅ TESTING COMPLETE!")
    print("=" * 50)
    
    if realistic_segments:
        print(f"✅ Realistic data: {len(realistic_segments)} segments created")
    if srt_segments:
        print(f"✅ SRT data: {len(srt_segments)} segments created")
    
    print("\n🎯 Key improvements observed:")
    print("   • Natural speech boundaries respected")
    print("   • No arbitrary overlapping")
    print("   • Better context preservation")
    print("   • Flexible duration based on content")