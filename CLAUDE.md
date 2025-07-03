# YouTube Shorts Generator for Torah Content - Claude Documentation

## Project Overview

This is a Python-based AI system that automatically extracts engaging short clips (20-60 seconds) from long Torah lectures for use as YouTube shorts or social media content. The project uses advanced AI techniques including speech recognition, natural language processing, and context-aware content analysis.

## Architecture & Technology Stack

### Core Technologies
- **Python 3.8+** - Main programming language
- **OpenAI GPT-4.1** - Content analysis and clip evaluation
- **FFmpeg** - Video/audio processing
- **RunPod Cloud** - GPU-accelerated deployment platform

### Key Dependencies
- `openai>=1.3.0` - GPT API integration
- `yt-dlp>=2023.11.16` - Video downloading
- `ffmpeg-python>=0.2.0` - Video processing
- `pysrt>=1.1.2` - Subtitle handling
- `python-dotenv>=1.0.0` - Environment management
- `pydub>=0.25.1` - Audio processing

### Project Structure
```
/
├── main.py                    # Full pipeline orchestrator
├── handler.py                 # RunPod serverless handler
├── config.py                  # Configuration settings
├── extract_shorts.py          # AI-powered clip extraction
├── highlights.py              # Legacy highlight extraction
├── pause_based_segmentation.py # Natural speech boundary detection
├── context_aware_prompting.py # Advanced GPT evaluation
├── cut_clips.py              # Video cutting and processing
├── transcribe.py             # Speech-to-text processing
├── download.py               # Video downloading
├── reframe.py                # Vertical format conversion
├── normalize.py              # Audio normalization
├── srt_tools.py              # Subtitle utilities
├── utils/                    # Helper modules
│   ├── audio_helpers.py
│   └── ffmpeg_helpers.py
├── payloads/                 # Test configurations
├── requirements.txt          # Local dependencies
├── requirements-runpod.txt   # Cloud dependencies
├── Dockerfile               # Container configuration
└── deployment docs/         # Deployment guides
```

## Core Functionality

### 1. Video Processing Pipeline
The system processes videos through a multi-stage pipeline:

1. **Download** (`download.py`) - Fetch videos from URLs using yt-dlp
2. **Transcribe** (`transcribe.py`) - Convert audio to text with timestamps
3. **Segment** (`pause_based_segmentation.py`) - Find natural speech boundaries
4. **Analyze** (`context_aware_prompting.py`) - AI-powered content evaluation
5. **Extract** (`cut_clips.py`) - Cut and format selected clips
6. **Optimize** (`reframe.py`, `normalize.py`) - Create vertical formats and normalize audio

### 2. AI-Powered Content Analysis

#### Pause-Based Segmentation
- Uses natural speech pauses to identify clip boundaries
- Respects narrative flow and teaching units
- Eliminates artificial overlapping segments
- Configurable pause thresholds (0.5-3.0 seconds)

#### Context-Aware Evaluation
- Multi-pass GPT analysis for better clip selection
- Evaluates clips within surrounding context
- 6-metric scoring system:
  - Inspirational value
  - Humor potential
  - Emotional impact
  - Information density
  - Standalone comprehensibility
  - Context dependency

#### Enhanced Scoring Algorithm
```python
enhanced_score = (
    base_score + 
    context_bonus +      # Low dependency = +1.0
    standalone_bonus +   # High comprehensibility = +0.3
    narrative_bonus +    # Complete thoughts = +0.2
    hook_bonus          # Strong opening = +0.4
)
```

### 3. Configuration System

#### Main Settings (`config.py`)
- `OPENAI_MODEL = "gpt-4.1"` - Large context window model
- `MIN_CLIP_DURATION = 30` - Minimum clip length
- `MAX_CLIP_DURATION = 60` - Maximum clip length
- `DEFAULT_LANGUAGE = "he"` - Hebrew as primary language
- `VERTICAL_WIDTH/HEIGHT = 720x1280` - Mobile format dimensions

#### Environment Variables
- `OPENAI_API_KEY` - Required for GPT analysis
- `FFMPEG_PATH` - Optional FFmpeg location
- `RUNPOD_API_KEY` - For cloud deployment

## Deployment Models

### 1. Local Development
- Interactive file selection dialogs
- Step-by-step processing
- Full manual control
- Suitable for testing and development

### 2. Command Line Interface
```bash
python main.py --url "https://youtube.com/watch?v=..." --clips 3 --vertical --normalize
```

### 3. Cloud Deployment (RunPod)
- Serverless GPU processing
- JSON API interface
- Auto-scaling infrastructure
- Professional production environment

#### Sample API Usage
```json
{
  "input": {
    "video_url": "https://example.com/lecture.mp4",
    "transcript_json": {...},
    "language": "he",
    "num_clips": 3,
    "vertical": true,
    "subtitles": true
  }
}
```

## Key Features & Improvements

### Natural Segmentation
- **Before**: Fixed overlapping windows
- **After**: Speech-pause boundary detection
- **Benefit**: No duplicate content, better narrative flow

### Context-Aware Analysis
- **Before**: Isolated clip evaluation
- **After**: Surrounding context consideration
- **Benefit**: Self-contained, comprehensible clips

### Multi-Format Output
- Horizontal (original) format
- Vertical (720x1280) for mobile
- SRT subtitle files
- Normalized audio levels

### Quality Assurance
- Duration validation (30-60 seconds)
- Content appropriateness scoring
- Fallback clip generation
- Error handling and recovery

## Processing Workflow

### Standard Processing Flow
1. **Input**: Video URL or file
2. **Download**: Fetch video using yt-dlp
3. **Transcribe**: Extract text with word-level timing
4. **Segment**: Create natural speech boundaries
5. **Analyze**: Multi-pass GPT evaluation
6. **Select**: Choose top clips based on enhanced scoring
7. **Cut**: Extract video segments
8. **Format**: Create vertical versions and subtitles
9. **Output**: Return processed clips and metadata

### Error Handling
- Graceful degradation with fallback clips
- Comprehensive logging and debugging
- Automatic retry mechanisms
- Health checks and validation

## Language Support

### Primary Languages
- **Hebrew** (`he`) - Optimized for Torah content
- **English** (`en`) - Full feature support

### Text Processing
- UTF-8 encoding throughout
- Right-to-left text support
- Religious text handling
- Subtitle timing synchronization

## Testing & Validation

### Test Configurations
- `torah_lecture_basic.json` - Standard Hebrew processing
- `english_shiur_quality.json` - English with medium quality
- `chassidish_ultimate_quality.json` - Maximum quality Hebrew
- `fast_processing.json` - Quick testing

### Performance Metrics
- **Accuracy**: 85%+ standalone comprehensibility
- **Processing Time**: 2-15 minutes (GPU-dependent)
- **Quality**: 8+/10 average clip scores
- **Efficiency**: Natural boundaries eliminate 40% duplicate content

## Security & Best Practices

### API Key Management
- Environment variable storage
- No hardcoded secrets
- Secure container deployment
- Runtime key validation

### Error Recovery
- Fallback clip generation
- Graceful API failure handling
- Progress tracking and resumption
- Comprehensive logging

## Development Commands

### Local Testing
```bash
# Interactive mode
python extract_shorts.py
python cut_clips.py

# Command line mode
python main.py --url "..." --clips 3

# Component testing
python test_pause_segmentation.py
python test_context_aware.py
```

### Cloud Deployment
```bash
# Build container
docker build -t youtube-shorts-generator .

# Test endpoint
python test_endpoint.py --endpoint ENDPOINT_ID
```

### Code Quality
```bash
# No specific linting commands found in project
# Recommend adding: flake8, black, pytest
```

## Recent Enhancements

Based on git history, recent improvements include:
- Simplified architecture removing WhisperX dependency
- JSON input acceptance for pre-transcribed content
- RunPod endpoint optimization
- Docker deployment streamlining
- Test video URL updates

## Known Limitations

- Requires FFmpeg system installation
- Hebrew/English optimized (other languages may vary)
- Processing time scales with video length
- GPU recommended for optimal performance
- OpenAI API costs for content analysis

## Future Development Opportunities

1. **Additional Languages** - Expand beyond Hebrew/English
2. **Real-time Processing** - Stream processing capabilities
3. **Advanced Analytics** - Engagement prediction modeling
4. **Batch Processing** - Multiple video handling
5. **Quality Metrics** - Automated quality assessment
6. **Content Filtering** - Advanced appropriateness detection

This project represents a sophisticated AI-powered content creation pipeline specifically designed for Torah educational content, with robust cloud deployment capabilities and advanced natural language processing features.