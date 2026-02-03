"""
Utils module - shared utilities.
"""

from .window_manager import (
    list_windows,
    focus_window,
    get_window_bounds,
    get_window_id,
    check_dependencies,
    WindowManagerError,
    DependencyMissingError,
    WindowNotFoundError,
)
from .ffmpeg import (
    get_ffmpeg_path,
    get_ffprobe_path,
    get_audio_duration,
    get_media_info,
)
from .protocol import (
    get_planning_guide,
    get_setup_guide,
    get_recording_guide,
    get_assembly_guide,
)

__all__ = [
    # Window manager
    "list_windows",
    "focus_window",
    "get_window_bounds",
    "get_window_id",
    "check_dependencies",
    "WindowManagerError",
    "DependencyMissingError",
    "WindowNotFoundError",
    # FFmpeg
    "get_ffmpeg_path",
    "get_ffprobe_path",
    "get_audio_duration",
    "get_media_info",
    # Protocol
    "get_planning_guide",
    "get_setup_guide",
    "get_recording_guide",
    "get_assembly_guide",
]
