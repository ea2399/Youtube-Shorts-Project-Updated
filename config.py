import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenAI API configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4.1"  # Using gpt-4.1 for larger context window

# FFmpeg configuration
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")  # Path to ffmpeg executable

# Video processing settings
DEFAULT_LANGUAGE = "he"  # Hebrew
TARGET_LUFS = -23  # Target loudness level for normalization
MIN_CLIP_DURATION = 30  # seconds
MAX_CLIP_DURATION = 60  # seconds

# Output settings
VERTICAL_WIDTH = 720
VERTICAL_HEIGHT = 1280

# Project structure
PROJECT_SUBDIRS = [
    "downloads",
    "transcripts",
    "clips",
    "vertical"
]

# Highlight extraction settings
HIGHLIGHT_PROMPT = """
Extract {num_clips} engaging segments from this Torah lecture transcript.
Each segment should be:
- 30-60 seconds long
- Contain a complete thought or teaching
- Be suitable for a short-form video
- Include a compelling hook

Format each segment as JSON with:
- start: timestamp (HH:MM:SS.mmm)
- end: timestamp (HH:MM:SS.mmm)
- slug: URL-friendly title
- hook: attention-grabbing description
- tone: emotional tone (inspiring, thought-provoking, etc.)
""" 