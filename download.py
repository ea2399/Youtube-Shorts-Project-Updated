import subprocess
from pathlib import Path
from typing import Optional

def download_video(url: str, project_path: Path, cookies: Optional[str] = None) -> Path:
    """
    Download video using yt-dlp.
    
    Args:
        url: YouTube video URL
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
    
    # Build yt-dlp command
    cmd = [
        "yt-dlp",
        "-f", "bestvideo+bestaudio",
        "--merge-output-format", "mp4",
        "-o", str(output_path),
        "--progress",  # Show download progress
        "--no-check-certificate"  # Add this if there are SSL issues
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