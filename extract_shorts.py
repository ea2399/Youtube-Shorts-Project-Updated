import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import openai
from config import OPENAI_API_KEY, OPENAI_MODEL, MIN_CLIP_DURATION, MAX_CLIP_DURATION
from pause_based_segmentation import PauseBasedSegmenter
from context_aware_prompting import ContextAwareEvaluator, create_multi_pass_analysis

# Optional tkinter import for GUI file dialogs (only needed for local use)
try:
    import tkinter as tk
    from tkinter import filedialog
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False

def select_transcript_file() -> Optional[Path]:
    """
    Prompt the user to select a transcript file using a file dialog.
    
    Returns:
        Path to the selected transcript file, or None if cancelled
    """
    if not TKINTER_AVAILABLE:
        raise RuntimeError("GUI file selection not available in serverless environment. Please provide file path directly.")
    
    # Hide the main tkinter window
    root = tk.Tk()
    root.withdraw()
    
    # Show the file dialog
    file_path = filedialog.askopenfilename(
        title="Select Transcript JSON File",
        filetypes=[
            ("JSON Files", "*.json"),
            ("All Files", "*.*")
        ]
    )
    
    # Return the selected file path, or None if cancelled
    return Path(file_path) if file_path else None

def select_output_file(suggested_name: str = "potential_shorts.json") -> Optional[Path]:
    """
    Prompt the user to select an output file using a file dialog.
    
    Args:
        suggested_name: Suggested filename
    
    Returns:
        Path to the selected output file, or None if cancelled
    """
    if not TKINTER_AVAILABLE:
        raise RuntimeError("GUI file selection not available in serverless environment. Please provide file path directly.")
    
    # Hide the main tkinter window
    root = tk.Tk()
    root.withdraw()
    
    # Show the file dialog
    file_path = filedialog.asksaveasfilename(
        title="Save Potential Shorts",
        defaultextension=".json",
        initialfile=suggested_name,
        filetypes=[
            ("JSON Files", "*.json"),
            ("All Files", "*.*")
        ]
    )
    
    # Return the selected file path, or None if cancelled
    return Path(file_path) if file_path else None

def load_transcript(json_path: Path) -> Dict[str, Any]:
    """Load the WhisperX JSON transcript."""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def format_time(seconds: float) -> str:
    """Format seconds to HH:MM:SS.mmm format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    msecs = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{msecs:03d}"

def seconds_to_time_range(start: float, end: float) -> str:
    """Convert start and end seconds to formatted time range."""
    return f"{format_time(start)} - {format_time(end)}"

def create_pause_based_segments(transcript: Dict[str, Any], 
                                min_duration: int = MIN_CLIP_DURATION, 
                                max_duration: int = MAX_CLIP_DURATION) -> List[Dict[str, Any]]:
    """
    Create natural segments from the transcript based on speech pauses.
    
    Args:
        transcript: WhisperX transcript with segments and word-level timing
        min_duration: Minimum duration in seconds
        max_duration: Maximum duration in seconds
        
    Returns:
        List of natural segment groups with start, end, and text
    """
    # Initialize the pause-based segmenter with custom parameters
    segmenter = PauseBasedSegmenter(
        min_pause_duration=0.5,  # 500ms minimum pause
        max_pause_duration=3.0,  # 3 second maximum pause
        min_segment_duration=min_duration,
        max_segment_duration=max_duration,
        min_words_per_segment=10  # Reduced for shorter clips
    )
    
    # Create natural segments
    natural_segments = segmenter.segment_transcript(transcript)
    
    # Convert to the expected format for compatibility
    potential_clips = []
    for segment in natural_segments:
        potential_clips.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text,
            "duration": segment.duration,
            "word_count": segment.word_count,
            "segmentation_method": "pause_based"
        })
    
    return potential_clips

def create_overlapping_segments(transcript: Dict[str, Any], 
                                min_duration: int = MIN_CLIP_DURATION, 
                                max_duration: int = MAX_CLIP_DURATION,
                                overlap_percentage: float = 0.5) -> List[Dict[str, Any]]:
    """
    DEPRECATED: Create overlapping segments from the transcript.
    
    This function is kept for backward compatibility but is no longer recommended.
    Use create_pause_based_segments() instead for better results.
    """
    print("⚠️  Warning: Using deprecated overlapping segmentation. Consider using pause-based segmentation.")
    
    segments = transcript["segments"]
    if not segments:
        return []
    
    # Calculate overlap amount in seconds
    overlap_seconds = min_duration * overlap_percentage
    
    # Create potential clips
    potential_clips = []
    
    current_start_idx = 0
    while current_start_idx < len(segments):
        current_start_time = segments[current_start_idx]["start"]
        
        # Find the segment that would make this clip at least min_duration long
        current_end_idx = current_start_idx
        while (current_end_idx < len(segments) - 1 and 
               segments[current_end_idx]["end"] - current_start_time < min_duration):
            current_end_idx += 1
        
        # If we can't find a segment group that's at least min_duration long, break
        if segments[current_end_idx]["end"] - current_start_time < min_duration:
            break
        
        # Now extend until we hit max_duration
        while (current_end_idx < len(segments) - 1 and 
               segments[current_end_idx]["end"] - current_start_time < max_duration):
            current_end_idx += 1
        
        # If we exceeded max_duration with the last segment, back up one
        if segments[current_end_idx]["end"] - current_start_time > max_duration and current_end_idx > current_start_idx:
            current_end_idx -= 1
        
        clip_text = " ".join([segment["text"] for segment in segments[current_start_idx:current_end_idx+1]])
        
        potential_clips.append({
            "start": segments[current_start_idx]["start"],
            "end": segments[current_end_idx]["end"],
            "text": clip_text,
            "duration": segments[current_end_idx]["end"] - segments[current_start_idx]["start"],
            "segments": segments[current_start_idx:current_end_idx+1]
        })
        
        # Calculate the new start index based on overlap
        new_time = current_start_time + min_duration - overlap_seconds
        
        # Find the segment index for the new start time
        new_start_idx = current_start_idx
        while new_start_idx < len(segments) and segments[new_start_idx]["start"] < new_time:
            new_start_idx += 1
            
        # If we didn't advance at all, move to the next segment to avoid infinite loop
        if new_start_idx <= current_start_idx:
            current_start_idx += 1
        else:
            current_start_idx = new_start_idx

    return potential_clips

def evaluate_clip_with_gpt(clip: Dict[str, Any], client: openai.OpenAI) -> Dict[str, Any]:
    """
    Use GPT to evaluate if a clip would make a good YouTube short.
    
    Args:
        clip: Clip data with text and timing information
        client: OpenAI client
        
    Returns:
        Evaluation results with scores and metadata
    """
    time_range = seconds_to_time_range(clip["start"], clip["end"])
    
    prompt = f"""Evaluate this {clip['duration']:.1f} second clip from a Torah lecture for use as a YouTube short:

TRANSCRIPT: "{clip['text']}"

TIME RANGE: {time_range}

Rate this clip 1-10 on these dimensions:
- Inspirational value: [?/10]
- Humor: [?/10]
- Emotional impact: [?/10] 
- Information density: [?/10]
- Stand-alone quality (makes sense without context): [?/10]

Then answer these questions:
1. Would this clip work well as a YouTube short? (Yes/No/Maybe)
2. What makes this clip compelling or not compelling?
3. Suggest a catchy title for this clip (under 60 characters).
4. Suggest 2-3 tags that describe the content (e.g., "Emunah", "Teshuva", "Faith", "Life Advice").

IMPORTANT: Respond in JSON format exactly like this:
{{
  "inspirational": score,
  "humor": score,
  "emotional": score,
  "informational": score,
  "standalone": score,
  "overall_score": average_score,
  "recommended": "Yes/No/Maybe",
  "reasoning": "what makes this clip compelling or not...",
  "title": "suggested title",
  "tags": ["tag1", "tag2", "tag3"]
}}"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are an expert in evaluating Torah content for social media shorts."},
            {"role": "user", "content": prompt}
        ]
    )
    
    evaluation = json.loads(response.choices[0].message.content)
    
    # Add clip info to evaluation results
    evaluation["start"] = clip["start"]
    evaluation["end"] = clip["end"]
    evaluation["duration"] = clip["duration"]
    evaluation["text"] = clip["text"]
    evaluation["time_range"] = time_range
    
    return evaluation

def filter_top_clips(evaluations: List[Dict[str, Any]], top_n: int = 5, min_score: float = 6.5) -> List[Dict[str, Any]]:
    """
    Filter the top clips based on overall score (legacy method).
    
    Args:
        evaluations: List of clip evaluations
        top_n: Number of top clips to return
        min_score: Minimum overall score to consider
        
    Returns:
        List of top clips
    """
    # Filter clips with minimum score
    good_clips = [clip for clip in evaluations if clip["overall_score"] >= min_score]
    
    # Sort by overall score
    good_clips.sort(key=lambda x: x["overall_score"], reverse=True)
    
    # Return top N clips
    return good_clips[:top_n]

def filter_context_aware_clips(evaluations: List[Dict[str, Any]], top_n: int = 5, min_score: float = 6.0) -> List[Dict[str, Any]]:
    """
    Filter clips using context-aware criteria for better YouTube Shorts. Guarantees at least one clip is returned.

    Args:
        evaluations: List of context-aware clip evaluations
        top_n: Number of top clips to return
        min_score: Minimum overall score to consider

    Returns:
        List of top clips optimized for context and engagement
    """
    if not evaluations:
        return []

    # Calculate enhanced score for all clips
    for clip in evaluations:
        # Prioritize clips with low context dependency
        context_bonus = 0
        context_dep = clip.get("context_dependency", "Medium")
        if context_dep == "Low":
            context_bonus = 1.0
        elif context_dep == "Medium":
            context_bonus = 0.5

        # Bonus for standalone comprehensibility
        standalone_score = clip.get("standalone_comprehensibility", 5)
        standalone_bonus = max(0, (standalone_score - 7) * 0.3)  # Bonus for scores 8+

        # Bonus for narrative completeness
        narrative_score = clip.get("narrative_completeness", 5)
        narrative_bonus = max(0, (narrative_score - 7) * 0.2)

        # Hook quality is crucial for shorts
        hook_score = clip.get("hook_quality", 5)
        hook_bonus = max(0, (hook_score - 6) * 0.4)

        # Calculate enhanced score
        enhanced_score = (
            clip.get("overall_score", 0) + 
            context_bonus + 
            standalone_bonus + 
            narrative_bonus + 
            hook_bonus
        )

        clip["enhanced_score"] = enhanced_score
        clip["context_bonus"] = context_bonus
        clip["standalone_bonus"] = standalone_bonus

    # Now, filter based on the original criteria, but keep all clips with scores
    viable_clips = [clip for clip in evaluations if clip.get("overall_score", 0) >= min_score]

    # Sort the viable clips by enhanced score
    viable_clips.sort(key=lambda x: x["enhanced_score"], reverse=True)

    # If no clips meet the minimum score, we still want to return the best one
    if not viable_clips:
        # If no clips meet the criteria, return the top clip based on enhanced_score
        evaluations.sort(key=lambda x: x.get("enhanced_score", 0), reverse=True)
        return evaluations[:1]

    # Ensure diversity in narrative positions from the viable clips
    selected_clips = []
    used_positions = set()

    # First pass: select best clips from different narrative positions
    for clip in viable_clips:
        if len(selected_clips) >= top_n:
            break

        position = clip.get("narrative_position", "middle")
        if position not in used_positions or len(selected_clips) < top_n // 2:
            selected_clips.append(clip)
            used_positions.add(position)

    # Second pass: fill remaining slots with highest scores
    if len(selected_clips) < top_n:
        for clip in viable_clips:
            if len(selected_clips) >= top_n:
                break
            if clip not in selected_clips:
                selected_clips.append(clip)

    # As a final fallback, if selected_clips is still empty, return the best viable clip.
    if not selected_clips and viable_clips:
        return viable_clips[:1]

    return selected_clips[:top_n]

def main():
    parser = argparse.ArgumentParser(description="Extract potential YouTube shorts from transcript")
    parser.add_argument("transcript_path", nargs="?", help="Path to WhisperX JSON transcript", default=None)
    parser.add_argument("--output", help="Output JSON file for results", default=None)
    parser.add_argument("--min_duration", type=int, default=MIN_CLIP_DURATION, 
                        help=f"Minimum clip duration in seconds (default: {MIN_CLIP_DURATION})")
    parser.add_argument("--max_duration", type=int, default=MAX_CLIP_DURATION, 
                        help=f"Maximum clip duration in seconds (default: {MAX_CLIP_DURATION})")
    parser.add_argument("--top_n", type=int, default=10, 
                        help="Number of top clips to extract (default: 10)")
    parser.add_argument("--use_pause_based", action="store_true", default=True,
                        help="Use pause-based segmentation instead of overlapping segments (default: True)")
    parser.add_argument("--use_overlapping", action="store_true", default=False,
                        help="Use the old overlapping segmentation method (not recommended)")
    parser.add_argument("--use_context_aware", action="store_true", default=True,
                        help="Use context-aware GPT prompting (default: True)")
    parser.add_argument("--use_simple_gpt", action="store_true", default=False,
                        help="Use the old simple GPT evaluation (not recommended)")
    
    args = parser.parse_args()
    
    # Prompt for transcript file if not provided
    transcript_path = Path(args.transcript_path) if args.transcript_path else select_transcript_file()
    if not transcript_path:
        print("No transcript file selected. Exiting.")
        return
    
    if not transcript_path.exists():
        print(f"Transcript file not found: {transcript_path}")
        return
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        # Suggest a default name based on the transcript path
        suggested_name = f"{transcript_path.stem}_shorts.json"
        output_path = select_output_file(suggested_name)
        if not output_path:
            # Default to the same directory as the transcript
            output_path = transcript_path.parent / suggested_name
            print(f"Using default output path: {output_path}")
    
    # Initialize OpenAI client
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
    # Load transcript
    print(f"Loading transcript from {transcript_path}...")
    transcript = load_transcript(transcript_path)
    
    # Create potential clips using the selected method
    if args.use_overlapping:
        print(f"Creating overlapping clips (min: {args.min_duration}s, max: {args.max_duration}s)...")
        potential_clips = create_overlapping_segments(
            transcript, 
            min_duration=args.min_duration,
            max_duration=args.max_duration
        )
    else:
        print(f"Creating pause-based natural clips (min: {args.min_duration}s, max: {args.max_duration}s)...")
        potential_clips = create_pause_based_segments(
            transcript, 
            min_duration=args.min_duration,
            max_duration=args.max_duration
        )
    
    print(f"Found {len(potential_clips)} potential clips")
    
    # Evaluate clips with GPT using selected method
    if args.use_simple_gpt:
        print("Using simple GPT evaluation (legacy method)...")
        evaluations = []
        for i, clip in enumerate(potential_clips, 1):
            print(f"Evaluating clip {i}/{len(potential_clips)} ({clip['duration']:.1f}s)...")
            evaluation = evaluate_clip_with_gpt(clip, client)
            evaluations.append(evaluation)
            print(f"  Score: {evaluation['overall_score']:.1f}/10 | Title: {evaluation['title']}")
        
        # Filter top clips
        print(f"Selecting top {args.top_n} clips...")
        top_clips = filter_top_clips(evaluations, top_n=args.top_n)
    else:
        print("Using context-aware multi-pass GPT evaluation...")
        print("🧠 Pass 1: Analyzing lecture themes and structure...")
        
        # Use context-aware evaluation
        analysis_results = create_multi_pass_analysis(
            all_segments=transcript["segments"],
            potential_clips=potential_clips,
            client=client
        )
        
        print(f"📋 Identified themes: {', '.join(analysis_results['theme_analysis']['main_themes'][:3])}")
        print(f"🎯 Overall topic: {analysis_results['theme_analysis']['overall_topic']}")
        print(f"🧠 Pass 2: Context-aware evaluation of {len(potential_clips)} clips...")
        
        evaluations = analysis_results['clip_evaluations']
        
        # Show enhanced evaluation results
        for i, evaluation in enumerate(evaluations, 1):
            print(f"  Clip {i}: {evaluation['overall_score']:.1f}/10 | Context: {evaluation['context_dependency']} | {evaluation['title']}")
        
        # Enhanced filtering with context awareness
        print(f"Selecting top {args.top_n} context-aware clips...")
        top_clips = filter_context_aware_clips(evaluations, top_n=args.top_n)
    
    # Save results
    print(f"Saving {len(top_clips)} top clips to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "clips": top_clips
        }, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("\n===== TOP CLIPS =====")
    for i, clip in enumerate(top_clips, 1):
        print(f"{i}. ({clip['time_range']}) - {clip['title']} | Score: {clip['overall_score']:.1f}/10")
    
    print(f"\nDone! Results saved to {output_path}")
    print("\nNext step: Run cut_clips.py to extract the selected clips")

if __name__ == "__main__":
    main() 