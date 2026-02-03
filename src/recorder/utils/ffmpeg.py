"""
FFmpeg utilities - helpers for video/audio processing.
"""

import json
import subprocess
from pathlib import Path
from typing import Optional

from ..core.config import get_ffmpeg_path as _get_ffmpeg_path


def get_ffmpeg_path() -> str:
    """Get the path to ffmpeg executable."""
    return _get_ffmpeg_path()


def get_ffprobe_path() -> str:
    """Get the path to ffprobe executable."""
    return get_ffmpeg_path().replace("ffmpeg", "ffprobe")


async def get_audio_duration(path: Path) -> float:
    """Get audio file duration in seconds."""
    try:
        ffprobe = get_ffprobe_path()
        result = subprocess.run(
            [ffprobe, "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def get_media_info(path: Path) -> Optional[dict]:
    """Get detailed media file information.
    
    Returns dict with:
    - duration: float (seconds)
    - size_mb: float
    - video: dict with width, height, fps, codec (if video stream exists)
    - audio: dict with sample_rate, channels, codec (if audio stream exists)
    """
    if not path.exists():
        return None
    
    ffprobe = get_ffprobe_path()
    
    cmd = [
        ffprobe, "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        str(path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        return None
    
    info = json.loads(result.stdout)
    fmt = info.get("format", {})
    streams = info.get("streams", [])
    
    output = {
        "duration": float(fmt.get("duration", 0)),
        "size_mb": int(fmt.get("size", 0)) / (1024 * 1024),
    }
    
    # Find video and audio streams
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    
    if video_stream:
        output["video"] = {
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "fps": video_stream.get("r_frame_rate"),
            "codec": video_stream.get("codec_name"),
        }
    
    if audio_stream:
        output["audio"] = {
            "sample_rate": audio_stream.get("sample_rate"),
            "channels": audio_stream.get("channels"),
            "codec": audio_stream.get("codec_name"),
        }
    
    return output
