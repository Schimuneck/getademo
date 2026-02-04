"""
Recording tools - start, stop, and status for screen recording.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional


def _kill_orphaned_ffmpeg_processes(recordings_dir: Path) -> int:
    """Kill any orphaned ffmpeg processes writing to the recordings directory.
    
    Returns the number of processes killed.
    """
    import subprocess
    import signal
    import os
    
    killed = 0
    try:
        # Find ffmpeg processes
        result = subprocess.run(
            ["pgrep", "-f", "ffmpeg"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return 0
        
        pids = [int(pid.strip()) for pid in result.stdout.strip().split('\n') if pid.strip()]
        
        for pid in pids:
            try:
                # Check if this ffmpeg is writing to our recordings dir
                cmdline_result = subprocess.run(
                    ["ps", "-p", str(pid), "-o", "args="],
                    capture_output=True, text=True
                )
                cmdline = cmdline_result.stdout.strip()
                
                if str(recordings_dir) in cmdline:
                    os.kill(pid, signal.SIGKILL)
                    killed += 1
            except (ProcessLookupError, PermissionError, OSError):
                pass
    except Exception:
        pass
    
    return killed


def register_recording_tools(mcp, backend):
    """Register recording tools with the MCP server."""
    
    @mcp.tool(description="Start video recording. REQUIRES window_title parameter. Perform actions AFTER calling this. Keep scenes short (10-30s).")
    async def start_recording(filename: str = None, window_title: str = None) -> str:
        """Start video recording.
        
        Args:
            filename: Output filename (e.g., "scene1.mp4"). Auto-generated if not provided.
            window_title: REQUIRED. Window to record (e.g., "Google Chrome", "Firefox", "Safari").
                          Use list_windows() to see available windows.
        """
        # Safety check: kill any orphaned ffmpeg processes from previous failed recordings
        recordings_dir = backend.get_recordings_dir()
        killed = _kill_orphaned_ffmpeg_processes(recordings_dir)
        orphan_warning = ""
        if killed > 0:
            import asyncio
            await asyncio.sleep(0.5)  # Give processes time to die
            orphan_warning = f"\n(Cleaned up {killed} orphaned recording process{'es' if killed > 1 else ''})\n"
        
        # Require window_title to prevent recording wrong window
        if not window_title:
            return (
                "ERROR: window_title parameter is REQUIRED.\n\n"
                "You must specify which window to record. Examples:\n"
                "  start_recording(window_title='Google Chrome')\n"
                "  start_recording(window_title='Firefox')\n"
                "  start_recording(window_title='Safari')\n\n"
                "Use list_windows() to see all available windows and their exact names."
            )
        
        # Auto-generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.mp4"
        
        # Ensure .mp4 extension
        if not filename.endswith('.mp4'):
            filename += '.mp4'
        
        out_path = backend.get_recordings_dir() / filename
        
        result = await backend.start_recording(out_path, window_title)
        
        if not result.success:
            return f"Recording failed: {result.message}"
        
        url_info = f"URL: {result.url}\n" if result.url else ""
        bounds = backend.get_window_bounds(window_title)
        size_info = f"{bounds.width}x{bounds.height}" if bounds else "unknown"
        
        return (
            f"Recording started!{orphan_warning}\n"
            f"Window: {window_title}\n"
            f"Output: {filename}\n"
            f"{url_info}"
            f"Resolution: {size_info} @ 30fps\n"
            f"Started at: {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"Use 'stop_recording' when done."
        )
    
    @mcp.tool(description="Stop the current recording and save the video file.")
    async def stop_recording() -> str:
        """Stop screen recording."""
        result = await backend.stop_recording()
        
        if not result.success:
            return result.message
        
        url_info = f"URL: {result.url}\n" if result.url else ""
        filename = result.file_path.name if result.file_path else "unknown"
        
        return (
            f"Recording stopped!\n"
            f"Output: {filename}\n"
            f"{url_info}"
            f"Duration: {result.duration:.1f} seconds\n"
            f"File size: {result.file_size:.1f} MB"
        )
    
    @mcp.tool(description="Check if a recording is in progress.")
    async def recording_status() -> str:
        """Get recording status with health monitoring."""
        result = backend.get_recording_status()
        
        if "No recording" in result.message:
            return "No recording in progress."
        
        filename = result.file_path.name if result.file_path else "unknown"
        
        return (
            f"Recording in progress\n"
            f"Output: {filename}\n"
            f"Duration: {result.duration:.1f} seconds\n"
            f"File size: {result.file_size:.2f} MB\n"
            f"Status: {result.message}"
        )
    
    # Only register list_screens for host mode (not needed in container)
    if hasattr(backend, 'list_screens'):
        @mcp.tool(description="List available screens/monitors for recording. Useful for multi-monitor setups on host machine.")
        async def list_screens() -> str:
            """List available screens for recording (host mode only)."""
            screens = backend.list_screens()
            if not screens:
                return "No screens detected."
            
            lines = ["Available Screens:\n"]
            for s in screens:
                scale = s.get('scale', 1)
                scale_info = f" (Retina {scale}x)" if scale > 1 else ""
                lines.append(
                    f"  Screen {s['index']}: {s['width']}x{s['height']} at position ({s['x']}, {s['y']}){scale_info}"
                )
            
            lines.append("\nRecording auto-detects which screen contains the target window.")
            lines.append("Retina displays capture at scaled resolution (e.g., 2x = double pixels).")
            lines.append("Use list_windows() to see available windows and their positions.")
            
            return "\n".join(lines)
