"""
Core configuration - environment detection, paths, and constants.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional


# Environment variables for configuration
VIDEO_SERVER_PORT = int(os.environ.get("VIDEO_SERVER_PORT", 8080))
VIDEO_SERVER_HOST = os.environ.get("VIDEO_SERVER_HOST", "localhost")

# Default recordings directories
CONTAINER_RECORDINGS_DIR = Path("/app/recordings")
HOST_RECORDINGS_DIR = Path(os.environ.get("RECORDINGS_DIR", os.path.expanduser("~/recordings")))


def is_container_environment() -> bool:
    """Detect if running in a container (Docker/Podman).
    
    Checks for common container indicators:
    - /.dockerenv file
    - /run/.containerenv file (Podman)
    - cgroup containing 'docker' or 'containerd'
    - CONTAINER environment variable
    """
    # Check for container environment variable (set in our Dockerfile)
    if os.environ.get("CONTAINER") or os.environ.get("container"):
        return True
    
    # Check for Docker
    if os.path.exists("/.dockerenv"):
        return True
    
    # Check for Podman
    if os.path.exists("/run/.containerenv"):
        return True
    
    # Check cgroup (Linux containers)
    try:
        with open("/proc/1/cgroup", "r") as f:
            content = f.read()
            if "docker" in content or "containerd" in content or "libpod" in content:
                return True
    except (FileNotFoundError, PermissionError):
        pass
    
    return False


def get_recordings_dir() -> Path:
    """Get the recordings directory based on environment.
    
    Returns:
        /app/recordings in container, ~/recordings (or RECORDINGS_DIR) on host.
    """
    if is_container_environment():
        recordings_dir = CONTAINER_RECORDINGS_DIR
    else:
        recordings_dir = HOST_RECORDINGS_DIR
    
    # Ensure directory exists
    recordings_dir.mkdir(parents=True, exist_ok=True)
    return recordings_dir


def get_ffmpeg_path() -> str:
    """Find ffmpeg executable.
    
    Raises:
        RuntimeError: If ffmpeg is not found.
    """
    # Common paths to check
    paths = [
        "/opt/homebrew/bin/ffmpeg",  # macOS Homebrew (Apple Silicon)
        "/usr/local/bin/ffmpeg",      # macOS Homebrew (Intel) / Linux manual install
        "/usr/bin/ffmpeg",            # Linux package manager
        "ffmpeg"                       # In PATH
    ]
    
    for path in paths:
        try:
            subprocess.run([path, "-version"], capture_output=True, check=True)
            return path
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    
    raise RuntimeError(
        "ffmpeg not found. Please install:\n"
        "  macOS: brew install ffmpeg\n"
        "  Ubuntu/Debian: sudo apt install ffmpeg\n"
        "  Windows: choco install ffmpeg"
    )


def get_ffprobe_path() -> str:
    """Find ffprobe executable (usually alongside ffmpeg)."""
    ffmpeg = get_ffmpeg_path()
    return ffmpeg.replace("ffmpeg", "ffprobe")


def get_media_url(file_path: Path) -> Optional[str]:
    """Generate a URL to access a media file via the HTTP server.
    
    Only works when running in a container with the video server.
    Returns None if not in container or file is not in recordings directory.
    
    Args:
        file_path: Path to the media file.
        
    Returns:
        URL string or None.
    """
    if not is_container_environment():
        return None
    
    try:
        # Check if file is under recordings dir
        rel_path = file_path.resolve().relative_to(CONTAINER_RECORDINGS_DIR.resolve())
        
        # Use HTTPS for public domains, HTTP for localhost
        if VIDEO_SERVER_HOST in ("localhost", "127.0.0.1"):
            return f"http://{VIDEO_SERVER_HOST}:{VIDEO_SERVER_PORT}/videos/{rel_path}"
        else:
            # Public domain - use HTTPS without port (reverse proxy handles SSL)
            return f"https://{VIDEO_SERVER_HOST}/videos/{rel_path}"
    except ValueError:
        # File is not in recordings directory
        return None
