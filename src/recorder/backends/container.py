"""
Container backend - for Docker/Podman with Xvfb virtual display.

Uses x11grab to capture from the Xvfb display where Playwright renders.
"""

import os
from pathlib import Path
from typing import List, Optional, Tuple

from .base import RecordingBackend
from ..core.types import WindowBounds
from ..core.config import (
    CONTAINER_RECORDINGS_DIR,
    VIDEO_SERVER_HOST,
    VIDEO_SERVER_PORT,
)


class ContainerBackend(RecordingBackend):
    """Recording backend for container environments.
    
    Features:
    - Uses x11grab to capture from Xvfb display (:99)
    - Captures from y=60 to skip Firefox window decorations
    - Returns HTTP URLs via the video server
    """
    
    # Browser window patterns to detect
    BROWSER_PATTERNS = ["Nightly", "Firefox", "Chromium", "Chrome"]
    
    def get_name(self) -> str:
        return "Container (Xvfb + x11grab)"
    
    def get_recordings_dir(self) -> Path:
        CONTAINER_RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        return CONTAINER_RECORDINGS_DIR
    
    def detect_browser_window(self) -> Optional[str]:
        """Detect browser window in the Xvfb display."""
        from ..utils.window_manager import get_window_id
        
        for pattern in self.BROWSER_PATTERNS:
            try:
                if get_window_id(pattern):
                    return pattern
            except Exception:
                continue
        return None
    
    def get_capture_args(
        self,
        window_title: str,
        fps: int = 30
    ) -> Tuple[List[str], Optional[str], Optional[str]]:
        """Get x11grab capture arguments.
        
        Captures from the Xvfb display with offset to skip window decorations.
        """
        from ..utils.window_manager import get_window_id, get_window_bounds
        
        # Verify window exists
        window_id = get_window_id(window_title)
        if not window_id:
            return [], None, f"Window '{window_title}' not found. Use list_windows to see available windows."
        
        # Get window bounds
        try:
            bounds = get_window_bounds(window_title)
            display = os.environ.get("DISPLAY", ":99")
            
            # Ensure dimensions are even (FFmpeg requirement)
            width = bounds.width if bounds.width % 2 == 0 else bounds.width + 1
            height = bounds.height if bounds.height % 2 == 0 else bounds.height + 1
            
            # Position: capture from near origin if window is there
            x = 0 if bounds.x < 50 else bounds.x
            y = 0 if bounds.y < 50 else bounds.y
            
            return [
                "-f", "x11grab",
                "-video_size", f"{width}x{height}",
                "-framerate", str(fps),
                "-i", f"{display}.0+{x},{y}",
            ], None, None
            
        except Exception as e:
            return [], None, f"Could not get window bounds: {e}"
    
    def get_window_bounds(self, window_title: str) -> Optional[WindowBounds]:
        """Get window bounds using wmctrl/xdotool."""
        from ..utils.window_manager import get_window_bounds
        try:
            return get_window_bounds(window_title)
        except Exception:
            return None
    
    def focus_window(self, window_title: str) -> bool:
        """Focus window using wmctrl."""
        from ..utils.window_manager import focus_window
        try:
            return focus_window(window_title)
        except Exception:
            return False
    
    def get_media_url(self, file_path: Path) -> Optional[str]:
        """Generate HTTP URL for accessing the media file."""
        try:
            rel_path = file_path.resolve().relative_to(CONTAINER_RECORDINGS_DIR.resolve())
            
            if VIDEO_SERVER_HOST in ("localhost", "127.0.0.1"):
                return f"http://{VIDEO_SERVER_HOST}:{VIDEO_SERVER_PORT}/videos/{rel_path}"
            else:
                # Public domain - use HTTPS
                return f"https://{VIDEO_SERVER_HOST}/videos/{rel_path}"
        except ValueError:
            return None
