"""
Core module - shared types and configuration.
"""

from .types import (
    WindowBounds,
    WindowInfo,
    RecordingResult,
    RecordingState,
)
from .config import (
    get_recordings_dir,
    get_ffmpeg_path,
    is_container_environment,
    get_media_url,
    VIDEO_SERVER_PORT,
    VIDEO_SERVER_HOST,
)

__all__ = [
    # Types
    "WindowBounds",
    "WindowInfo",
    "RecordingResult",
    "RecordingState",
    # Config
    "get_recordings_dir",
    "get_ffmpeg_path",
    "is_container_environment",
    "get_media_url",
    "VIDEO_SERVER_PORT",
    "VIDEO_SERVER_HOST",
]
