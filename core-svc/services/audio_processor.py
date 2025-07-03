"""
Audio Intelligence System - Phase 2
Modern audio processing pipeline with VAD, filler word detection, and quality metrics
"""

import numpy as np
import torch
import torchaudio
import webrtcvad
import spacy
import fasttext
import soundfile as sf
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
import structlog
import tempfile
import json

logger = structlog.get_logger()


@dataclass
class AudioAnalysis:
    """Complete audio analysis results"""
    silence_segments: List[Tuple[float, float]]
    filler_words: List[Dict[str, Any]]
    quality_metrics: Dict[str, float]
    language_segments: List[Dict[str, Any]]
    speech_rate: float
    rms_levels: List[float]
    breathing_patterns: List[Dict[str, Any]]


@dataclass
class FillerWord:
    """Detected filler word with context"""
    word: str
    start_time: float
    end_time: float
    confidence: float
    language: str
    context: str


class AudioProcessor:
    """
    Audio Intelligence System for Phase 2
    Provides VAD, filler word detection, and audio quality metrics
    """
    
    def __init__(self, vad_mode: int = 2):
        """Initialize audio processor with models"""
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.vad = webrtcvad.Vad(vad_mode)  # 0-3, 2 is balanced
        
        # Language-specific filler word databases
        self.filler_databases = {
            "he": ["אה", "אמ", "כאילו", "יעני", "אוקיי", "בקיצור", "איך אומרים", "מה זה"],
            "en": ["um", "uh", "like", "you know", "actually", "basically", "sort of", "kind of"],
            "mixed": []  # Will combine both
        }
        
        # Initialize spaCy models (lazy loading)
        self._spacy_he = None
        self._spacy_en = None
        
        # FastText language detection (lazy loading)
        self._fasttext_model = None
        
        logger.info("AudioProcessor initialized", device=str(self.device))
    
    def _get_spacy_model(self, language: str):
        """Lazy load spaCy models"""
        if language == "he" and self._spacy_he is None:
            try:
                self._spacy_he = spacy.load("he_core_news_sm")
            except OSError:
                logger.warning("Hebrew spaCy model not found, using English")
                self._spacy_he = self._get_spacy_model("en")
        
        if language == "en" and self._spacy_en is None:
            try:
                self._spacy_en = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("English spaCy model not found, using simple tokenization")
                return None
        
        return self._spacy_he if language == "he" else self._spacy_en
    
    def _get_fasttext_model(self):
        """Lazy load FastText language detection model"""
        if self._fasttext_model is None:
            try:
                # Download if not exists
                self._fasttext_model = fasttext.load_model('lid.176.bin')
            except Exception as e:
                logger.warning("FastText model not available, using fallback detection", error=str(e))
                self._fasttext_model = None
        return self._fasttext_model
    
    def detect_silence(self, audio_path: Path, frame_duration_ms: int = 30) -> List[Tuple[float, float]]:
        """
        Detect silence segments using Voice Activity Detection (VAD)
        Returns list of (start_time, end_time) tuples for silence segments
        """
        try:
            # Load audio file
            waveform, sample_rate = torchaudio.load(str(audio_path))
            
            # Convert to 16kHz mono if needed (VAD requirement)
            if sample_rate != 16000:
                resampler = torchaudio.transforms.Resample(sample_rate, 16000)
                waveform = resampler(waveform)
                sample_rate = 16000
            
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
            
            # Convert to numpy for VAD
            audio_data = waveform.squeeze().numpy()
            
            # Convert to 16-bit PCM
            audio_int16 = (audio_data * 32767).astype(np.int16).tobytes()
            
            # VAD processing
            frame_length = int(sample_rate * frame_duration_ms / 1000)
            silence_segments = []
            current_silence_start = None
            
            for i in range(0, len(audio_int16) - frame_length * 2, frame_length * 2):
                frame = audio_int16[i:i + frame_length * 2]
                
                # VAD returns True for speech, False for silence
                is_speech = self.vad.is_speech(frame, sample_rate)
                current_time = i / (sample_rate * 2)  # 2 bytes per sample
                
                if not is_speech and current_silence_start is None:
                    current_silence_start = current_time
                elif is_speech and current_silence_start is not None:
                    silence_segments.append((current_silence_start, current_time))
                    current_silence_start = None
            
            # Close final silence segment if needed
            if current_silence_start is not None:
                silence_segments.append((current_silence_start, len(audio_int16) / (sample_rate * 2)))
            
            logger.info("Silence detection completed", 
                       segments_found=len(silence_segments),
                       audio_duration=len(audio_int16) / (sample_rate * 2))
            
            return silence_segments
            
        except Exception as e:
            logger.error("Silence detection failed", error=str(e))
            return []
    
    def detect_language_segments(self, transcript: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect language for each transcript segment"""
        fasttext_model = self._get_fasttext_model()
        segments = transcript.get("segments", [])
        language_segments = []
        
        for segment in segments:
            text = segment.get("text", "").strip()
            if not text:
                continue
            
            # FastText language detection
            detected_lang = "unknown"
            confidence = 0.0
            
            if fasttext_model:
                try:
                    predictions = fasttext_model.predict(text, k=1)
                    detected_lang = predictions[0][0].replace("__label__", "")
                    confidence = float(predictions[1][0])
                    
                    # Map common language codes
                    if detected_lang in ["he", "heb"]:
                        detected_lang = "he"
                    elif detected_lang in ["en", "eng"]:
                        detected_lang = "en"
                        
                except Exception as e:
                    logger.warning("Language detection failed for segment", error=str(e))
            
            # Fallback heuristic detection
            if detected_lang == "unknown" or confidence < 0.5:
                # Simple heuristic: check for Hebrew characters
                hebrew_chars = sum(1 for char in text if '\u0590' <= char <= '\u05FF')
                if hebrew_chars > len(text) * 0.3:
                    detected_lang = "he"
                    confidence = 0.8
                else:
                    detected_lang = "en"
                    confidence = 0.6
            
            language_segments.append({
                "start": segment.get("start", 0),
                "end": segment.get("end", 0),
                "text": text,
                "language": detected_lang,
                "confidence": confidence
            })
        
        logger.info("Language detection completed", 
                   segments_processed=len(language_segments))
        
        return language_segments
    
    def detect_filler_words(self, transcript: Dict[str, Any], 
                          audio_path: Path) -> List[FillerWord]:
        """
        Detect filler words in transcript with context analysis
        Uses word-level timestamps from WhisperX for precision
        """
        filler_words = []
        words = transcript.get("words", [])
        
        if not words:
            logger.warning("No word-level timestamps found in transcript")
            return filler_words
        
        # Detect language segments first
        language_segments = self.detect_language_segments(transcript)
        
        # Process each word
        for word_data in words:
            word = word_data.get("word", "").strip().lower()
            start_time = word_data.get("start", 0)
            end_time = word_data.get("end", 0)
            word_confidence = word_data.get("score", 1.0)
            
            if not word:
                continue
            
            # Determine language for this word
            word_language = "en"  # default
            for lang_segment in language_segments:
                if lang_segment["start"] <= start_time <= lang_segment["end"]:
                    word_language = lang_segment["language"]
                    break
            
            # Check against filler word database
            filler_db = self.filler_databases.get(word_language, 
                                                 self.filler_databases["en"])
            
            # Normalize word for matching
            normalized_word = word.replace("'", "").replace(",", "").replace(".", "")
            
            if normalized_word in filler_db or word in filler_db:
                # Get context around the filler word
                context_words = []
                for ctx_word in words:
                    if (abs(ctx_word.get("start", 0) - start_time) < 3.0 and  # 3 seconds context
                        ctx_word.get("word", "").strip()):
                        context_words.append(ctx_word.get("word", "").strip())
                
                context = " ".join(context_words)
                
                # Calculate confidence based on word confidence and context
                final_confidence = word_confidence
                
                # Boost confidence if surrounded by silence (typical filler pattern)
                # Lower confidence if part of compound word
                if len(context_words) < 3:  # Isolated word
                    final_confidence *= 1.2
                elif word in context and len(word) < 3:  # Very short words are more likely fillers
                    final_confidence *= 1.1
                
                final_confidence = min(final_confidence, 1.0)
                
                filler_word = FillerWord(
                    word=word,
                    start_time=start_time,
                    end_time=end_time,
                    confidence=final_confidence,
                    language=word_language,
                    context=context
                )
                
                filler_words.append(filler_word)
        
        logger.info("Filler word detection completed", 
                   filler_words_found=len(filler_words),
                   languages_detected=set(fw.language for fw in filler_words))
        
        return filler_words
    
    def calculate_audio_quality_metrics(self, audio_path: Path, 
                                      transcript: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate comprehensive audio quality metrics
        """
        try:
            # Load audio with torchaudio for GPU acceleration
            waveform, sample_rate = torchaudio.load(str(audio_path))
            waveform = waveform.to(self.device)
            
            # Convert to mono if stereo
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
            
            # Calculate RMS levels
            frame_size = int(sample_rate * 0.05)  # 50ms frames
            rms_values = []
            
            for i in range(0, waveform.shape[1] - frame_size, frame_size):
                frame = waveform[:, i:i + frame_size]
                rms = torch.sqrt(torch.mean(frame ** 2))
                rms_values.append(rms.item())
            
            # Calculate metrics
            metrics = {}
            
            # RMS statistics
            rms_tensor = torch.tensor(rms_values)
            metrics["rms_mean"] = torch.mean(rms_tensor).item()
            metrics["rms_std"] = torch.std(rms_tensor).item()
            metrics["rms_max"] = torch.max(rms_tensor).item()
            metrics["rms_min"] = torch.min(rms_tensor).item()
            
            # Dynamic range
            metrics["dynamic_range_db"] = 20 * np.log10(metrics["rms_max"] / max(metrics["rms_min"], 1e-8))
            
            # Speech rate calculation
            total_words = len(transcript.get("words", []))
            total_duration = transcript.get("segments", [])[-1].get("end", 1) if transcript.get("segments") else 1
            metrics["speech_rate_wpm"] = (total_words / total_duration) * 60
            
            # Signal-to-noise estimation (simplified)
            # Use top 20% of RMS values as signal, bottom 20% as noise
            sorted_rms = sorted(rms_values, reverse=True)
            signal_level = np.mean(sorted_rms[:len(sorted_rms)//5])  # Top 20%
            noise_level = np.mean(sorted_rms[-len(sorted_rms)//5:])  # Bottom 20%
            metrics["snr_estimate_db"] = 20 * np.log10(signal_level / max(noise_level, 1e-8))
            
            # Breathing pattern detection (silence analysis)
            silence_segments = self.detect_silence(audio_path)
            if silence_segments:
                pause_durations = [end - start for start, end in silence_segments]
                metrics["avg_pause_duration"] = np.mean(pause_durations)
                metrics["pause_count"] = len(pause_durations)
                metrics["breathing_regularity"] = 1.0 / (1.0 + np.std(pause_durations))
            else:
                metrics["avg_pause_duration"] = 0.0
                metrics["pause_count"] = 0
                metrics["breathing_regularity"] = 0.0
            
            logger.info("Audio quality metrics calculated", 
                       snr_db=round(metrics["snr_estimate_db"], 2),
                       speech_rate=round(metrics["speech_rate_wpm"], 1),
                       dynamic_range=round(metrics["dynamic_range_db"], 2))
            
            return metrics
            
        except Exception as e:
            logger.error("Audio quality metrics calculation failed", error=str(e))
            return {}
    
    def process_audio(self, audio_path: Path, transcript: Dict[str, Any]) -> AudioAnalysis:
        """
        Complete audio processing pipeline
        Returns comprehensive audio analysis
        """
        logger.info("Starting audio intelligence processing", audio_path=str(audio_path))
        
        # Input validation
        if not audio_path or not audio_path.exists():
            raise ValueError(f"Audio path does not exist: {audio_path}")
        
        if not audio_path.is_file():
            raise ValueError(f"Audio path is not a file: {audio_path}")
        
        # Check file size (limit to 1GB for safety)
        file_size = audio_path.stat().st_size
        if file_size > 1024 * 1024 * 1024:  # 1GB
            raise ValueError(f"Audio file too large: {file_size / (1024**3):.1f}GB")
        
        # Validate audio format
        valid_extensions = {'.wav', '.mp3', '.flac', '.m4a', '.aac', '.ogg'}
        if audio_path.suffix.lower() not in valid_extensions:
            raise ValueError(f"Unsupported audio format: {audio_path.suffix}")
        
        # Validate transcript structure
        if not isinstance(transcript, dict):
            raise ValueError("Transcript must be a dictionary")
        
        if not transcript.get("segments") and not transcript.get("words"):
            raise ValueError("Transcript must contain either 'segments' or 'words'")
        
        try:
            # Step 1: Silence detection
            silence_segments = self.detect_silence(audio_path)
            
            # Step 2: Filler word detection
            filler_words = self.detect_filler_words(transcript, audio_path)
            
            # Step 3: Language detection
            language_segments = self.detect_language_segments(transcript)
            
            # Step 4: Quality metrics
            quality_metrics = self.calculate_audio_quality_metrics(audio_path, transcript)
            
            # Step 5: Speech rate calculation
            speech_rate = quality_metrics.get("speech_rate_wpm", 0.0)
            
            # Step 6: RMS level extraction
            rms_levels = [quality_metrics.get("rms_mean", 0.0)]  # Simplified for now
            
            # Step 7: Breathing pattern analysis
            breathing_patterns = []
            for start, end in silence_segments:
                if end - start > 0.5:  # Significant pauses
                    breathing_patterns.append({
                        "start": start,
                        "end": end,
                        "duration": end - start,
                        "type": "pause"
                    })
            
            # Convert filler words to dict format
            filler_words_dict = []
            for fw in filler_words:
                filler_words_dict.append({
                    "word": fw.word,
                    "start": fw.start_time,
                    "end": fw.end_time,
                    "confidence": fw.confidence,
                    "language": fw.language,
                    "context": fw.context
                })
            
            analysis = AudioAnalysis(
                silence_segments=silence_segments,
                filler_words=filler_words_dict,
                quality_metrics=quality_metrics,
                language_segments=language_segments,
                speech_rate=speech_rate,
                rms_levels=rms_levels,
                breathing_patterns=breathing_patterns
            )
            
            logger.info("Audio intelligence processing completed",
                       silence_segments=len(silence_segments),
                       filler_words=len(filler_words_dict),
                       speech_rate=round(speech_rate, 1))
            
            return analysis
            
        except Exception as e:
            logger.error("Audio processing failed", error=str(e))
            raise