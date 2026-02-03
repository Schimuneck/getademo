"""
Tools module - MCP tool definitions organized by category.

All tools are registered with the FastMCP server in server.py.
"""

from .recording import register_recording_tools
from .tts import register_tts_tools
from .video import register_video_tools
from .guides import register_guide_tools
from .windows import register_window_tools


def register_all_tools(mcp, backend):
    """Register all tools with the MCP server.
    
    Args:
        mcp: FastMCP server instance.
        backend: RecordingBackend instance.
    """
    register_recording_tools(mcp, backend)
    register_tts_tools(mcp, backend)
    register_video_tools(mcp, backend)
    register_guide_tools(mcp)
    register_window_tools(mcp)


__all__ = [
    "register_all_tools",
    "register_recording_tools",
    "register_tts_tools",
    "register_video_tools",
    "register_guide_tools",
    "register_window_tools",
]
