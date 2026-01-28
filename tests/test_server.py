"""Tests for getademo MCP server."""

import pytest
from pathlib import Path


class TestProtocol:
    """Tests for the demo protocol."""

    def test_get_protocol_returns_string(self):
        """Test that get_protocol returns the protocol document."""
        from getademo.protocol import get_protocol
        
        protocol = get_protocol()
        
        assert isinstance(protocol, str)
        assert len(protocol) > 0
        assert "Demo Recording Protocol" in protocol

    def test_protocol_contains_mandatory_rules(self):
        """Test that protocol contains the mandatory rules section."""
        from getademo.protocol import get_protocol
        
        protocol = get_protocol()
        
        assert "MANDATORY RULES" in protocol
        assert "RULE 1" in protocol
        assert "RULE 2" in protocol

    def test_protocol_contains_tool_reference(self):
        """Test that protocol contains tool reference."""
        from getademo.protocol import get_protocol
        
        protocol = get_protocol()
        
        assert "start_recording" in protocol
        assert "stop_recording" in protocol
        assert "text_to_speech" in protocol


class TestServerSetup:
    """Tests for server initialization."""

    def test_server_module_imports(self):
        """Test that the server module can be imported."""
        from getademo import server
        
        assert hasattr(server, 'server')
        assert hasattr(server, 'run')

    def test_server_has_tools(self):
        """Test that tools are defined."""
        from getademo import server
        
        # The server object should exist
        assert server.server is not None


class TestToolDefinitions:
    """Tests for tool definitions."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_expected_tools(self):
        """Test that list_tools returns expected tools."""
        from getademo.server import list_tools
        
        tools = await list_tools()
        tool_names = [t.name for t in tools]
        
        expected_tools = [
            "start_recording",
            "stop_recording",
            "recording_status",
            "text_to_speech",
            "replace_video_audio",
            "merge_audio_tracks",
            "trim_video",
            "get_media_info",
            "concatenate_videos",
            "get_audio_duration",
            "adjust_video_to_audio_length",
            "get_demo_protocol",
        ]
        
        for expected in expected_tools:
            assert expected in tool_names, f"Missing tool: {expected}"

    @pytest.mark.asyncio
    async def test_tools_have_descriptions(self):
        """Test that all tools have descriptions."""
        from getademo.server import list_tools
        
        tools = await list_tools()
        
        for tool in tools:
            assert tool.description, f"Tool {tool.name} missing description"
            assert len(tool.description) > 10, f"Tool {tool.name} has too short description"

    @pytest.mark.asyncio
    async def test_tools_have_input_schemas(self):
        """Test that all tools have input schemas."""
        from getademo.server import list_tools
        
        tools = await list_tools()
        
        for tool in tools:
            assert tool.inputSchema, f"Tool {tool.name} missing input schema"
            assert "type" in tool.inputSchema


class TestFfmpegPath:
    """Tests for ffmpeg path detection."""

    def test_get_ffmpeg_path_common_paths(self):
        """Test that common ffmpeg paths are checked."""
        from getademo.server import get_ffmpeg_path
        
        # This may raise RuntimeError if ffmpeg is not installed
        # but it should not raise other exceptions
        try:
            path = get_ffmpeg_path()
            assert path is not None
            assert "ffmpeg" in path
        except RuntimeError as e:
            assert "ffmpeg not found" in str(e)


class TestScreenCaptureArgs:
    """Tests for screen capture arguments."""

    def test_get_screen_capture_args_macos(self):
        """Test macOS screen capture arguments."""
        import sys
        from getademo.server import get_screen_capture_args
        
        if sys.platform == "darwin":
            args = get_screen_capture_args(screen_index=1)
            assert "-f" in args
            assert "avfoundation" in args
            assert "-capture_cursor" in args

    def test_screen_index_in_args(self):
        """Test that screen index is used in arguments."""
        import sys
        from getademo.server import get_screen_capture_args
        
        if sys.platform == "darwin":
            args1 = get_screen_capture_args(screen_index=1)
            args2 = get_screen_capture_args(screen_index=2)
            
            # The screen index should be different in the args
            assert "1:none" in str(args1)
            assert "2:none" in str(args2)


