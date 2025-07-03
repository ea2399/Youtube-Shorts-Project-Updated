import json
import re
from pathlib import Path
from typing import List, Dict

from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL, HIGHLIGHT_PROMPT

def split_transcript_into_chunks(transcript: str, max_chunk_size: int = 6000) -> List[str]:
    """Split transcript into chunks that fit within token limits."""
    # Split by double newline to keep subtitle blocks together
    blocks = transcript.split('\n\n')
    chunks = []
    current_chunk = []
    current_size = 0
    
    for block in blocks:
        # Rough token estimation (4 chars ≈ 1 token)
        block_size = len(block) // 4
        
        if current_size + block_size > max_chunk_size:
            # Save current chunk and start a new one
            chunks.append('\n\n'.join(current_chunk))
            current_chunk = [block]
            current_size = block_size
        else:
            current_chunk.append(block)
            current_size += block_size
    
    # Add the last chunk
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    return chunks

def create_fallback_highlights(num_clips: int = 1) -> List[Dict]:
    """Create fallback highlights from beginning of video."""
    fallbacks = []
    for i in range(min(num_clips, 3)):
        start_time = i * 60  # Start every minute
        end_time = start_time + 45  # 45 seconds duration
        
        # Format times as HH:MM:SS
        start_formatted = f"{start_time // 3600:02d}:{(start_time % 3600) // 60:02d}:{start_time % 60:02d}"
        end_formatted = f"{end_time // 3600:02d}:{(end_time % 3600) // 60:02d}:{end_time % 60:02d}"
        
        fallbacks.append({
            "start": start_formatted,
            "end": end_formatted,
            "slug": f"fallback-clip-{i+1}",
            "hook": f"Fallback clip {i+1} from the lecture",
            "tone": "informative"
        })
    
    return fallbacks

def parse_timestamp_to_seconds(timestamp: str) -> float:
    """Convert timestamp string to seconds."""
    parts = timestamp.replace(',', '.').split(':')
    if len(parts) == 3:  # HH:MM:SS
        hours, minutes, seconds = parts
        return float(hours) * 3600 + float(minutes) * 60 + float(seconds)
    elif len(parts) == 2:  # MM:SS
        minutes, seconds = parts
        return float(minutes) * 60 + float(seconds)
    else:
        return 0

def format_seconds_to_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS.mmm format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}".replace('.', ',')

def validate_highlight_duration(highlight: Dict) -> Dict:
    """Validate and fix highlight duration to ensure it's between 30-60 seconds."""
    MIN_DURATION = 30
    MAX_DURATION = 60
    IDEAL_DURATION = 45
    
    start_seconds = parse_timestamp_to_seconds(highlight['start'])
    end_seconds = parse_timestamp_to_seconds(highlight['end'])
    duration = end_seconds - start_seconds
    
    # If duration is already valid, return the highlight unchanged
    if MIN_DURATION <= duration <= MAX_DURATION:
        return highlight
    
    print(f"  ⚠️ Invalid duration: {duration:.1f}s (should be 30-60s). Adjusting...")
    
    # Fix duration if it's too short
    if duration < MIN_DURATION:
        # Try to extend the end time
        new_end_seconds = start_seconds + IDEAL_DURATION
        highlight['end'] = format_seconds_to_timestamp(new_end_seconds)
        print(f"  → Extended end time to {highlight['end']} (new duration: {IDEAL_DURATION}s)")
    
    # Fix duration if it's too long
    elif duration > MAX_DURATION:
        # Trim the end time
        new_end_seconds = start_seconds + IDEAL_DURATION
        highlight['end'] = format_seconds_to_timestamp(new_end_seconds)
        print(f"  → Shortened end time to {highlight['end']} (new duration: {IDEAL_DURATION}s)")
    
    return highlight

def extract_highlights_from_chunk(client: OpenAI, chunk: str, num_clips: int) -> List[Dict]:
    """Extract highlights from a single chunk."""
    prompt = HIGHLIGHT_PROMPT.format(num_clips=num_clips)
    system_message = """
    You are a helpful assistant that extracts engaging segments from Torah lectures.
    
    IMPORTANT: Each highlight MUST be between 30-60 seconds in duration. 
    This is absolutely critical - highlights shorter than 30 seconds or longer than 60 seconds are not acceptable.
    
    Your output MUST be valid JSON with an array of objects, each with these fields:
    - start: timestamp (HH:MM:SS format)
    - end: timestamp (HH:MM:SS format) - MUST be 30-60 seconds after start time
    - slug: a short URL-friendly title
    - hook: an attention-grabbing description
    - tone: the emotional tone
    
    Example of valid output format with PROPER DURATION (45 seconds):
    [
      {
        "start": "00:05:30",
        "end": "00:06:15",
        "slug": "faith-example",
        "hook": "How faith transforms challenges",
        "tone": "inspiring"
      }
    ]
    
    Always verify that end time - start time is between 30 and 60 seconds before returning your response.
    """
    
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": f"{prompt}\n\nTranscript:\n{chunk}"}
    ]
    
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        print(f"API response received, attempting to parse JSON...")
        
        # Try to clean up the response if it's not pure JSON
        # Strip any markdown code block formatting
        content = re.sub(r'```json|```', '', content).strip()
        
        # Find the first [ and last ] for a JSON array
        start_idx = content.find('[')
        end_idx = content.rfind(']') + 1
        
        if start_idx >= 0 and end_idx > start_idx:
            json_str = content[start_idx:end_idx]
            highlights = json.loads(json_str)
            
            # Validate and fix highlight durations
            validated_highlights = []
            for h in highlights:
                validated_highlights.append(validate_highlight_duration(h))
            
            return validated_highlights
        else:
            print("No JSON array found in response.")
            return create_fallback_highlights(num_clips)
            
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {str(e)}")
        print(f"Response content: {content[:200]}...")  # Print part of the response
        return create_fallback_highlights(num_clips)
    except Exception as e:
        print(f"Error in API call: {str(e)}")
        return create_fallback_highlights(num_clips)

def merge_highlights(all_highlights: List[Dict], num_clips: int) -> List[Dict]:
    """Merge and select the best highlights."""
    if not all_highlights:
        return create_fallback_highlights(num_clips)
    
    # Ensure all highlights have required fields
    valid_highlights = []
    for h in all_highlights:
        if all(k in h for k in ['start', 'end', 'slug', 'hook']):
            valid_highlights.append(h)
    
    if not valid_highlights:
        return create_fallback_highlights(num_clips)
    
    # Limit to requested number of clips
    return valid_highlights[:num_clips]

def extract_highlights(transcript_path: Path, num_clips: int) -> List[Dict]:
    """
    Extract highlight segments from transcript using GPT-4.1.
    
    Args:
        transcript_path: Path to transcript file
        num_clips: Number of clips to extract
        
    Returns:
        List of highlight segments with timestamps and metadata
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OpenAI API key not found. Set OPENAI_API_KEY in .env file.")
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    try:
        # Read transcript
        print("Reading transcript...")
        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript = f.read()
        
        # Check if transcript is too short or empty
        if len(transcript.strip()) < 100:
            print("Warning: Transcript is very short. Creating default highlights.")
            highlights = create_fallback_highlights(num_clips)
            
            # Save highlights
            output_path = transcript_path.parent.parent / "highlights.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(highlights, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Created {len(highlights)} default highlights")
            return highlights
        
        # Split transcript into chunks
        print("Splitting transcript into manageable chunks...")
        chunks = split_transcript_into_chunks(transcript)
        print(f"Split into {len(chunks)} chunks")
        
        # Process each chunk
        all_highlights = []
        for i, chunk in enumerate(chunks, 1):
            print(f"Processing chunk {i}/{len(chunks)}...")
            try:
                chunk_highlights = extract_highlights_from_chunk(client, chunk, num_clips)
                if chunk_highlights:
                    all_highlights.extend(chunk_highlights)
                    print(f"✓ Found {len(chunk_highlights)} highlights in chunk {i}")
            except Exception as e:
                print(f"Warning: Error processing chunk {i}: {str(e)}")
                continue
        
        # If no highlights found, create fallbacks
        if not all_highlights:
            print("No highlights found in any chunk. Creating fallbacks.")
            all_highlights = create_fallback_highlights(num_clips)
        
        # Select best highlights
        print("Selecting final highlights...")
        final_highlights = merge_highlights(all_highlights, num_clips)
        
        # Save highlights
        output_path = transcript_path.parent.parent / "highlights.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(final_highlights, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Saved {len(final_highlights)} highlight segments")
        return final_highlights
    
    except Exception as e:
        print(f"Critical error in highlight extraction: {str(e)}")
        fallback_highlights = create_fallback_highlights(num_clips)
        
        try:
            # Try to save fallbacks
            output_path = transcript_path.parent.parent / "highlights.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(fallback_highlights, f, indent=2, ensure_ascii=False)
            print(f"Created and saved {len(fallback_highlights)} fallback highlights")
        except Exception:
            print("Could not save fallback highlights file")
        
        return fallback_highlights 