"""
Pause-based segmentation for creating natural speech segments from WhisperX word-level timing data.

This module analyzes word-level timing data to identify natural speech breaks and create
segments that respect the natural flow of speech, eliminating arbitrary overlapping segments.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

@dataclass
class WordTiming:
    """Represents a single word with its timing information."""
    word: str
    start: float
    end: float
    
@dataclass
class SpeechPause:
    """Represents a pause in speech."""
    start: float
    end: float
    duration: float
    
@dataclass
class NaturalSegment:
    """Represents a natural speech segment bounded by pauses."""
    words: List[WordTiming]
    text: str
    start: float
    end: float
    duration: float
    word_count: int

class PauseBasedSegmenter:
    """
    Creates natural speech segments based on pause detection from word-level timing.
    """
    
    def __init__(self, 
                 min_pause_duration: float = 0.5,
                 max_pause_duration: float = 3.0,
                 min_segment_duration: float = 20.0,
                 max_segment_duration: float = 90.0,
                 min_words_per_segment: int = 15):
        """
        Initialize the pause-based segmenter.
        
        Args:
            min_pause_duration: Minimum pause duration to consider as a segment boundary (seconds)
            max_pause_duration: Maximum pause duration to consider (longer pauses are treated as breaks)
            min_segment_duration: Minimum duration for a segment to be considered viable
            max_segment_duration: Maximum duration for a segment
            min_words_per_segment: Minimum number of words required for a viable segment
        """
        self.min_pause_duration = min_pause_duration
        self.max_pause_duration = max_pause_duration
        self.min_segment_duration = min_segment_duration
        self.max_segment_duration = max_segment_duration
        self.min_words_per_segment = min_words_per_segment
    
    def extract_word_timings(self, whisperx_data: Dict[str, Any]) -> List[WordTiming]:
        """
        Extract word-level timing data from WhisperX output.
        
        Args:
            whisperx_data: WhisperX JSON output containing segments with word-level timing
            
        Returns:
            List of WordTiming objects
        """
        word_timings = []
        
        for segment in whisperx_data.get("segments", []):
            # Handle both segment-level and word-level timing
            if "words" in segment:
                # Word-level timing available
                for word_data in segment["words"]:
                    # Skip malformed word entries
                    if not isinstance(word_data, dict):
                        continue
                    if not all(key in word_data for key in ["word", "start", "end"]):
                        continue
                    
                    try:
                        word_timings.append(WordTiming(
                            word=str(word_data["word"]),
                            start=float(word_data["start"]),
                            end=float(word_data["end"])
                        ))
                    except (TypeError, ValueError) as e:
                        # Skip word entries with invalid timing data
                        continue
            else:
                # Fall back to segment-level timing
                # Estimate word timing within the segment
                segment_text = segment["text"]
                words = segment_text.split()
                segment_duration = segment["end"] - segment["start"]
                word_duration = segment_duration / len(words) if words else 0
                
                for i, word in enumerate(words):
                    word_start = segment["start"] + (i * word_duration)
                    word_end = word_start + word_duration
                    word_timings.append(WordTiming(
                        word=word,
                        start=word_start,
                        end=word_end
                    ))
        
        return word_timings
    
    def detect_pauses(self, word_timings: List[WordTiming]) -> List[SpeechPause]:
        """
        Detect natural speech pauses between words.
        
        Args:
            word_timings: List of word timing data
            
        Returns:
            List of detected pauses
        """
        pauses = []
        
        for i in range(len(word_timings) - 1):
            current_word = word_timings[i]
            next_word = word_timings[i + 1]
            
            # Calculate gap between words
            gap_start = current_word.end
            gap_end = next_word.start
            gap_duration = gap_end - gap_start
            
            # Only consider gaps that meet our minimum pause duration
            if gap_duration >= self.min_pause_duration:
                pauses.append(SpeechPause(
                    start=gap_start,
                    end=gap_end,
                    duration=gap_duration
                ))
        
        return pauses
    
    def create_natural_segments(self, word_timings: List[WordTiming], pauses: List[SpeechPause]) -> List[NaturalSegment]:
        """
        Create natural speech segments based on detected pauses.
        
        Args:
            word_timings: List of word timing data
            pauses: List of detected pauses
            
        Returns:
            List of natural segments
        """
        if not word_timings:
            return []
        
        # If no pauses detected, create one segment from all words
        if not pauses:
            segment = self._create_segment_from_words(word_timings)
            if self._is_viable_segment(segment):
                return [segment]
            else:
                return []
        
        segments = []
        current_segment_words = []
        
        for i, word in enumerate(word_timings):
            current_segment_words.append(word)
            
            # Check if we should end the current segment
            should_end_segment = False
            
            # Check if there's a pause after this word
            for pause in pauses:
                if pause.duration <= self.max_pause_duration:
                    # Check if this word ends right before a pause starts
                    if abs(word.end - pause.start) < 0.2:  # Allow timing tolerance
                        should_end_segment = True
                        break
            
            # End segment if it's getting too long
            if current_segment_words:
                segment_duration = word.end - current_segment_words[0].start
                if segment_duration >= self.max_segment_duration:
                    should_end_segment = True
            
            # End segment at the last word
            if i == len(word_timings) - 1:
                should_end_segment = True
            
            if should_end_segment and current_segment_words:
                segment = self._create_segment_from_words(current_segment_words)
                # Always add segments, even if they're short - we'll merge them later
                segments.append(segment)
                current_segment_words = []
        
        return segments
    
    def _create_segment_from_words(self, words: List[WordTiming]) -> NaturalSegment:
        """Create a NaturalSegment from a list of words."""
        if not words:
            return None
        
        text = " ".join(word.word for word in words)
        start_time = words[0].start
        end_time = words[-1].end
        duration = end_time - start_time
        
        return NaturalSegment(
            words=words,
            text=text,
            start=start_time,
            end=end_time,
            duration=duration,
            word_count=len(words)
        )
    
    def _is_viable_segment(self, segment: NaturalSegment) -> bool:
        """Check if a segment meets the minimum requirements."""
        if not segment:
            return False
        
        return (segment.duration >= self.min_segment_duration and
                segment.word_count >= self.min_words_per_segment)
    
    def merge_short_segments(self, segments: List[NaturalSegment]) -> List[NaturalSegment]:
        """
        Merge segments that are too short with adjacent segments.
        
        Args:
            segments: List of natural segments
            
        Returns:
            List of merged segments
        """
        if not segments:
            return []
        
        merged = []
        current_words = []
        
        for segment in segments:
            if not current_words:
                current_words = segment.words.copy()
            else:
                # Check if we should merge with the current segment
                potential_segment = self._create_segment_from_words(current_words + segment.words)
                
                if potential_segment.duration <= self.max_segment_duration:
                    # Merge with current segment
                    current_words.extend(segment.words)
                else:
                    # Finalize current segment and start new one
                    merged_segment = self._create_segment_from_words(current_words)
                    if self._is_viable_segment(merged_segment):
                        merged.append(merged_segment)
                    current_words = segment.words.copy()
        
        # Don't forget the last segment
        if current_words:
            final_segment = self._create_segment_from_words(current_words)
            if self._is_viable_segment(final_segment):
                merged.append(final_segment)
        
        return merged
    
    def segment_transcript(self, whisperx_data: Dict[str, Any]) -> List[NaturalSegment]:
        """
        Main method to create natural segments from WhisperX transcript data.
        
        Args:
            whisperx_data: WhisperX JSON output
            
        Returns:
            List of natural speech segments
        """
        # Extract word-level timing
        word_timings = self.extract_word_timings(whisperx_data)
        
        if not word_timings:
            return []
        
        # Detect pauses
        pauses = self.detect_pauses(word_timings)
        
        # Create initial segments based on pauses
        segments = self.create_natural_segments(word_timings, pauses)
        
        # Merge segments that are too short
        final_segments = self.merge_short_segments(segments)
        
        return final_segments
    
    def segments_to_dict(self, segments: List[NaturalSegment]) -> List[Dict[str, Any]]:
        """
        Convert NaturalSegment objects to dictionary format for compatibility.
        
        Args:
            segments: List of NaturalSegment objects
            
        Returns:
            List of segment dictionaries
        """
        return [
            {
                "text": segment.text,
                "start": segment.start,
                "end": segment.end,
                "duration": segment.duration,
                "word_count": segment.word_count,
                "words": [
                    {
                        "word": word.word,
                        "start": word.start,
                        "end": word.end
                    }
                    for word in segment.words
                ]
            }
            for segment in segments
        ]

def load_whisperx_transcript(json_path: Path) -> Dict[str, Any]:
    """Load WhisperX transcript from JSON file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_natural_segments(segments: List[NaturalSegment], output_path: Path) -> None:
    """Save natural segments to JSON file."""
    segmenter = PauseBasedSegmenter()
    segments_dict = segmenter.segments_to_dict(segments)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "segments": segments_dict,
            "total_segments": len(segments_dict),
            "segmentation_method": "pause_based"
        }, f, indent=2, ensure_ascii=False)

# Example usage
if __name__ == "__main__":
    # Example with mock data (replace with actual WhisperX JSON)
    mock_whisperx_data = {
        "segments": [
            {
                "start": 0.0,
                "end": 5.0,
                "text": "This is a test transcript",
                "words": [
                    {"word": "This", "start": 0.0, "end": 0.5},
                    {"word": "is", "start": 0.6, "end": 0.8},
                    {"word": "a", "start": 0.9, "end": 1.0},
                    {"word": "test", "start": 1.5, "end": 2.0},  # 0.5 second pause here
                    {"word": "transcript", "start": 2.1, "end": 3.0}
                ]
            }
        ]
    }
    
    segmenter = PauseBasedSegmenter()
    segments = segmenter.segment_transcript(mock_whisperx_data)
    
    print(f"Created {len(segments)} natural segments:")
    for i, segment in enumerate(segments, 1):
        print(f"{i}. {segment.start:.1f}s - {segment.end:.1f}s ({segment.duration:.1f}s): {segment.text[:50]}...")