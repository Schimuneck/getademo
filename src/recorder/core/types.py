"""
Core types - shared dataclasses used across the project.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import subprocess


@dataclass
class WindowBounds:
    """Window position and size."""
    x: int
    y: int
    width: int
    height: int


@dataclass
class WindowInfo:
    """Information about a window."""
    title: str
    window_id: str
    pid: Optional[int]
    bounds: Optional[WindowBounds]
    app_name: Optional[str] = None


@dataclass
class RecordingResult:
    """Result of a recording operation."""
    success: bool
    message: str
    file_path: Optional[Path] = None
    url: Optional[str] = None
    duration: Optional[float] = None
    file_size: Optional[float] = None


@dataclass
class RecordingState:
    """Global state for an active recording session."""
    process: Optional[subprocess.Popen] = None
    output_path: Optional[Path] = None
    start_time: Optional[datetime] = None
    log_file: Optional[Any] = None
    last_file_size: int = 0
    window_title: Optional[str] = None
    
    def is_recording(self) -> bool:
        """Check if a recording is currently in progress."""
        return self.process is not None and self.process.poll() is None
    
    def reset(self) -> None:
        """Reset the recording state."""
        if self.log_file is not None:
            try:
                self.log_file.close()
            except Exception:
                pass
        self.process = None
        self.output_path = None
        self.start_time = None
        self.log_file = None
        self.last_file_size = 0
        self.window_title = None
