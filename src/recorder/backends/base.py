"""
Base backend - abstract interface for recording operations.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple, List

from ..core.types import RecordingResult, RecordingState, WindowBounds


class RecordingBackend(ABC):
    """Abstract interface for environment-specific recording operations.
    
    Implementations:
    - ContainerBackend: For Docker/Podman with Xvfb
    - HostBackend: For native execution on macOS/Linux/Windows
    """
    
    def __init__(self):
        self._state = RecordingState()
    
    @property
    def state(self) -> RecordingState:
        """Get the current recording state."""
        return self._state
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the backend name for logging/display."""
        pass
    
    @abstractmethod
    def get_recordings_dir(self) -> Path:
        """Get the directory where recordings are stored."""
        pass
    
    @abstractmethod
    def detect_browser_window(self) -> Optional[str]:
        """Find a browser window to record.
        
        Returns:
            Window title/pattern that was found, or None if no browser found.
        """
        pass
    
    @abstractmethod
    def get_capture_args(
        self,
        window_title: str,
        fps: int = 30
    ) -> Tuple[List[str], Optional[str], Optional[str]]:
        """Get FFmpeg capture arguments for the specified window.
        
        Args:
            window_title: Window title pattern to capture.
            fps: Frames per second for recording.
            
        Returns:
            Tuple of (ffmpeg_args, crop_filter, error_message).
            If error_message is set, the other values should be ignored.
        """
        pass
    
    @abstractmethod
    def get_window_bounds(self, window_title: str) -> Optional[WindowBounds]:
        """Get the bounds of a window.
        
        Args:
            window_title: Window title pattern.
            
        Returns:
            WindowBounds or None if not found.
        """
        pass
    
    @abstractmethod
    def focus_window(self, window_title: str) -> bool:
        """Bring a window to the foreground.
        
        Args:
            window_title: Window title pattern.
            
        Returns:
            True if successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def get_media_url(self, file_path: Path) -> Optional[str]:
        """Get URL to access a media file.
        
        Args:
            file_path: Path to the media file.
            
        Returns:
            URL string (container mode) or None (host mode).
        """
        pass
    
    async def start_recording(
        self,
        output_path: Path,
        window_title: str,
        fps: int = 30
    ) -> RecordingResult:
        """Start screen recording.
        
        This is a template method that uses get_capture_args().
        Subclasses can override for custom behavior.
        
        Args:
            output_path: Where to save the recording.
            window_title: Window to record.
            fps: Frames per second.
            
        Returns:
            RecordingResult with success status and message.
        """
        import asyncio
        import subprocess
        from datetime import datetime
        from ..core.config import get_ffmpeg_path
        
        if self._state.is_recording():
            return RecordingResult(
                success=False,
                message="Recording already in progress. Stop it first."
            )
        
        # Get capture arguments
        capture_args, crop_filter, error = self.get_capture_args(window_title, fps)
        if error:
            return RecordingResult(success=False, message=error)
        
        # Try to focus the window
        try:
            self.focus_window(window_title)
            await asyncio.sleep(0.3)
        except Exception:
            pass  # Continue anyway
        
        # Get window bounds for output size
        bounds = self.get_window_bounds(window_title)
        if bounds:
            width, height = bounds.width, bounds.height
        else:
            width, height = 1920, 1080
        
        # Ensure even dimensions for h264 encoding
        width = width if width % 2 == 0 else width - 1
        height = height if height % 2 == 0 else height - 1
        
        # Build FFmpeg command
        ffmpeg = get_ffmpeg_path()
        cmd = [ffmpeg, "-y", *capture_args]
        
        # Add video filter if needed
        video_filters = []
        if crop_filter:
            video_filters.append(crop_filter)
        video_filters.append(f"scale={width}:{height}")
        
        if video_filters:
            cmd.extend(["-vf", ",".join(video_filters)])
        
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-movflags", "frag_keyframe+empty_moov",
            str(output_path)
        ])
        
        # Create log file
        log_path = output_path.with_suffix('.ffmpeg.log')
        log_file = open(log_path, 'w')
        
        # Start the process
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=log_file,
            stderr=subprocess.STDOUT
        )
        
        # Update state
        self._state.process = process
        self._state.output_path = output_path
        self._state.start_time = datetime.now()
        self._state.log_file = log_file
        self._state.last_file_size = 0
        self._state.window_title = window_title
        
        # Wait and check if started successfully
        await asyncio.sleep(0.5)
        
        if process.poll() is not None:
            # Process died
            log_file.close()
            try:
                with open(log_path, 'r') as f:
                    error_msg = f.read() or "Unknown error"
            except Exception:
                error_msg = "Unknown error"
            
            self._state.reset()
            return RecordingResult(
                success=False,
                message=f"Recording failed to start: {error_msg}"
            )
        
        url = self.get_media_url(output_path)
        return RecordingResult(
            success=True,
            message=f"Recording started",
            file_path=output_path,
            url=url
        )
    
    async def stop_recording(self) -> RecordingResult:
        """Stop the current recording.
        
        Returns:
            RecordingResult with file info.
        """
        import asyncio
        import signal
        from datetime import datetime
        
        if not self._state.is_recording():
            return RecordingResult(
                success=False,
                message="No recording in progress."
            )
        
        process = self._state.process
        output_path = self._state.output_path
        start_time = self._state.start_time
        
        duration = (datetime.now() - start_time).total_seconds() if start_time else 0
        
        # Stop FFmpeg gracefully
        stopped = False
        
        # Method 1: Send 'q' to stdin
        try:
            if process.stdin:
                process.stdin.write(b'q')
                process.stdin.flush()
                for _ in range(30):
                    await asyncio.sleep(0.1)
                    if process.poll() is not None:
                        stopped = True
                        break
        except (BrokenPipeError, OSError):
            pass
        
        # Method 2: SIGINT
        if not stopped:
            try:
                process.send_signal(signal.SIGINT)
                for _ in range(20):
                    await asyncio.sleep(0.1)
                    if process.poll() is not None:
                        stopped = True
                        break
            except (ProcessLookupError, OSError):
                pass
        
        # Method 3: SIGTERM
        if not stopped:
            try:
                process.terminate()
                for _ in range(20):
                    await asyncio.sleep(0.1)
                    if process.poll() is not None:
                        stopped = True
                        break
            except (ProcessLookupError, OSError):
                pass
        
        # Method 4: Kill
        if not stopped:
            try:
                process.kill()
                await asyncio.sleep(0.5)
            except (ProcessLookupError, OSError):
                pass
        
        # Final verification: ensure process is truly dead
        pid = process.pid
        if pid and process.poll() is None:
            # Process still running! Force kill by PID
            import os
            try:
                os.kill(pid, signal.SIGKILL)
                await asyncio.sleep(0.3)
            except (ProcessLookupError, OSError):
                pass
        
        # Close log file and clean up
        log_path = None
        if self._state.log_file:
            try:
                log_path = Path(self._state.log_file.name)
                self._state.log_file.close()
            except Exception:
                pass
        
        # Get file size
        try:
            file_size = output_path.stat().st_size / (1024 * 1024) if output_path and output_path.exists() else 0
        except Exception:
            file_size = 0
        
        # Clean up log file if recording succeeded
        if log_path and log_path.exists() and file_size > 0:
            try:
                log_path.unlink()
            except Exception:
                pass
        
        # Reset state
        self._state.reset()
        
        url = self.get_media_url(output_path) if output_path else None
        
        return RecordingResult(
            success=True,
            message="Recording stopped",
            file_path=output_path,
            url=url,
            duration=duration,
            file_size=file_size
        )
    
    def get_recording_status(self) -> RecordingResult:
        """Get the current recording status.
        
        Returns:
            RecordingResult with status info.
        """
        from datetime import datetime
        
        if not self._state.is_recording():
            return RecordingResult(
                success=True,
                message="No recording in progress."
            )
        
        duration = 0
        if self._state.start_time:
            duration = (datetime.now() - self._state.start_time).total_seconds()
        
        # Check file size and growth
        current_size = 0
        size_growing = True
        try:
            if self._state.output_path and self._state.output_path.exists():
                current_size = self._state.output_path.stat().st_size
                if self._state.last_file_size > 0 and current_size <= self._state.last_file_size:
                    size_growing = False
                self._state.last_file_size = current_size
        except Exception:
            pass
        
        health = "Healthy (file growing)" if size_growing else "Warning: File not growing!"
        
        return RecordingResult(
            success=True,
            message=f"Recording in progress - {health}",
            file_path=self._state.output_path,
            duration=duration,
            file_size=current_size / (1024 * 1024)
        )
