"""
Host backend - for native execution on macOS/Linux/Windows.

Uses platform-specific capture:
- macOS: AVFoundation
- Linux: x11grab (native X11, not Xvfb)
- Windows: gdigrab
"""

import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from .base import RecordingBackend
from ..core.types import WindowBounds
from ..core.config import HOST_RECORDINGS_DIR


class HostBackend(RecordingBackend):
    """Recording backend for host machine (non-container) environments.
    
    Features:
    - Uses native screen capture for each platform
    - Detects cursor-browser-extension and other browsers
    - Returns local file paths (no HTTP URLs)
    """
    
    # Browser patterns including cursor-browser-extension
    BROWSER_PATTERNS = [
        # Cursor's browser often shows page title
        "Chrome", "Chromium", "Safari", "Firefox", 
        "Arc", "Brave", "Edge", "Nightly",
        # Common page titles that might indicate the browser
        "localhost", "http://", "https://",
    ]
    
    def get_name(self) -> str:
        platform_names = {
            "darwin": "macOS (AVFoundation)",
            "linux": "Linux (x11grab)",
            "win32": "Windows (gdigrab)",
        }
        return f"Host - {platform_names.get(sys.platform, sys.platform)}"
    
    def get_recordings_dir(self) -> Path:
        HOST_RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        return HOST_RECORDINGS_DIR
    
    def detect_browser_window(self) -> Optional[str]:
        """Detect browser window on the host system.
        
        Priority order:
        1. Cursor IDE (when using cursor-browser-extension, browser is embedded)
        2. Traditional browsers (Chrome, Firefox, Safari, etc.)
        3. Any window with URL-like title
        """
        from ..utils.window_manager import list_windows
        
        try:
            windows = list_windows()
        except Exception:
            return None
        
        # Priority 1: Cursor IDE (embedded browser via cursor-browser-extension)
        # When running in Cursor with cursor-browser-extension, we need to record
        # the Cursor window itself since the browser is embedded
        for win in windows:
            if win.app_name == "Cursor":
                return "Cursor"
        
        # Priority 2: Traditional browsers by app name
        browser_apps = ["Google Chrome", "Firefox", "Safari", "Arc", "Brave", "Edge", "Chromium"]
        for win in windows:
            if win.app_name in browser_apps:
                return win.app_name
        
        # Priority 3: Any window with URL-like title
        for win in windows:
            title = (win.title or "").lower()
            if any(x in title for x in ['http', 'localhost', '.com', '.io', '.org']):
                return win.title[:50]  # Use first 50 chars as pattern
        
        return None
    
    def get_capture_args(
        self,
        window_title: str,
        fps: int = 30
    ) -> Tuple[List[str], Optional[str], Optional[str]]:
        """Get platform-specific capture arguments."""
        from ..utils.window_manager import get_window_id, get_window_bounds
        
        if sys.platform == "darwin":
            return self._get_macos_capture_args(window_title, fps)
        elif sys.platform == "linux":
            return self._get_linux_capture_args(window_title, fps)
        elif sys.platform == "win32":
            return self._get_windows_capture_args(window_title, fps)
        else:
            return [], None, f"Unsupported platform: {sys.platform}"
    
    def _get_macos_capture_args(
        self,
        window_title: str,
        fps: int
    ) -> Tuple[List[str], Optional[str], Optional[str]]:
        """macOS: Use AVFoundation with multi-monitor support.
        
        Detects which screen the window is on and captures that screen,
        using relative coordinates for cropping.
        
        Important considerations:
        - AVFoundation uses 0-based screen indexing (screen 0, screen 1, etc.)
        - macOS Retina displays capture at 2x resolution (e.g., 1728 logical = 3456 actual)
        - Window bounds are in logical (non-Retina) coordinates
        - Crop filter needs actual pixel coordinates (scaled by Retina factor)
        """
        from ..utils.window_manager import get_window_bounds
        
        try:
            bounds = get_window_bounds(window_title)
        except Exception as e:
            return [], None, f"Window '{window_title}' not found: {e}"
        
        # Get screen info to determine which monitor the window is on
        screen_info = self._get_macos_screens()
        screen_index, crop_x, crop_y, scale_factor = self._find_screen_for_window(bounds, screen_info)
        
        # AVFoundation device indices: 0=camera, 1=screen0, 2=screen1, etc.
        # NSScreen uses 1-based indexing which happens to match AVFoundation screen devices
        # (because camera is at index 0, screens start at index 1)
        avfoundation_index = screen_index
        
        # Scale dimensions for Retina displays (typically 2x on modern Macs)
        # FFmpeg captures at actual pixel resolution, not logical resolution
        scaled_width = bounds.width * scale_factor
        scaled_height = bounds.height * scale_factor
        scaled_crop_x = crop_x * scale_factor
        scaled_crop_y = crop_y * scale_factor
        
        # Ensure even dimensions for h264 encoding
        width = scaled_width if scaled_width % 2 == 0 else scaled_width - 1
        height = scaled_height if scaled_height % 2 == 0 else scaled_height - 1
        
        # Ensure even crop coordinates too
        crop_x_final = scaled_crop_x if scaled_crop_x % 2 == 0 else scaled_crop_x + 1
        crop_y_final = scaled_crop_y if scaled_crop_y % 2 == 0 else scaled_crop_y + 1
        
        return [
            "-f", "avfoundation",
            "-capture_cursor", "1",
            "-framerate", str(fps),
            "-pixel_format", "uyvy422",
            "-i", f"{avfoundation_index}:none",
        ], f"crop={width}:{height}:{crop_x_final}:{crop_y_final}", None
    
    def _get_macos_screens(self) -> List[dict]:
        """Get list of screens with their bounds and scale factor on macOS.
        
        Returns screens with:
        - index: 1-based index (matches NSScreen order)
        - x, y: position in global coordinate space
        - width, height: logical dimensions (not Retina-scaled)
        - scale: backing scale factor (1 for standard, 2 for Retina)
        """
        import subprocess
        
        script = '''
use framework "AppKit"
set screenList to ""
set screens to current application's NSScreen's screens()
repeat with i from 1 to count of screens
    set scr to item i of screens
    set frame to scr's frame()
    set origin to item 1 of frame
    set sz to item 2 of frame
    set x to item 1 of origin as integer
    set y to item 2 of origin as integer
    set w to item 1 of sz as integer
    set h to item 2 of sz as integer
    set scaleFactor to scr's backingScaleFactor() as integer
    set screenList to screenList & x & "," & y & "," & w & "," & h & "," & scaleFactor & linefeed
end repeat
return screenList
'''
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=5
            )
            screens = []
            for i, line in enumerate(result.stdout.strip().split("\n")):
                if line:
                    parts = line.split(",")
                    if len(parts) >= 4:
                        scale = int(parts[4]) if len(parts) > 4 else 2  # Default to 2x for Retina
                        screens.append({
                            "index": i + 1,  # 1-based index for NSScreen
                            "x": int(parts[0]),
                            "y": int(parts[1]),
                            "width": int(parts[2]),
                            "height": int(parts[3]),
                            "scale": scale
                        })
            return screens if screens else [{"index": 1, "x": 0, "y": 0, "width": 1920, "height": 1080, "scale": 2}]
        except Exception:
            return [{"index": 1, "x": 0, "y": 0, "width": 1920, "height": 1080, "scale": 2}]
    
    def _find_screen_for_window(self, bounds, screens: List[dict]) -> Tuple[int, int, int, int]:
        """Find which screen contains the window and calculate relative coordinates.
        
        Uses overlap calculation to find the screen with most window coverage.
        
        Returns: (screen_index, relative_x, relative_y, scale_factor)
        """
        best_screen = None
        best_overlap = 0
        
        for screen in screens:
            # Calculate overlap area between window and screen
            overlap_left = max(bounds.x, screen["x"])
            overlap_right = min(bounds.x + bounds.width, screen["x"] + screen["width"])
            overlap_top = max(bounds.y, screen["y"])
            overlap_bottom = min(bounds.y + bounds.height, screen["y"] + screen["height"])
            
            if overlap_right > overlap_left and overlap_bottom > overlap_top:
                overlap_area = (overlap_right - overlap_left) * (overlap_bottom - overlap_top)
                if overlap_area > best_overlap:
                    best_overlap = overlap_area
                    best_screen = screen
        
        if best_screen:
            # Calculate relative coordinates within the screen
            relative_x = bounds.x - best_screen["x"]
            relative_y = bounds.y - best_screen["y"]
            
            # Clamp to screen bounds (handle windows partially off-screen)
            relative_x = max(0, relative_x)
            relative_y = max(0, relative_y)
            
            scale = best_screen.get("scale", 2)  # Default to 2x Retina
            return best_screen["index"], relative_x, relative_y, scale
        
        # Default to first screen if no overlap found
        return 1, max(0, bounds.x), max(0, bounds.y), 2
    
    def list_screens(self) -> List[dict]:
        """List all available screens for recording.
        
        Returns list of screens with index, position, and dimensions.
        Useful for debugging multi-monitor setups.
        """
        return self._get_macos_screens() if sys.platform == "darwin" else []
    
    def _get_linux_capture_args(
        self,
        window_title: str,
        fps: int
    ) -> Tuple[List[str], Optional[str], Optional[str]]:
        """Linux: Use x11grab with native X11 display."""
        from ..utils.window_manager import get_window_id, get_window_bounds
        
        window_id = get_window_id(window_title)
        if not window_id:
            return [], None, f"Window '{window_title}' not found."
        
        try:
            bounds = get_window_bounds(window_title)
            display = os.environ.get("DISPLAY", ":0")
            
            # Ensure even dimensions
            width = bounds.width if bounds.width % 2 == 0 else bounds.width + 1
            height = bounds.height if bounds.height % 2 == 0 else bounds.height + 1
            
            return [
                "-f", "x11grab",
                "-video_size", f"{width}x{height}",
                "-framerate", str(fps),
                "-i", f"{display}+{bounds.x},{bounds.y}",
            ], None, None
            
        except Exception as e:
            return [], None, f"Could not get window bounds: {e}"
    
    def _get_windows_capture_args(
        self,
        window_title: str,
        fps: int
    ) -> Tuple[List[str], Optional[str], Optional[str]]:
        """Windows: Use gdigrab with window title."""
        return [
            "-f", "gdigrab",
            "-framerate", str(fps),
            "-i", f"title={window_title}",
        ], None, None
    
    def get_window_bounds(self, window_title: str) -> Optional[WindowBounds]:
        """Get window bounds using platform-specific methods."""
        from ..utils.window_manager import get_window_bounds
        try:
            return get_window_bounds(window_title)
        except Exception:
            return None
    
    def focus_window(self, window_title: str) -> bool:
        """Focus window using platform-specific methods."""
        from ..utils.window_manager import focus_window
        try:
            return focus_window(window_title)
        except Exception:
            return False
    
    def get_media_url(self, file_path: Path) -> Optional[str]:
        """Host mode doesn't have HTTP server, return None."""
        return None
