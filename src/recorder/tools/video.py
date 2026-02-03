"""
Video editing tools - adjust speed, concatenate, get media info.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path


def register_video_tools(mcp, backend):
    """Register video editing tools with the MCP server."""
    
    @mcp.tool(description="Get metadata for a video or audio file: duration, resolution, codecs, file size, and URL.")
    async def media_info(filename: str) -> str:
        """Get media file information including download URL.
        
        Args:
            filename: The filename to get info for (e.g., "scene1.mp4").
        """
        from ..utils.ffmpeg import get_media_info, get_ffprobe_path
        
        path = backend.get_recordings_dir() / filename
        
        if not path.exists():
            return f"File not found: {filename}"
        
        info = get_media_info(path)
        if not info:
            return f"Error reading media info for {filename}"
        
        url = backend.get_media_url(path)
        
        output = f"Media Info: {filename}\n"
        if url:
            output += f"URL: {url}\n"
        output += f"Duration: {info['duration']:.1f}s ({info['duration']/60:.1f}m)\n"
        output += f"Size: {info['size_mb']:.1f} MB\n"
        
        if "video" in info:
            v = info["video"]
            output += f"Video: {v['width']}x{v['height']} @ {v['fps']} ({v['codec']})\n"
        
        if "audio" in info:
            a = info["audio"]
            output += f"Audio: {a['sample_rate']}Hz, {a['channels']}ch ({a['codec']})\n"
        
        return output
    
    @mcp.tool(description="List all media files (videos and audio) in the recordings directory with URLs.")
    async def list_media_files() -> str:
        """List all available media files with their URLs, sizes, and durations."""
        from ..utils.ffmpeg import get_ffprobe_path
        
        recordings_dir = backend.get_recordings_dir()
        
        # Get all media files
        media_extensions = {'.mp4', '.mp3', '.wav', '.webm', '.mkv', '.avi', '.m4a'}
        files = []
        
        for file_path in recordings_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in media_extensions:
                files.append(file_path)
        
        if not files:
            return "No media files found in recordings directory."
        
        # Sort by modification time (newest first)
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        ffprobe = get_ffprobe_path()
        
        output = f"Media Files ({len(files)} files):\n\n"
        
        for i, file_path in enumerate(files, 1):
            filename = file_path.name
            size_mb = file_path.stat().st_size / (1024 * 1024)
            
            # Determine type based on extension
            ext = file_path.suffix.lower()
            file_type = "video" if ext in {'.mp4', '.webm', '.mkv', '.avi'} else "audio"
            
            # Get duration
            try:
                result = subprocess.run(
                    [ffprobe, "-v", "quiet", "-show_entries", "format=duration",
                     "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)],
                    capture_output=True, text=True
                )
                duration = float(result.stdout.strip()) if result.stdout.strip() else 0
            except Exception:
                duration = 0
            
            url = backend.get_media_url(file_path)
            
            output += f"{i}. {filename}\n"
            if url:
                output += f"   URL: {url}\n"
            output += f"   Size: {size_mb:.1f} MB | Duration: {duration:.1f}s | Type: {file_type}\n\n"
        
        return output
    
    @mcp.tool(description="Join multiple video files into one sequential video.")
    async def concatenate_videos(filenames: list[str], output_filename: str) -> str:
        """Concatenate multiple videos.
        
        Args:
            filenames: List of video filenames to concatenate (e.g., ["scene1.mp4", "scene2.mp4"]).
            output_filename: Output filename for the merged video (e.g., "final.mp4").
        """
        from ..utils.ffmpeg import get_ffmpeg_path
        
        recordings_dir = backend.get_recordings_dir()
        paths = [recordings_dir / f for f in filenames]
        out_path = recordings_dir / output_filename
        
        # Check all input files exist
        for i, path in enumerate(paths):
            if not path.exists():
                return f"File not found: {filenames[i]}"
        
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
        
        url = backend.get_media_url(out_path)
        url_info = f"URL: {url}\n" if url else ""
        
        return (
            f"Videos concatenated!\n"
            f"Output: {output_filename}\n"
            f"{url_info}"
            f"Videos merged: {len(paths)}"
        )
    
    @mcp.tool(description="Sync video to audio by adjusting playback speed, then merge audio track. Preserves all visual content.")
    async def adjust_video_to_audio(video_filename: str, audio_filename: str, output_filename: str) -> str:
        """Adjust video speed to match audio duration, then merge the audio.
        
        Args:
            video_filename: Input video filename (e.g., "scene1_raw.mp4").
            audio_filename: Input audio filename (e.g., "scene1_audio.mp3").
            output_filename: Output filename for synced video (e.g., "scene1_final.mp4").
        """
        from ..utils.ffmpeg import get_ffmpeg_path, get_audio_duration
        
        recordings_dir = backend.get_recordings_dir()
        vid_path = recordings_dir / video_filename
        aud_path = recordings_dir / audio_filename
        out_path = recordings_dir / output_filename
        
        if not vid_path.exists():
            return f"Video not found: {video_filename}"
        if not aud_path.exists():
            return f"Audio not found: {audio_filename}"
        
        ffmpeg = get_ffmpeg_path()
        ffprobe = ffmpeg.replace("ffmpeg", "ffprobe")
        
        # Get audio duration
        audio_duration = await get_audio_duration(aud_path)
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
        
        # Build FFmpeg command
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
        final_duration = await get_audio_duration(out_path)
        file_size = out_path.stat().st_size / (1024 * 1024) if out_path.exists() else 0
        
        url = backend.get_media_url(out_path)
        url_info = f"URL: {url}\n" if url else ""
        
        return (
            f"Video synced to audio!\n"
            f"Action: {action}\n"
            f"Speed: {speed_change}\n"
            f"Video: {video_duration:.2f}s -> {final_duration:.2f}s\n"
            f"Audio: {audio_duration:.2f}s (merged)\n"
            f"Output: {output_filename}\n"
            f"{url_info}"
            f"Size: {file_size:.1f} MB\n"
            f"ALL visual content preserved (no frames cut)"
        )
