import subprocess
import requests
from pathlib import Path
from typing import Optional
import urllib.parse

def is_direct_video_url(url: str) -> bool:
    """
    Check if URL is a direct video file (MP4, etc.) rather than a streaming platform.
    """
    parsed_url = urllib.parse.urlparse(url)
    
    # Check for direct video file extensions
    if parsed_url.path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
        return True
    
    # Check for known storage domains
    storage_domains = ['r2.dev', 's3.amazonaws.com', 'storage.googleapis.com', 'blob.core.windows.net']
    if any(domain in parsed_url.netloc for domain in storage_domains):
        return True
    
    return False

def download_direct_file(url: str, output_path: Path) -> Path:
    """
    Download a direct file using requests with streaming.
    """
    print(f"Downloading direct file: {url}")
    
    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Download with streaming to handle large files
    with requests.get(url, stream=True, timeout=30) as response:
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Show progress
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\rProgress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end="")
        
        print("\nDirect download complete!")
        return output_path

def download_video(url: str, project_path: Path, cookies: Optional[str] = None) -> Path:
    """
    Smart download function that handles both streaming platforms and direct files.
    
    Args:
        url: Video URL (YouTube, direct MP4, etc.)
        project_path: Path to project directory
        cookies: Optional path to cookies file for private videos
        
    Returns:
        Path to downloaded video file
    """
    output_path = project_path / "downloads" / "full.mp4"
    
    # Clean URL - remove leading/trailing spaces and quotes
    url = url.strip().strip('"\'')
    
    print(f"Starting download from: {url}")
    if cookies:
        print("Using cookies file for authentication")
    
    # Detect if this is a direct file or streaming platform
    if is_direct_video_url(url):
        print("Detected direct video file - using direct download")
        return download_direct_file(url, output_path)
    
    print("Detected streaming platform - using yt-dlp")
    
    # Build yt-dlp command for streaming platforms
    cmd = [
        "yt-dlp",
        "-f", "best[ext=mp4]/best",  # Try MP4 first, fallback to best available
        "-o", str(output_path),
        "--progress",
        "--no-check-certificate"
    ]
    
    if cookies:
        cmd.extend(["--cookies", cookies])
    
    cmd.append(url)
    
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        # Run with progress output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Print progress in real-time
        for line in process.stdout:
            print(line.strip())
        
        process.wait()
        
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd)
        
        print("\nDownload complete!")
        return output_path
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if hasattr(e, 'stderr') and e.stderr else 'Unknown error'
        raise RuntimeError(f"Failed to download video: {error_msg}") 