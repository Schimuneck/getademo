#!/usr/bin/env python3
"""
getademo - MCP Server for Demo Recording

Provides tools for:
- Screen recording (start/stop)
- Text-to-speech generation (OpenAI or Edge TTS)
- Video/audio composition (merge, replace audio, trim)

Container Support:
- When running in a container with Xvfb, captures the virtual display
- Designed to work with Playwright MCP in the same container
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .protocol import (
    get_planning_guide,
    get_setup_guide,
    get_recording_guide,
    get_assembly_guide,
)
from . import window_manager

# Default recordings directory and video server config
CONTAINER_RECORDINGS_DIR = Path("/app/recordings")
VIDEO_SERVER_PORT = int(os.environ.get("VIDEO_SERVER_PORT", 8080))
VIDEO_SERVER_HOST = os.environ.get("VIDEO_SERVER_HOST", "localhost")


def get_video_url(file_path: Path) -> Optional[str]:
    """Generate a URL to access a video file via the HTTP server.
    
    Only works when running in a container with the video server.
    Returns None if the file is not in the recordings directory.
    """
    if not is_container_environment():
        return None
    
    try:
        # Check if file is under recordings dir
        rel_path = file_path.resolve().relative_to(CONTAINER_RECORDINGS_DIR.resolve())
        return f"http://{VIDEO_SERVER_HOST}:{VIDEO_SERVER_PORT}/videos/{rel_path}"
    except ValueError:
        # File is not in recordings directory
        return None


def get_default_output_path(filename: str) -> Path:
    """Get the default output path for recordings.
    
    In container: saves to /app/recordings/<filename>
    On host: saves to current directory
    """
    if is_container_environment():
        return CONTAINER_RECORDINGS_DIR / filename
    return Path.cwd() / filename


# Global state for recording
_recording_process: Optional[subprocess.Popen] = None
_recording_path: Optional[Path] = None
_recording_start_time: Optional[datetime] = None
_recording_log_file: Optional[Any] = None  # File handle for FFmpeg output log
_recording_last_size: int = 0  # Track file size for health monitoring


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


def get_ffmpeg_path() -> str:
    """Find ffmpeg executable."""
    # Common paths
    paths = [
        "/opt/homebrew/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        "/usr/bin/ffmpeg",
        "ffmpeg"
    ]
    for path in paths:
        try:
            subprocess.run([path, "-version"], capture_output=True, check=True)
            return path
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    raise RuntimeError("ffmpeg not found. Please install: brew install ffmpeg")


def get_screen_capture_args(screen_index: int = 1, width: int = 1920, height: int = 1080, fps: int = 30) -> list[str]:
    """Get platform-specific FULL SCREEN capture arguments for ffmpeg.
    
    Args:
        screen_index: Screen device index for macOS (1=first screen, 2=second screen).
                     Use ffmpeg -f avfoundation -list_devices true -i "" to list devices.
        width: Capture width (used for container Xvfb capture)
        height: Capture height (used for container Xvfb capture)
        fps: Frames per second
    
    In container environments:
        Uses x11grab to capture the Xvfb virtual display (typically :99).
        This captures whatever is rendered to the virtual display, including
        browser windows from Playwright MCP running in the same container.
    """
    # Container environment - always use x11grab with DISPLAY
    if is_container_environment() or sys.platform == "linux":
        display = os.environ.get("DISPLAY", ":99")
        # For Xvfb with browser windows, we capture from y=60 to skip the window title bar
        # The Xvfb display is taller (1140) to accommodate the browser chrome
        # We capture just the browser content area (1920x1080)
        title_bar_height = 60  # Firefox window title bar height
        return [
            "-f", "x11grab",
            "-video_size", f"{width}x{height}",
            "-framerate", str(fps),
            "-i", f"{display}+0,{title_bar_height}",  # Offset by title bar height
        ]
    elif sys.platform == "darwin":  # macOS
        # macOS uses AVFoundation - device indices are listed with -list_devices true
        # Typically: 0=FaceTime Camera, 1=Capture screen 0, 2=Capture screen 1
        return [
            "-f", "avfoundation",
            "-capture_cursor", "1",
            "-framerate", str(fps),
            "-pixel_format", "uyvy422",
            "-i", f"{screen_index}:none",  # Screen index:audio (none = no audio)
        ]
    elif sys.platform == "win32":
        return [
            "-f", "gdigrab",
            "-framerate", str(fps),
            "-i", "desktop",
        ]
    else:
        raise RuntimeError(f"Unsupported platform: {sys.platform}")


def get_region_capture_args(x: int, y: int, width: int, height: int, screen_index: int = 1, fps: int = 30) -> list[str]:
    """Get platform-specific REGION capture arguments for ffmpeg.
    
    Args:
        x: X coordinate of top-left corner
        y: Y coordinate of top-left corner
        width: Width of capture region
        height: Height of capture region
        screen_index: Screen device index (macOS only)
        fps: Frames per second
    """
    # Container environment - use x11grab with offset
    if is_container_environment() or sys.platform == "linux":
        display = os.environ.get("DISPLAY", ":99")
        return [
            "-f", "x11grab",
            "-video_size", f"{width}x{height}",
            "-framerate", str(fps),
            "-i", f"{display}+{x},{y}",
        ], None
    elif sys.platform == "darwin":  # macOS
        # AVFoundation doesn't support region directly, capture full and crop
        return [
            "-f", "avfoundation",
            "-capture_cursor", "1",
            "-framerate", str(fps),
            "-pixel_format", "uyvy422",
            "-i", f"{screen_index}:none",
        ], f"crop={width}:{height}:{x}:{y}"  # Returns args and crop filter
    elif sys.platform == "win32":
        return [
            "-f", "gdigrab",
            "-framerate", str(fps),
            "-offset_x", str(x),
            "-offset_y", str(y),
            "-video_size", f"{width}x{height}",
            "-i", "desktop",
        ], None
    else:
        raise RuntimeError(f"Unsupported platform: {sys.platform}")


def get_window_capture_args(window_title: str) -> tuple[list[str], Optional[str], Optional[str]]:
    """Get platform-specific WINDOW capture arguments for ffmpeg.
    
    Args:
        window_title: Window title pattern to match
        
    Returns:
        Tuple of (ffmpeg_args, crop_filter, error_message)
        If error_message is set, the other values should be ignored.
    """
    if sys.platform == "darwin":  # macOS
        # Get the CGWindowID for the window
        window_id = window_manager.get_window_id(window_title)
        if not window_id:
            return [], None, f"Window '{window_title}' not found. Use list_windows to see available windows."
        
        # Use screencapture to capture specific window, pipe to ffmpeg
        # Unfortunately, ffmpeg AVFoundation doesn't support window capture directly
        # We'll use a workaround: focus the window and capture full screen
        # Or use region-based capture with window bounds
        try:
            bounds = window_manager.get_window_bounds(window_title)
            # Use region capture with the window's bounds
            args, crop = get_region_capture_args(bounds.x, bounds.y, bounds.width, bounds.height)
            return args, crop, None
        except Exception as e:
            return [], None, f"Could not get window bounds: {e}"
    
    elif sys.platform == "linux":
        # Linux x11grab can capture by window ID
        window_id = window_manager.get_window_id(window_title)
        if not window_id:
            return [], None, f"Window '{window_title}' not found. Use list_windows to see available windows."
        
        # Get window bounds for proper sizing
        try:
            bounds = window_manager.get_window_bounds(window_title)
            display = os.environ.get("DISPLAY", ":0")
            
            # Ensure dimensions are even (FFmpeg requirement for most codecs)
            width = bounds.width if bounds.width % 2 == 0 else bounds.width + 1
            height = bounds.height if bounds.height % 2 == 0 else bounds.height + 1
            
            # Ensure we start at position 0,0 or the actual window position
            # Sometimes bounds.x/y have offset issues, so we capture from 0,0
            # if the window is near the origin (within 50px tolerance)
            x = 0 if bounds.x < 50 else bounds.x
            y = 0 if bounds.y < 50 else bounds.y
            
            return [
                "-f", "x11grab",
                "-video_size", f"{width}x{height}",
                "-i", f"{display}.0+{x},{y}",
            ], None, None
        except Exception as e:
            return [], None, f"Could not get window bounds: {e}"
    
    elif sys.platform == "win32":
        # Windows gdigrab supports capture by window title
        return [
            "-f", "gdigrab",
            "-i", f"title={window_title}",
        ], None, None
    
    else:
        return [], None, f"Unsupported platform: {sys.platform}"


# Create the MCP server
server = Server("getademo")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools.
    
    OpenAI Compatibility Notes:
    - All schemas include "additionalProperties": false (required for strict mode)
    - Tools with no parameters use empty properties object
    - Array parameters (concatenate_videos) are supported but may need special handling
    """
    return [
        Tool(
            name="start_recording",
            description="Start video recording. Auto-detects browser window in container. Perform actions AFTER calling this. Keep scenes short (10-30s).",
            inputSchema={
                "type": "object",
                "properties": {
                    "output_path": {
                        "type": "string",
                        "description": "Output video path. Default: recording_<timestamp>.mp4"
                    }
                },
                "required": [],
                "additionalProperties": False
            }
        ),
        Tool(
            name="stop_recording",
            description="Stop the current recording and save the video file.",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        ),
        Tool(
            name="recording_status",
            description="Check if a recording is in progress.",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        ),
        Tool(
            name="text_to_speech",
            description="Convert text to speech audio. Uses OpenAI TTS if API key set, else Edge TTS.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to convert to speech"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output audio path. Default: tts_<timestamp>.mp3"
                    }
                },
                "required": ["text"],
                "additionalProperties": False
            }
        ),
        Tool(
            name="media_info",
            description="Get metadata for a video or audio file: duration, resolution, codecs, file size.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to media file (video or audio)"
                    }
                },
                "required": ["file_path"],
                "additionalProperties": False
            }
        ),
        Tool(
            name="concatenate_videos",
            description="Join multiple video files into one sequential video.",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Ordered list of video paths to concatenate"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output path for final concatenated video"
                    }
                },
                "required": ["video_paths", "output_path"],
                "additionalProperties": False
            }
        ),
        Tool(
            name="adjust_video_to_audio",
            description="Sync video to audio by adjusting playback speed, then merge audio track. Preserves all visual content.",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_path": {
                        "type": "string",
                        "description": "Input video file path"
                    },
                    "audio_path": {
                        "type": "string",
                        "description": "Audio file path (determines output duration)"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output video path with synced audio"
                    }
                },
                "required": ["video_path", "audio_path", "output_path"],
                "additionalProperties": False
            }
        ),
        Tool(
            name="planning_phase_1",
            description="Phase 1: Demo planning guide. Call FIRST before any demo.",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        ),
        Tool(
            name="setup_phase_2",
            description="Phase 2: Pre-recording setup. Call after planning_phase_1.",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        ),
        Tool(
            name="recording_phase_3",
            description="Phase 3: Recording actions guide. Call after setup_phase_2.",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        ),
        Tool(
            name="editing_phase_4",
            description="Phase 4: Post-recording assembly. Call after recording_phase_3.",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        ),
        Tool(
            name="list_windows",
            description="List all windows in the virtual display. Call after browser_navigate().",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        ),
        Tool(
            name="window_tools",
            description="Check availability of window management tools (wmctrl, xdotool).",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    global _recording_process, _recording_path, _recording_start_time
    
    try:
        if name == "start_recording":
            return await _start_recording(arguments)
        
        elif name == "stop_recording":
            return await _stop_recording()
        
        elif name == "recording_status":
            return await _recording_status()
        
        elif name == "text_to_speech":
            return await _text_to_speech(arguments)
        
        
        elif name == "media_info":
            return await _get_media_info(arguments)
        
        # Backward compatibility alias
        elif name == "get_media_info":
            return await _get_media_info(arguments)
        
        elif name == "concatenate_videos":
            return await _concatenate_videos(arguments)
        
        elif name == "adjust_video_to_audio":
            return await _adjust_video_to_audio(arguments)
        
        # Backward compatibility - old name still works
        elif name == "adjust_video_to_audio_length":
            return await _adjust_video_to_audio(arguments)
        
        # Phase-based Protocol Tools (renamed for clarity)
        elif name == "planning_phase_1":
            return [TextContent(type="text", text=get_planning_guide())]
        
        elif name == "setup_phase_2":
            return [TextContent(type="text", text=get_setup_guide())]
        
        elif name == "recording_phase_3":
            return [TextContent(type="text", text=get_recording_guide())]
        
        elif name == "editing_phase_4":
            return [TextContent(type="text", text=get_assembly_guide())]
        
        # Backward compatibility aliases for old guide tool names
        elif name == "get_demo_planning_guide":
            return [TextContent(type="text", text=get_planning_guide())]
        
        elif name == "get_recording_setup_guide":
            return [TextContent(type="text", text=get_setup_guide())]
        
        elif name == "get_recording_actions_guide":
            return [TextContent(type="text", text=get_recording_guide())]
        
        elif name == "get_video_assembly_guide":
            return [TextContent(type="text", text=get_assembly_guide())]
        
        # Window Management Tools
        elif name == "list_windows":
            return await _list_windows()
        
        elif name == "window_tools":
            return await _check_window_tools()
        
        # Backward compatibility alias
        elif name == "check_window_tools":
            return await _check_window_tools()
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def _start_recording(args: dict) -> list[TextContent]:
    """Start recording with support for multiple capture modes."""
    global _recording_process, _recording_path, _recording_start_time, _recording_log_file, _recording_last_size
    
    if _recording_process is not None and _recording_process.poll() is None:
        return [TextContent(type="text", text="Recording already in progress. Stop it first.")]
    
    # Auto-generate output path if not provided
    if "output_path" in args and args["output_path"]:
        output_path = Path(args["output_path"])
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = get_default_output_path(f"recording_{timestamp}.mp4")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # WINDOW MODE ONLY - simplest and cleanest approach
    window_title = args.get("window_title")
    fps = 30  # Hardcoded - optimal for demos
    
    # Auto-detect browser window if not specified (container mode)
    if not window_title and is_container_environment():
        # Try common browser window patterns
        for pattern in ["Nightly", "Firefox", "Chromium", "Chrome"]:
            try:
                if window_manager.get_window_id(pattern):
                    window_title = pattern
                    break
            except Exception:
                continue
    
    if not window_title:
        return [TextContent(
            type="text",
            text="ERROR: Could not auto-detect browser window.\n\n"
                 "Make sure you have navigated to a URL first (browser_navigate).\n"
                 "Then either:\n"
                 "  - Just call start_recording() - it will auto-detect the browser\n"
                 "  - Or specify window_title='Firefox' explicitly"
        )]
    
    ffmpeg = get_ffmpeg_path()
    
    # WINDOW MODE ONLY - clean, simple, no black bars
    # First, try to focus the window to ensure it's visible
    try:
        window_manager.focus_window(window_title)
        await asyncio.sleep(0.3)  # Brief delay for window to come to front
    except Exception:
        pass  # Continue anyway, window might still be capturable
    
    # Get window capture arguments
    capture_args, crop_filter, error = get_window_capture_args(window_title)
    if error:
        return [TextContent(type="text", text=f"Window capture error: {error}\n\nRun list_windows() to verify the window exists.")]
    
    # Get window bounds for output size - always use actual window dimensions
    try:
        bounds = window_manager.get_window_bounds(window_title)
        width = bounds.width
        height = bounds.height
        mode_info = f"Window: {window_title}\nWindow size: {width}x{height}"
    except Exception:
        # Fallback if bounds detection fails
        width = 1920
        height = 1080
        mode_info = f"Window: {window_title} (using default 1920x1080)"
    
    # Build video filter
    video_filters = []
    if crop_filter:
        video_filters.append(crop_filter)
    # Add scale filter to ensure exact output size
    if crop_filter or not is_container_environment():
        video_filters.append(f"scale={width}:{height}")
    
    # Build command
    cmd = [ffmpeg, "-y", *capture_args]
    
    if video_filters:
        vf_string = ",".join(video_filters)
        cmd.extend(["-vf", vf_string])
    
    cmd.extend([
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        # Use fragmented MP4 for crash recovery - writes metadata throughout the file
        # instead of only at the end (moov atom issue)
        "-movflags", "frag_keyframe+empty_moov",
        str(output_path)
    ])
    
    # Create log file for FFmpeg output (prevents pipe buffer deadlock for long recordings)
    log_path = output_path.with_suffix('.ffmpeg.log')
    _recording_log_file = open(log_path, 'w')
    
    # Start the process with output going to log file instead of pipes
    # This prevents the ~1MB pipe buffer from filling and blocking FFmpeg
    _recording_process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=_recording_log_file,
        stderr=subprocess.STDOUT  # Combine stderr into same log file
    )
    _recording_path = output_path
    _recording_start_time = datetime.now()
    _recording_last_size = 0
    
    # Wait briefly and check if process started successfully
    await asyncio.sleep(0.5)
    
    if _recording_process.poll() is not None:
        # Process died - get error from log file
        _recording_log_file.close()
        try:
            with open(log_path, 'r') as f:
                error_msg = f.read() or "Unknown error"
        except Exception:
            error_msg = "Unknown error (could not read log)"
        
        _recording_process = None
        _recording_path = None
        _recording_start_time = None
        _recording_log_file = None
        
        if is_container_environment():
            troubleshooting = (
                f"**Container Troubleshooting:**\n"
                f"1. Ensure Xvfb is running (check /app/start-xvfb.sh)\n"
                f"2. Verify DISPLAY is set: DISPLAY={os.environ.get('DISPLAY', 'not set')}\n"
                f"3. Check Xvfb resolution matches recording size\n"
                f"4. Ensure Playwright browser is rendering to the same DISPLAY"
            )
        else:
            troubleshooting = (
                f"**Troubleshooting:**\n"
                f"1. Grant Screen Recording permission: System Settings -> Privacy & Security -> Screen Recording\n"
                f"2. Add the terminal app (Terminal, iTerm, or Cursor) to allowed apps\n"
                f"3. Restart Cursor after granting permission"
            )
        
        return [TextContent(
            type="text",
            text=f"Recording failed to start!\n\n"
                 f"Error: {error_msg}\n\n"
                 f"{troubleshooting}\n\n"
                 f"Command attempted: {' '.join(cmd)}"
        )]
    
    return [TextContent(
        type="text",
        text=f"Recording started!\n"
             f"{mode_info}\n"
             f"Output: {output_path}\n"
             f"Resolution: {width}x{height} @ {fps}fps\n"
             f"Started at: {_recording_start_time.strftime('%H:%M:%S')}\n\n"
             f"Use 'stop_recording' when done."
    )]


async def _stop_recording() -> list[TextContent]:
    """Stop screen recording."""
    global _recording_process, _recording_path, _recording_start_time, _recording_log_file, _recording_last_size
    
    if _recording_process is None:
        return [TextContent(type="text", text="No recording in progress.")]
    
    if _recording_process.poll() is not None:
        return [TextContent(type="text", text="Recording already stopped.")]
    
    duration = (datetime.now() - _recording_start_time).total_seconds() if _recording_start_time else 0
    output_path = _recording_path
    
    # Stop ffmpeg gracefully - multiple approaches for reliability
    stopped = False
    
    # Method 1: Send 'q' to stdin (graceful stop)
    try:
        if _recording_process.stdin:
            _recording_process.stdin.write(b'q')
            _recording_process.stdin.flush()
            # Use asyncio to wait without blocking
            for _ in range(30):  # Wait up to 3 seconds
                await asyncio.sleep(0.1)
                if _recording_process.poll() is not None:
                    stopped = True
                    break
    except (BrokenPipeError, OSError):
        pass  # stdin may be closed
    
    # Method 2: Send SIGINT (Ctrl+C equivalent)
    if not stopped:
        try:
            import signal
            _recording_process.send_signal(signal.SIGINT)
            for _ in range(20):  # Wait up to 2 seconds
                await asyncio.sleep(0.1)
                if _recording_process.poll() is not None:
                    stopped = True
                    break
        except (ProcessLookupError, OSError):
            pass
    
    # Method 3: SIGTERM
    if not stopped:
        try:
            _recording_process.terminate()
            for _ in range(20):  # Wait up to 2 seconds
                await asyncio.sleep(0.1)
                if _recording_process.poll() is not None:
                    stopped = True
                    break
        except (ProcessLookupError, OSError):
            pass
    
    # Method 4: Force kill
    if not stopped:
        try:
            _recording_process.kill()
            await asyncio.sleep(0.5)
        except (ProcessLookupError, OSError):
            pass
    
    # Close log file
    log_path = None
    if _recording_log_file is not None:
        try:
            log_path = Path(_recording_log_file.name)
            _recording_log_file.close()
        except Exception:
            pass
    
    # Reset state
    _recording_process = None
    _recording_path = None
    _recording_start_time = None
    _recording_log_file = None
    _recording_last_size = 0
    
    # Check file size
    try:
        file_size = output_path.stat().st_size / (1024 * 1024) if output_path and output_path.exists() else 0
    except Exception:
        file_size = 0
    
    # Clean up log file if recording succeeded (file > 0 bytes)
    if log_path and log_path.exists() and file_size > 0:
        try:
            log_path.unlink()
        except Exception:
            pass  # Log cleanup is optional
    
    # Generate URL if in container
    url = get_video_url(output_path) if output_path else None
    url_info = f"URL: {url}\n" if url else ""
    
    return [TextContent(
        type="text",
        text=f"Recording stopped!\n"
             f"Output: {output_path}\n"
             f"{url_info}"
             f"Duration: {duration:.1f} seconds\n"
             f"File size: {file_size:.1f} MB"
    )]


async def _recording_status() -> list[TextContent]:
    """Get recording status with health monitoring."""
    global _recording_process, _recording_path, _recording_start_time, _recording_last_size
    
    if _recording_process is None or _recording_process.poll() is not None:
        return [TextContent(type="text", text="No recording in progress.")]
    
    duration = (datetime.now() - _recording_start_time).total_seconds() if _recording_start_time else 0
    
    # Check file size and growth (health monitoring)
    current_size = 0
    size_growing = True
    try:
        if _recording_path and _recording_path.exists():
            current_size = _recording_path.stat().st_size
            # Check if file is growing (healthy recording)
            if _recording_last_size > 0 and current_size <= _recording_last_size:
                size_growing = False
            _recording_last_size = current_size
    except Exception:
        pass
    
    size_mb = current_size / (1024 * 1024)
    health_status = "✓ Healthy (file growing)" if size_growing else "⚠ Warning: File not growing!"
    
    return [TextContent(
        type="text",
        text=f"Recording in progress\n"
             f"Output: {_recording_path}\n"
             f"Duration: {duration:.1f} seconds\n"
             f"File size: {size_mb:.2f} MB\n"
             f"Health: {health_status}\n"
             f"Started: {_recording_start_time.strftime('%H:%M:%S')}"
    )]


async def _text_to_speech(args: dict) -> list[TextContent]:
    """Generate speech from text."""
    text = args["text"]
    
    # Auto-generate output path if not provided
    if "output_path" in args and args["output_path"]:
        output_path = Path(args["output_path"])
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = get_default_output_path(f"tts_{timestamp}.mp3")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Simplified: Always use "onyx" voice, auto-detect engine from API key
    voice = "onyx"  # Professional, clear voice - best for demos
    api_key = os.environ.get("OPENAI_API_KEY")
    
    # Auto-detect engine: OpenAI if API key available, otherwise Edge TTS
    if api_key:
        engine = "openai"
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            response = client.audio.speech.create(
                model="tts-1-hd",
                voice=voice,
                input=text
            )
            response.stream_to_file(str(output_path))
            
        except Exception as e:
            return [TextContent(type="text", text=f"OpenAI TTS error: {str(e)}")]
    else:
        # Fallback to Edge TTS (free, no API key needed)
        engine = "edge"
        edge_voice = "en-US-GuyNeural"  # Similar to onyx - professional male voice
        try:
            import edge_tts
            
            communicate = edge_tts.Communicate(text, edge_voice)
            await communicate.save(str(output_path))
            voice = edge_voice  # Update for output message
            
        except ImportError:
            return [TextContent(type="text", text="No OPENAI_API_KEY set and edge-tts not installed.\n\nOptions:\n1. Set OPENAI_API_KEY environment variable (recommended)\n2. Install edge-tts: pip install edge-tts")]
        except Exception as e:
            return [TextContent(type="text", text=f"Edge TTS error: {str(e)}")]
    
    # Get file info
    file_size = output_path.stat().st_size / 1024 if output_path.exists() else 0
    duration = await _get_audio_duration(output_path)
    
    url = get_video_url(output_path)  # Also works for audio files
    url_info = f"URL: {url}\n" if url else ""
    
    return [TextContent(
        type="text",
        text=f"Audio generated!\n"
             f"Output: {output_path}\n"
             f"{url_info}"
             f"Engine: {engine} ({voice})\n"
             f"Duration: {duration:.1f} seconds\n"
             f"Size: {file_size:.1f} KB\n"
             f"Text length: {len(text)} characters"
    )]


async def _get_audio_duration(path: Path) -> float:
    """Get audio file duration."""
    try:
        ffmpeg = get_ffmpeg_path()
        ffprobe = ffmpeg.replace("ffmpeg", "ffprobe")
        
        result = subprocess.run(
            [ffprobe, "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True
        )
        return float(result.stdout.strip())
    except:
        return 0.0


async def _get_media_info(args: dict) -> list[TextContent]:
    """Get media file information."""
    file_path = Path(args["file_path"])
    
    if not file_path.exists():
        return [TextContent(type="text", text=f"File not found: {file_path}")]
    
    ffmpeg = get_ffmpeg_path()
    ffprobe = ffmpeg.replace("ffmpeg", "ffprobe")
    
    cmd = [
        ffprobe, "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        str(file_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        return [TextContent(type="text", text=f"Error: {result.stderr}")]
    
    info = json.loads(result.stdout)
    fmt = info.get("format", {})
    streams = info.get("streams", [])
    
    duration = float(fmt.get("duration", 0))
    size_mb = int(fmt.get("size", 0)) / (1024 * 1024)
    
    # Find video and audio streams
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    
    output = f"Media Info: {file_path.name}\n"
    output += f"Duration: {duration:.1f}s ({duration/60:.1f}m)\n"
    output += f"Size: {size_mb:.1f} MB\n"
    
    if video_stream:
        width = video_stream.get("width", "?")
        height = video_stream.get("height", "?")
        fps = video_stream.get("r_frame_rate", "?")
        codec = video_stream.get("codec_name", "?")
        output += f"Video: {width}x{height} @ {fps} ({codec})\n"
    
    if audio_stream:
        sample_rate = audio_stream.get("sample_rate", "?")
        channels = audio_stream.get("channels", "?")
        codec = audio_stream.get("codec_name", "?")
        output += f"Audio: {sample_rate}Hz, {channels}ch ({codec})\n"
    
    return [TextContent(type="text", text=output)]


async def _concatenate_videos(args: dict) -> list[TextContent]:
    """Concatenate multiple videos."""
    video_paths = [Path(p) for p in args["video_paths"]]
    output_path = Path(args["output_path"])
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = get_ffmpeg_path()
    
    # Create concat file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        for path in video_paths:
            f.write(f"file '{path.absolute()}'\n")
        concat_file = f.name
    
    try:
        cmd = [
            ffmpeg, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return [TextContent(type="text", text=f"Error: {result.stderr}")]
    
    finally:
        os.unlink(concat_file)
    
    url = get_video_url(output_path)
    url_info = f"URL: {url}\n" if url else ""
    
    return [TextContent(
        type="text",
        text=f"Videos concatenated!\n"
             f"Output: {output_path}\n"
             f"{url_info}"
             f"Videos merged: {len(video_paths)}"
    )]


async def _adjust_video_to_audio(args: dict) -> list[TextContent]:
    """
    Adjust video speed to match audio duration, then merge the audio.
    
    Does NOT cut/trim - speeds up or slows down the video so ALL visual 
    content is preserved while matching audio length.
    
    - Video longer than audio -> Speed UP (faster playback)
    - Video shorter than audio -> Slow DOWN (slower playback)
    - ALWAYS merges the audio into the output video
    """
    video_path = Path(args["video_path"])
    audio_path = Path(args["audio_path"])
    output_path = Path(args["output_path"])
    
    if not video_path.exists():
        return [TextContent(type="text", text=f"Video not found: {video_path}")]
    if not audio_path.exists():
        return [TextContent(type="text", text=f"Audio not found: {audio_path}")]
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = get_ffmpeg_path()
    ffprobe = ffmpeg.replace("ffmpeg", "ffprobe")
    
    # Get audio duration
    audio_duration = await _get_audio_duration(audio_path)
    if audio_duration <= 0:
        return [TextContent(type="text", text="Could not determine audio duration")]
    
    # Get video duration
    result = subprocess.run(
        [ffprobe, "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
        capture_output=True, text=True
    )
    video_duration = float(result.stdout.strip()) if result.stdout.strip() else 0
    
    if video_duration <= 0:
        return [TextContent(type="text", text="Could not determine video duration")]
    
    # Calculate speed factor
    # speed_factor > 1 = speed up (video longer than audio)
    # speed_factor < 1 = slow down (video shorter than audio)
    speed_factor = video_duration / audio_duration
    
    # Determine action description
    if abs(speed_factor - 1.0) < 0.01:
        action = "no change needed"
        speed_change = "1.0x (unchanged)"
    elif speed_factor > 1:
        action = "speed up"
        speed_change = f"{speed_factor:.2f}x faster"
    else:
        action = "slow down"
        speed_change = f"{1/speed_factor:.2f}x slower"
    
    # Build FFmpeg command using setpts filter to adjust video speed
    # setpts=PTS/speed_factor adjusts the presentation timestamps
    # For speed_factor=2, video plays 2x faster (PTS/2 = half the timestamps)
    # For speed_factor=0.5, video plays 2x slower (PTS/0.5 = double the timestamps)
    
    # Always merge audio (the whole point of this tool)
    cmd = [
        ffmpeg, "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-filter_complex",
        f"[0:v]setpts=PTS/{speed_factor}[v]",
        "-map", "[v]",
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-shortest",
        str(output_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        return [TextContent(type="text", text=f"Error: {result.stderr}")]
    
    # Get final duration
    final_duration = await _get_audio_duration(output_path)
    file_size = output_path.stat().st_size / (1024 * 1024) if output_path.exists() else 0
    
    url = get_video_url(output_path)
    url_info = f"URL: {url}\n" if url else ""
    
    return [TextContent(
        type="text",
        text=f"Video synced to audio!\n"
             f"Action: {action}\n"
             f"Speed: {speed_change}\n"
             f"Video: {video_duration:.2f}s -> {final_duration:.2f}s\n"
             f"Audio: {audio_duration:.2f}s (merged)\n"
             f"Output: {output_path}\n"
             f"{url_info}"
             f"Size: {file_size:.1f} MB\n"
             f"ALL visual content preserved (no frames cut)"
    )]


# =============================================================================
# Window Management Tool Implementations
# =============================================================================

async def _list_windows() -> list[TextContent]:
    """List all visible windows."""
    try:
        windows = window_manager.list_windows()
        
        if not windows:
            return [TextContent(type="text", text="No visible windows found.")]
        
        output = f"Found {len(windows)} visible windows:\n\n"
        for i, win in enumerate(windows, 1):
            output += f"{i}. {win.title}\n"
            if win.app_name:
                output += f"   App: {win.app_name}\n"
            output += f"   ID: {win.window_id}\n"
            if win.pid:
                output += f"   PID: {win.pid}\n"
            if win.bounds:
                output += f"   Bounds: x={win.bounds.x}, y={win.bounds.y}, "
                output += f"w={win.bounds.width}, h={win.bounds.height}\n"
            output += "\n"
        
        return [TextContent(type="text", text=output)]
    
    except window_manager.DependencyMissingError as e:
        return [TextContent(type="text", text=f"Missing dependencies: {str(e)}")]
    except window_manager.WindowManagerError as e:
        return [TextContent(type="text", text=f"Error listing windows: {str(e)}")]


async def _check_window_tools() -> list[TextContent]:
    """Check window management tool availability."""
    deps = window_manager.check_dependencies()
    
    output = f"Window Management Tools Status\n"
    output += f"{'=' * 40}\n\n"
    output += f"Platform: {deps['platform']}\n"
    output += f"Available: {'Yes' if deps['available'] else 'No'}\n"
    output += f"Message: {deps['message']}\n"
    
    if deps['missing']:
        output += f"\nMissing tools: {', '.join(deps['missing'])}\n"
        
        if deps['platform'] == 'linux':
            output += f"\nTo install:\n"
            output += f"  Ubuntu/Debian: sudo apt install wmctrl xdotool\n"
            output += f"  Fedora/RHEL:   sudo dnf install wmctrl xdotool\n"
            output += f"  Arch:          sudo pacman -S wmctrl xdotool\n"
    
    return [TextContent(type="text", text=output)]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def run():
    """Entry point."""
    asyncio.run(main())


if __name__ == "__main__":
    run()


