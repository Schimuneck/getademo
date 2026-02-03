"""
Text-to-speech tools - generate voiceover audio.
"""

import os
from datetime import datetime
from pathlib import Path


def register_tts_tools(mcp, backend):
    """Register TTS tools with the MCP server."""
    
    @mcp.tool(description="Convert text to speech audio. Uses OpenAI TTS if API key set, else Edge TTS.")
    async def text_to_speech(text: str, filename: str = None) -> str:
        """Generate speech from text.
        
        Args:
            text: The text to convert to speech.
            filename: Output filename (e.g., "narration.mp3"). Auto-generated if not provided.
        """
        from ..utils.ffmpeg import get_audio_duration
        
        # Auto-generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tts_{timestamp}.mp3"
        
        # Ensure .mp3 extension
        if not filename.endswith('.mp3'):
            filename += '.mp3'
        
        out_path = backend.get_recordings_dir() / filename
        
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
                voice = edge_voice
                
            except ImportError:
                return (
                    "No OPENAI_API_KEY set and edge-tts not installed.\n\n"
                    "Options:\n"
                    "1. Set OPENAI_API_KEY environment variable (recommended)\n"
                    "2. Install edge-tts: pip install edge-tts"
                )
            except Exception as e:
                return f"Edge TTS error: {str(e)}"
        
        # Get file info
        file_size = out_path.stat().st_size / 1024 if out_path.exists() else 0
        duration = await get_audio_duration(out_path)
        
        url = backend.get_media_url(out_path)
        url_info = f"URL: {url}\n" if url else ""
        
        return (
            f"Audio generated!\n"
            f"Output: {filename}\n"
            f"{url_info}"
            f"Engine: {engine} ({voice})\n"
            f"Duration: {duration:.1f} seconds\n"
            f"Size: {file_size:.1f} KB\n"
            f"Text length: {len(text)} characters"
        )
