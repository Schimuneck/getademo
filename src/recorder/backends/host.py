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
        1. Traditional browsers (Chrome, Firefox, Safari, etc.) - ALWAYS prefer these
           since they're standalone and more reliable to capture
        2. Windows with URL-like titles (indicates browser content)
        3. Cursor IDE - ONLY as last resort when using cursor-browser-extension
        
        The key insight: if a standalone browser (Chrome, Firefox, etc.) is open,
        the user is likely using Playwright MCP or manual browsing, NOT the embedded
        cursor-browser-extension. Always prefer standalone browsers.
        """
        from ..utils.window_manager import list_windows
        
        try:
            windows = list_windows()
        except Exception:
            return None
        
        # Priority 1: Traditional browsers by app name
        # ALWAYS prefer standalone browsers over Cursor - they're more reliable
        # and indicate the user is using Playwright MCP or similar
        browser_apps = ["Google Chrome", "Firefox", "Safari", "Arc", "Brave", "Edge", "Chromium"]
        for win in windows:
            if win.app_name in browser_apps:
                return win.app_name
        
        # Priority 2: Any window with URL-like title (could be browser)
        for win in windows:
            title = (win.title or "").lower()
            if any(x in title for x in ['http', 'localhost', '.com', '.io', '.org']):
                # Skip Cursor windows with project names that happen to match
                if win.app_name != "Cursor":
                    return win.title[:50]  # Use first 50 chars as pattern
        
        # Priority 3: Cursor IDE - ONLY when no standalone browser is available
        # This is the fallback for cursor-browser-extension embedded browser
        for win in windows:
            if win.app_name == "Cursor":
                return "Cursor"
        
        return None
    
    def get_capture_args(
        self,
        window_title: str,
        fps: int = 30
    ) -> Tuple[List[str], Optional[str], Optional[str], Optional[Tuple[int, int]]]:
        """Get platform-specific capture arguments."""
        from ..utils.window_manager import get_window_id, get_window_bounds
        
        if sys.platform == "darwin":
            return self._get_macos_capture_args(window_title, fps)
        elif sys.platform == "linux":
            return self._get_linux_capture_args(window_title, fps)
        elif sys.platform == "win32":
            return self._get_windows_capture_args(window_title, fps)
        else:
            return [], None, f"Unsupported platform: {sys.platform}", None
    
    def _get_macos_capture_args(
        self,
        window_title: str,
        fps: int
    ) -> Tuple[List[str], Optional[str], Optional[str], Optional[Tuple[int, int]]]:
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
            return [], None, f"Window '{window_title}' not found: {e}", None
        
        # Get screen info to determine which monitor the window is on
        screen_info = self._get_macos_screens()
        nsscreen_index, crop_x, crop_y, scale_factor = self._find_screen_for_window(bounds, screen_info)
        
        # Get the screen we're capturing from - needed to clamp crop to capture dimensions
        capture_screen = next(
            (s for s in screen_info if s["index"] == nsscreen_index),
            screen_info[0] if screen_info else {"width": 1920, "height": 1080, "scale": 2}
        )
        capture_width = capture_screen["width"] * capture_screen.get("scale", scale_factor)
        capture_height = capture_screen["height"] * capture_screen.get("scale", scale_factor)
        
        # AVFoundation device indices vary: cameras come first, then "Capture screen 0", "Capture screen 1", etc.
        # Systems with OBS/virtual cameras may have screens at index 6+ - parse ffmpeg output to find the correct one
        avfoundation_index = self._get_avfoundation_screen_index(nsscreen_index)
        
        # Probe actual capture dimensions - NSScreen and AVFoundation can report different resolutions
        actual_capture_w, actual_capture_h = self._probe_avfoundation_dimensions(avfoundation_index)
        if actual_capture_w and actual_capture_h:
            capture_width = actual_capture_w
            capture_height = actual_capture_h
        
        # Scale dimensions for Retina displays (typically 2x on modern Macs)
        # FFmpeg captures at actual pixel resolution, not logical resolution
        scaled_width = bounds.width * scale_factor
        scaled_height = bounds.height * scale_factor
        scaled_crop_x = crop_x * scale_factor
        scaled_crop_y = crop_y * scale_factor
        
        # Clamp crop to capture dimensions - window bounds can exceed capture when coordinate
        # systems differ (e.g. CGWindowList vs NSScreen, or multi-monitor)
        max_width = int(capture_width - scaled_crop_x)
        max_height = int(capture_height - scaled_crop_y)
        scaled_width = min(scaled_width, max_width)
        scaled_height = min(scaled_height, max_height)
        scaled_width = max(2, scaled_width)
        scaled_height = max(2, scaled_height)
        
        # Ensure even dimensions for h264 encoding
        width = scaled_width if scaled_width % 2 == 0 else scaled_width - 1
        height = scaled_height if scaled_height % 2 == 0 else scaled_height - 1
        
        # Ensure even crop coordinates too
        crop_x_final = scaled_crop_x if scaled_crop_x % 2 == 0 else scaled_crop_x + 1
        crop_y_final = scaled_crop_y if scaled_crop_y % 2 == 0 else scaled_crop_y + 1
        
        # Final clamp: crop region must fit within capture
        if crop_x_final + width > capture_width or crop_y_final + height > capture_height:
            width = min(width, int(capture_width) - crop_x_final)
            height = min(height, int(capture_height) - crop_y_final)
            width = width if width % 2 == 0 else width - 1
            height = height if height % 2 == 0 else height - 1
            width = max(2, width)
            height = max(2, height)
        
        return [
            "-f", "avfoundation",
            "-capture_cursor", "1",
            "-framerate", str(fps),
            "-pixel_format", "uyvy422",
            "-i", f"{avfoundation_index}:none",
        ], f"crop={width}:{height}:{crop_x_final}:{crop_y_final}", None, (width, height)
    
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
    
    def _probe_avfoundation_dimensions(self, device_index: int) -> Tuple[Optional[int], Optional[int]]:
        """Probe actual capture dimensions from AVFoundation.
        
        Returns (width, height) or (None, None) if probe fails.
        """
        import subprocess
        import re
        
        try:
            result = subprocess.run(
                [
                    self._get_ffmpeg_path(),
                    "-f", "avfoundation",
                    "-i", f"{device_index}:none",
                    "-t", "0.001",
                    "-f", "null", "-",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            output = (result.stdout or "") + (result.stderr or "")
            # Match "3024x1964" from stream info like "Stream #0:0: Video: rawvideo ... 3024x1964"
            match = re.search(r"Stream #\d+:\d+.*?(\d{3,5})x(\d{3,5})", output)
            if match:
                return int(match.group(1)), int(match.group(2))
        except Exception:
            pass
        return None, None
    
    def _get_avfoundation_screen_index(self, nsscreen_index: int) -> int:
        """Get AVFoundation device index for the given NSScreen.
        
        AVFoundation device order varies: cameras (built-in, virtual, etc.) come first,
        then 'Capture screen 0', 'Capture screen 1', etc. Parse ffmpeg output to find
        the correct index instead of assuming screens start at 1.
        
        Args:
            nsscreen_index: 1-based NSScreen index (1 = first screen)
            
        Returns:
            AVFoundation device index for that screen
        """
        import subprocess
        import re
        
        try:
            result = subprocess.run(
                [self._get_ffmpeg_path(), "-f", "avfoundation", "-list_devices", "true", "-i", ""],
                capture_output=True, text=True, timeout=5
            )
            # FFmpeg outputs device list to stderr
            output = (result.stdout or "") + (result.stderr or "")
            # Match "[N] Capture screen M" - N is device index, M is screen number (0-based)
            # nsscreen_index 1 -> Capture screen 0, nsscreen_index 2 -> Capture screen 1, etc.
            target_screen_num = nsscreen_index - 1
            pattern = rf"\[\s*(\d+)\s*\]\s*Capture screen\s+{target_screen_num}\b"
            match = re.search(pattern, output)
            if match:
                return int(match.group(1))
        except Exception:
            pass
        # Fallback: assume screens start after cameras (legacy behavior for simple setups)
        return nsscreen_index
    
    def _get_ffmpeg_path(self) -> str:
        """Get path to ffmpeg executable."""
        from ..core.config import get_ffmpeg_path
        return get_ffmpeg_path()
    
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
    ) -> Tuple[List[str], Optional[str], Optional[str], Optional[Tuple[int, int]]]:
        """Linux: Use x11grab with native X11 display."""
        from ..utils.window_manager import get_window_id, get_window_bounds
        
        window_id = get_window_id(window_title)
        if not window_id:
            return [], None, f"Window '{window_title}' not found.", None
        
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
            ], None, None, None
            
        except Exception as e:
            return [], None, f"Could not get window bounds: {e}", None
    
    def _get_windows_capture_args(
        self,
        window_title: str,
        fps: int
    ) -> Tuple[List[str], Optional[str], Optional[str], Optional[Tuple[int, int]]]:
        """Windows: Use gdigrab with window title."""
        return [
            "-f", "gdigrab",
            "-framerate", str(fps),
            "-i", f"title={window_title}",
        ], None, None, None
    
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
