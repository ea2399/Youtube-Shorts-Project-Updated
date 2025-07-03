"""
Context-aware GPT prompting for better clip evaluation and selection.

This module enhances GPT evaluation by providing surrounding context, analyzing
narrative flow, and ensuring clips are self-contained and understandable.
"""

import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import openai
from config import OPENAI_API_KEY, OPENAI_MODEL

@dataclass
class ClipContext:
    """Represents context information for a clip."""
    before_text: str
    clip_text: str
    after_text: str
    topic_context: str
    narrative_position: str  # "opening", "middle", "conclusion"
    setup_needed: bool
    provides_payoff: bool

class ContextAwareEvaluator:
    """
    Enhanced GPT evaluator that considers context when scoring clips.
    """
    
    def __init__(self, openai_client: openai.OpenAI):
        self.client = openai_client
        
    def extract_context_around_clip(self, 
                                  all_segments: List[Dict[str, Any]], 
                                  clip_start: float, 
                                  clip_end: float,
                                  context_duration: float = 30.0) -> ClipContext:
        """
        Extract context before and after a clip for better evaluation.
        
        Args:
            all_segments: All transcript segments
            clip_start: Start time of the clip
            clip_end: End time of the clip
            context_duration: How many seconds of context to include
            
        Returns:
            ClipContext with surrounding information
        """
        # Find context before the clip
        before_segments = []
        before_end_time = clip_start
        before_start_time = clip_start - context_duration
        
        for segment in all_segments:
            if (segment["start"] >= before_start_time and 
                segment["end"] <= before_end_time):
                before_segments.append(segment)
        
        # Find context after the clip
        after_segments = []
        after_start_time = clip_end
        after_end_time = clip_end + context_duration
        
        for segment in all_segments:
            if (segment["start"] >= after_start_time and 
                segment["end"] <= after_end_time):
                after_segments.append(segment)
        
        # Find the actual clip segments
        clip_segments = []
        for segment in all_segments:
            if (segment["start"] >= clip_start and 
                segment["end"] <= clip_end):
                clip_segments.append(segment)
        
        # Combine text
        before_text = " ".join(seg["text"] for seg in before_segments)
        clip_text = " ".join(seg["text"] for seg in clip_segments)
        after_text = " ".join(seg["text"] for seg in after_segments)
        
        # Analyze narrative position
        total_duration = all_segments[-1]["end"] if all_segments else clip_end
        position_ratio = clip_start / total_duration
        
        if position_ratio < 0.2:
            narrative_position = "opening"
        elif position_ratio > 0.8:
            narrative_position = "conclusion"
        else:
            narrative_position = "middle"
        
        # Determine if setup is needed or payoff is provided
        setup_needed = self._needs_setup(before_text, clip_text)
        provides_payoff = self._provides_payoff(clip_text, after_text)
        
        # Extract topic context
        topic_context = self._extract_topic_context(before_text, clip_text, after_text)
        
        return ClipContext(
            before_text=before_text,
            clip_text=clip_text,
            after_text=after_text,
            topic_context=topic_context,
            narrative_position=narrative_position,
            setup_needed=setup_needed,
            provides_payoff=provides_payoff
        )
    
    def _needs_setup(self, before_text: str, clip_text: str) -> bool:
        """Determine if the clip needs setup context to be understood."""
        # Simple heuristics - could be enhanced with NLP
        setup_indicators = [
            "this", "that", "it", "he", "she", "they",  # Pronouns without clear referents
            "therefore", "so", "thus", "as a result",   # Conclusion words
            "but", "however", "nevertheless",           # Contrast words
            "the answer", "the solution", "the key"     # References to previous questions
        ]
        
        clip_lower = clip_text.lower()
        
        # Check if clip starts with words that need context
        first_words = clip_lower.split()[:5]
        for word in first_words:
            if any(indicator in word for indicator in setup_indicators):
                return True
        
        return False
    
    def _provides_payoff(self, clip_text: str, after_text: str) -> bool:
        """Determine if the clip provides resolution/payoff."""
        payoff_indicators = [
            "the answer is", "the solution", "here's why", "this means",
            "therefore", "in conclusion", "the key point",
            "what this teaches us", "the lesson", "we learn"
        ]
        
        clip_lower = clip_text.lower()
        return any(indicator in clip_lower for indicator in payoff_indicators)
    
    def _extract_topic_context(self, before_text: str, clip_text: str, after_text: str) -> str:
        """Extract the main topic/theme being discussed."""
        # Combine all text for topic analysis
        full_text = f"{before_text} {clip_text} {after_text}"
        
        # Simple keyword extraction - could be enhanced with NLP
        torah_topics = [
            "faith", "emunah", "trust", "bitachon",
            "prayer", "tefillah", "davening",
            "mitzvah", "commandment", "halacha",
            "teshuvah", "repentance", "forgiveness",
            "Torah study", "learning", "gemara",
            "Shabbat", "holidays", "festivals",
            "names of God", "divine attributes",
            "relationships", "marriage", "family",
            "business ethics", "honesty", "integrity"
        ]
        
        found_topics = []
        text_lower = full_text.lower()
        for topic in torah_topics:
            if topic.lower() in text_lower:
                found_topics.append(topic)
        
        if found_topics:
            return f"Discussion about: {', '.join(found_topics[:3])}"
        else:
            return "Torah teaching and wisdom"
    
    def evaluate_clip_with_context(self, 
                                 clip: Dict[str, Any],
                                 context: ClipContext,
                                 all_segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluate a clip using context-aware prompting.
        
        Args:
            clip: The clip data
            context: Context information
            all_segments: All transcript segments for reference
            
        Returns:
            Enhanced evaluation with context awareness
        """
        time_range = f"{clip['start']:.1f}s - {clip['end']:.1f}s"
        
        # Create context-aware prompt
        prompt = f"""You are evaluating a {clip['duration']:.1f}-second clip from a Torah lecture for use as a YouTube short.

CONTEXT INFORMATION:
• Topic: {context.topic_context}
• Position in lecture: {context.narrative_position}
• Needs setup: {'Yes' if context.setup_needed else 'No'}
• Provides payoff: {'Yes' if context.provides_payoff else 'No'}

SURROUNDING CONTEXT:
What was said BEFORE this clip:
"{context.before_text}"

THE CLIP TO EVALUATE:
"{context.clip_text}"

What comes AFTER this clip:
"{context.after_text}"

Now evaluate this clip considering:

1. STANDALONE COMPREHENSIBILITY (1-10):
   - Can a viewer understand this clip without hearing what came before?
   - Does it make sense on its own?
   - Are there unresolved references or pronouns?

2. NARRATIVE COMPLETENESS (1-10):
   - Does the clip contain a complete thought or teaching?
   - Is there a clear beginning, middle, and end?
   - Does it resolve any questions or tensions it raises?

3. HOOK QUALITY (1-10):
   - Does it grab attention from the first seconds?
   - Is there an engaging opening that draws viewers in?
   - Would someone keep watching?

4. INSPIRATIONAL VALUE (1-10):
   - How inspiring or uplifting is the message?
   - Does it provide practical wisdom or guidance?

5. EMOTIONAL IMPACT (1-10):
   - How emotionally engaging is the content?
   - Does it evoke feelings or create connection?

6. INFORMATION DENSITY (1-10):
   - How much valuable information is packed in?
   - Is the content substantive or superficial?

ADDITIONAL ANALYSIS:
• Context Dependency: How much does this clip rely on prior context? (Low/Medium/High)
• Improvement Suggestions: If the clip needs context, how could it be improved?
• Target Audience Appeal: Who would find this most engaging?

Respond in JSON format:
{{
  "standalone_comprehensibility": score,
  "narrative_completeness": score,
  "hook_quality": score,
  "inspirational": score,
  "emotional": score,
  "informational": score,
  "overall_score": average_score,
  "context_dependency": "Low/Medium/High",
  "recommended": "Yes/No/Maybe",
  "reasoning": "detailed explanation of why this clip works or doesn't work",
  "title": "engaging title under 60 characters",
  "tags": ["tag1", "tag2", "tag3"],
  "improvement_suggestions": "how to make this clip better",
  "target_audience": "who would most enjoy this clip",
  "confidence": "how confident you are in this evaluation (1-10)"
}}"""

        try:
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You are an expert in evaluating Torah content for social media shorts with deep understanding of context and narrative flow."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3  # Lower temperature for more consistent evaluations
            )
            
            evaluation = json.loads(response.choices[0].message.content)
            
            # Add clip metadata
            evaluation.update({
                "start": clip["start"],
                "end": clip["end"],
                "duration": clip["duration"],
                "text": context.clip_text,
                "time_range": time_range,
                "context_before": context.before_text[:100] + "..." if len(context.before_text) > 100 else context.before_text,
                "context_after": context.after_text[:100] + "..." if len(context.after_text) > 100 else context.after_text,
                "narrative_position": context.narrative_position,
                "topic_context": context.topic_context
            })
            
            return evaluation
            
        except Exception as e:
            # Fallback evaluation
            return {
                "start": clip["start"],
                "end": clip["end"],
                "duration": clip["duration"],
                "text": context.clip_text,
                "standalone_comprehensibility": 5,
                "narrative_completeness": 5,
                "hook_quality": 5,
                "inspirational": 5,
                "emotional": 5,
                "informational": 5,
                "overall_score": 5.0,
                "context_dependency": "Unknown",
                "recommended": "Maybe",
                "reasoning": f"Error in evaluation: {str(e)}",
                "title": "Torah Wisdom Clip",
                "tags": ["Torah", "Wisdom"],
                "improvement_suggestions": "Unable to analyze due to error",
                "target_audience": "Torah students",
                "confidence": 1,
                "error": str(e)
            }

def create_multi_pass_analysis(all_segments: List[Dict[str, Any]], 
                             potential_clips: List[Dict[str, Any]],
                             client: openai.OpenAI) -> Dict[str, Any]:
    """
    Perform multi-pass analysis: first extract themes, then evaluate clips.
    
    Args:
        all_segments: All transcript segments
        potential_clips: Potential clips to evaluate
        client: OpenAI client
        
    Returns:
        Analysis results with themes and evaluations
    """
    # Pass 1: Extract main themes and topics
    full_text = " ".join(segment["text"] for segment in all_segments)
    
    theme_prompt = f"""Analyze this Torah lecture transcript and extract:

1. Main themes and topics discussed
2. Key teaching points or lessons
3. Narrative structure (how ideas flow and build)
4. Most impactful moments or quotes

Transcript:
{full_text[:4000]}...

Respond in JSON format:
{{
  "main_themes": ["theme1", "theme2", "theme3"],
  "key_teachings": ["teaching1", "teaching2"],
  "narrative_flow": "description of how ideas develop",
  "impactful_moments": ["moment1", "moment2"],
  "overall_topic": "one sentence summary of the lecture"
}}"""
    
    try:
        theme_response = client.chat.completions.create(
            model=OPENAI_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are an expert in Torah content analysis."},
                {"role": "user", "content": theme_prompt}
            ]
        )
        
        theme_analysis = json.loads(theme_response.choices[0].message.content)
    except:
        theme_analysis = {
            "main_themes": ["Torah wisdom", "spiritual growth"],
            "key_teachings": ["faith and trust"],
            "narrative_flow": "Progressive development of ideas",
            "impactful_moments": ["opening teaching"],
            "overall_topic": "Torah teachings and wisdom"
        }
    
    # Pass 2: Evaluate clips with theme context
    evaluator = ContextAwareEvaluator(client)
    enhanced_evaluations = []
    
    for clip in potential_clips:
        context = evaluator.extract_context_around_clip(
            all_segments, 
            clip["start"], 
            clip["end"]
        )
        
        # Add theme context
        context.topic_context = f"{theme_analysis['overall_topic']}. Main themes: {', '.join(theme_analysis['main_themes'][:2])}"
        
        evaluation = evaluator.evaluate_clip_with_context(clip, context, all_segments)
        enhanced_evaluations.append(evaluation)
    
    return {
        "theme_analysis": theme_analysis,
        "clip_evaluations": enhanced_evaluations,
        "total_clips": len(enhanced_evaluations),
        "analysis_method": "context_aware_multi_pass"
    }

# Example usage
if __name__ == "__main__":
    # This would be called from extract_shorts.py
    print("Context-aware prompting module ready!")
    print("Use create_multi_pass_analysis() for enhanced clip evaluation.")