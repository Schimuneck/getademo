#!/usr/bin/env python3
"""
demo-recorder - FastMCP Server for Demo Recording

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

from fastmcp import FastMCP

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

# Create the FastMCP server
mcp = FastMCP("demo-recorder")


def get_video_url(file_path: Path) -> Optional[str]:
    """Generate a URL to access a video file via the HTTP server.
    
    Only works when running in a container with the video server.
    Returns None if the file is not in the recordings directory.
    Uses HTTPS for public domains, HTTP for localhost.
    """
    if not is_container_environment():
        return None
    
    try:
        # Check if file is under recordings dir
        rel_path = file_path.resolve().relative_to(CONTAINER_RECORDINGS_DIR.resolve())
        
        # Use HTTPS for public domains, HTTP for localhost
        if VIDEO_SERVER_HOST in ("localhost", "127.0.0.1"):
            return f"http://{VIDEO_SERVER_HOST}:{VIDEO_SERVER_PORT}/videos/{rel_path}"
        else:
            # Public domain - use HTTPS without port (reverse proxy handles SSL)
            return f"https://{VIDEO_SERVER_HOST}/videos/{rel_path}"
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


# =============================================================================
# Recording Tools
# =============================================================================

@mcp.tool(description="Start video recording. Auto-detects browser window in container. Perform actions AFTER calling this. Keep scenes short (10-30s).")
async def start_recording(output_path: str = None) -> str:
    """Start video recording."""
    global _recording_process, _recording_path, _recording_start_time, _recording_log_file, _recording_last_size
    
    if _recording_process is not None and _recording_process.poll() is None:
        return "Recording already in progress. Stop it first."
    
    # Auto-generate output path if not provided
    if output_path:
        out_path = Path(output_path)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = get_default_output_path(f"recording_{timestamp}.mp4")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    # WINDOW MODE ONLY - simplest and cleanest approach
    window_title = None
    fps = 30  # Hardcoded - optimal for demos
    
    # Auto-detect browser window (container mode)
    if is_container_environment():
        # Try common browser window patterns
        for pattern in ["Nightly", "Firefox", "Chromium", "Chrome"]:
            try:
                if window_manager.get_window_id(pattern):
                    window_title = pattern
                    break
            except Exception:
                continue
    
    if not window_title:
        return (
            "ERROR: Could not auto-detect browser window.\n\n"
            "Make sure you have navigated to a URL first (browser_navigate).\n"
            "Then either:\n"
            "  - Just call start_recording() - it will auto-detect the browser\n"
            "  - Or specify window_title='Firefox' explicitly"
        )
    
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
        return f"Window capture error: {error}\n\nRun list_windows() to verify the window exists."
    
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
        str(out_path)
    ])
    
    # Create log file for FFmpeg output (prevents pipe buffer deadlock for long recordings)
    log_path = out_path.with_suffix('.ffmpeg.log')
    _recording_log_file = open(log_path, 'w')
    
    # Start the process with output going to log file instead of pipes
    # This prevents the ~1MB pipe buffer from filling and blocking FFmpeg
    _recording_process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=_recording_log_file,
        stderr=subprocess.STDOUT  # Combine stderr into same log file
    )
    _recording_path = out_path
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
        
        return (
            f"Recording failed to start!\n\n"
            f"Error: {error_msg}\n\n"
            f"{troubleshooting}\n\n"
            f"Command attempted: {' '.join(cmd)}"
        )
    
    return (
        f"Recording started!\n"
        f"{mode_info}\n"
        f"Output: {out_path}\n"
        f"Resolution: {width}x{height} @ {fps}fps\n"
        f"Started at: {_recording_start_time.strftime('%H:%M:%S')}\n\n"
        f"Use 'stop_recording' when done."
    )


@mcp.tool(description="Stop the current recording and save the video file.")
async def stop_recording() -> str:
    """Stop screen recording."""
    global _recording_process, _recording_path, _recording_start_time, _recording_log_file, _recording_last_size
    
    if _recording_process is None:
        return "No recording in progress."
    
    if _recording_process.poll() is not None:
        return "Recording already stopped."
    
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
    
    return (
        f"Recording stopped!\n"
        f"Output: {output_path}\n"
        f"{url_info}"
        f"Duration: {duration:.1f} seconds\n"
        f"File size: {file_size:.1f} MB"
    )


@mcp.tool(description="Check if a recording is in progress.")
async def recording_status() -> str:
    """Get recording status with health monitoring."""
    global _recording_process, _recording_path, _recording_start_time, _recording_last_size
    
    if _recording_process is None or _recording_process.poll() is not None:
        return "No recording in progress."
    
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
    
    return (
        f"Recording in progress\n"
        f"Output: {_recording_path}\n"
        f"Duration: {duration:.1f} seconds\n"
        f"File size: {size_mb:.2f} MB\n"
        f"Health: {health_status}\n"
        f"Started: {_recording_start_time.strftime('%H:%M:%S')}"
    )


# =============================================================================
# Text-to-Speech Tool
# =============================================================================

@mcp.tool(description="Convert text to speech audio. Uses OpenAI TTS if API key set, else Edge TTS.")
async def text_to_speech(text: str, output_path: str = None) -> str:
    """Generate speech from text."""
    # Auto-generate output path if not provided
    if output_path:
        out_path = Path(output_path)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = get_default_output_path(f"tts_{timestamp}.mp3")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
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
            response.stream_to_file(str(out_path))
            
        except Exception as e:
            return f"OpenAI TTS error: {str(e)}"
    else:
        # Fallback to Edge TTS (free, no API key needed)
        engine = "edge"
        edge_voice = "en-US-GuyNeural"  # Similar to onyx - professional male voice
        try:
            import edge_tts
            
            communicate = edge_tts.Communicate(text, edge_voice)
            await communicate.save(str(out_path))
            voice = edge_voice  # Update for output message
            
        except ImportError:
            return "No OPENAI_API_KEY set and edge-tts not installed.\n\nOptions:\n1. Set OPENAI_API_KEY environment variable (recommended)\n2. Install edge-tts: pip install edge-tts"
        except Exception as e:
            return f"Edge TTS error: {str(e)}"
    
    # Get file info
    file_size = out_path.stat().st_size / 1024 if out_path.exists() else 0
    duration = await _get_audio_duration(out_path)
    
    url = get_video_url(out_path)  # Also works for audio files
    url_info = f"URL: {url}\n" if url else ""
    
    return (
        f"Audio generated!\n"
        f"Output: {out_path}\n"
        f"{url_info}"
        f"Engine: {engine} ({voice})\n"
        f"Duration: {duration:.1f} seconds\n"
        f"Size: {file_size:.1f} KB\n"
        f"Text length: {len(text)} characters"
    )


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


# =============================================================================
# Media Tools
# =============================================================================

@mcp.tool(description="Get metadata for a video or audio file: duration, resolution, codecs, file size.")
async def media_info(file_path: str) -> str:
    """Get media file information."""
    path = Path(file_path)
    
    if not path.exists():
        return f"File not found: {path}"
    
    ffmpeg = get_ffmpeg_path()
    ffprobe = ffmpeg.replace("ffmpeg", "ffprobe")
    
    cmd = [
        ffprobe, "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        str(path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        return f"Error: {result.stderr}"
    
    info = json.loads(result.stdout)
    fmt = info.get("format", {})
    streams = info.get("streams", [])
    
    duration = float(fmt.get("duration", 0))
    size_mb = int(fmt.get("size", 0)) / (1024 * 1024)
    
    # Find video and audio streams
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    
    output = f"Media Info: {path.name}\n"
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
    
    return output


@mcp.tool(description="Join multiple video files into one sequential video.")
async def concatenate_videos(video_paths: list[str], output_path: str) -> str:
    """Concatenate multiple videos."""
    paths = [Path(p) for p in video_paths]
    out_path = Path(output_path)
    
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = get_ffmpeg_path()
    
    # Create concat file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        for path in paths:
            f.write(f"file '{path.absolute()}'\n")
        concat_file = f.name
    
    try:
        cmd = [
            ffmpeg, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            str(out_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return f"Error: {result.stderr}"
    
    finally:
        os.unlink(concat_file)
    
    url = get_video_url(out_path)
    url_info = f"URL: {url}\n" if url else ""
    
    return (
        f"Videos concatenated!\n"
        f"Output: {out_path}\n"
        f"{url_info}"
        f"Videos merged: {len(paths)}"
    )


@mcp.tool(description="Sync video to audio by adjusting playback speed, then merge audio track. Preserves all visual content.")
async def adjust_video_to_audio(video_path: str, audio_path: str, output_path: str) -> str:
    """
    Adjust video speed to match audio duration, then merge the audio.
    
    Does NOT cut/trim - speeds up or slows down the video so ALL visual 
    content is preserved while matching audio length.
    
    - Video longer than audio -> Speed UP (faster playback)
    - Video shorter than audio -> Slow DOWN (slower playback)
    - ALWAYS merges the audio into the output video
    """
    vid_path = Path(video_path)
    aud_path = Path(audio_path)
    out_path = Path(output_path)
    
    if not vid_path.exists():
        return f"Video not found: {vid_path}"
    if not aud_path.exists():
        return f"Audio not found: {aud_path}"
    
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = get_ffmpeg_path()
    ffprobe = ffmpeg.replace("ffmpeg", "ffprobe")
    
    # Get audio duration
    audio_duration = await _get_audio_duration(aud_path)
    if audio_duration <= 0:
        return "Could not determine audio duration"
    
    # Get video duration
    result = subprocess.run(
        [ffprobe, "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(vid_path)],
        capture_output=True, text=True
    )
    video_duration = float(result.stdout.strip()) if result.stdout.strip() else 0
    
    if video_duration <= 0:
        return "Could not determine video duration"
    
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
        "-i", str(vid_path),
        "-i", str(aud_path),
        "-filter_complex",
        f"[0:v]setpts=PTS/{speed_factor}[v]",
        "-map", "[v]",
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-shortest",
        str(out_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        return f"Error: {result.stderr}"
    
    # Get final duration
    final_duration = await _get_audio_duration(out_path)
    file_size = out_path.stat().st_size / (1024 * 1024) if out_path.exists() else 0
    
    url = get_video_url(out_path)
    url_info = f"URL: {url}\n" if url else ""
    
    return (
        f"Video synced to audio!\n"
        f"Action: {action}\n"
        f"Speed: {speed_change}\n"
        f"Video: {video_duration:.2f}s -> {final_duration:.2f}s\n"
        f"Audio: {audio_duration:.2f}s (merged)\n"
        f"Output: {out_path}\n"
        f"{url_info}"
        f"Size: {file_size:.1f} MB\n"
        f"ALL visual content preserved (no frames cut)"
    )


# =============================================================================
# Protocol/Guide Tools
# =============================================================================

@mcp.tool(description="Phase 1: Demo planning guide. Call FIRST before any demo.")
async def planning_phase_1() -> str:
    """Get phase 1 planning guide."""
    return get_planning_guide()


@mcp.tool(description="Phase 2: Pre-recording setup. Call after planning_phase_1.")
async def setup_phase_2() -> str:
    """Get phase 2 setup guide."""
    return get_setup_guide()


@mcp.tool(description="Phase 3: Recording actions guide. Call after setup_phase_2.")
async def recording_phase_3() -> str:
    """Get phase 3 recording guide."""
    return get_recording_guide()


@mcp.tool(description="Phase 4: Post-recording assembly. Call after recording_phase_3.")
async def editing_phase_4() -> str:
    """Get phase 4 editing guide."""
    return get_assembly_guide()


# =============================================================================
# Window Management Tools
# =============================================================================

@mcp.tool(description="List all windows in the virtual display. Call after browser_navigate().")
async def list_windows() -> str:
    """List all visible windows."""
    try:
        windows = window_manager.list_windows()
        
        if not windows:
            return "No visible windows found."
        
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
        
        return output
    
    except window_manager.DependencyMissingError as e:
        return f"Missing dependencies: {str(e)}"
    except window_manager.WindowManagerError as e:
        return f"Error listing windows: {str(e)}"


@mcp.tool(description="Check availability of window management tools (wmctrl, xdotool).")
async def window_tools() -> str:
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
    
    return output


# =============================================================================
# Entry Points
# =============================================================================

def run():
    """Entry point for STDIO transport (default)."""
    mcp.run()


def main():
    """Entry point for HTTP transport."""
    mcp.run(transport="sse")


if __name__ == "__main__":
    run()
