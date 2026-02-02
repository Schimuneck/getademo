"""Tests for demo-recorder MCP server."""

import pytest
from pathlib import Path


class TestProtocol:
    """Tests for the demo protocol guides."""

    def test_get_planning_guide_returns_string(self):
        """Test that get_planning_guide returns the planning document."""
        from recorder.protocol import get_planning_guide
        
        guide = get_planning_guide()
        
        assert isinstance(guide, str)
        assert len(guide) > 0
        assert "PLANNING" in guide or "Demo Planning" in guide

    def test_get_setup_guide_returns_string(self):
        """Test that get_setup_guide returns the setup document."""
        from recorder.protocol import get_setup_guide
        
        guide = get_setup_guide()
        
        assert isinstance(guide, str)
        assert len(guide) > 0
        assert "browser" in guide.lower() or "setup" in guide.lower()

    def test_get_recording_guide_returns_string(self):
        """Test that get_recording_guide returns the recording document."""
        from recorder.protocol import get_recording_guide
        
        guide = get_recording_guide()
        
        assert isinstance(guide, str)
        assert len(guide) > 0
        assert "recording" in guide.lower()

    def test_get_assembly_guide_returns_string(self):
        """Test that get_assembly_guide returns the assembly document."""
        from recorder.protocol import get_assembly_guide
        
        guide = get_assembly_guide()
        
        assert isinstance(guide, str)
        assert len(guide) > 0

    def test_guides_contain_tool_references(self):
        """Test that guides reference the core tools."""
        from recorder.protocol import get_planning_guide, get_recording_guide, get_assembly_guide
        
        all_guides = get_planning_guide() + get_recording_guide() + get_assembly_guide()
        
        assert "start_recording" in all_guides
        assert "stop_recording" in all_guides
        assert "text_to_speech" in all_guides

    def test_guides_emphasize_actions_during_recording(self):
        """Test that guides emphasize performing actions during recording."""
        from recorder.protocol import get_recording_guide
        
        guide = get_recording_guide()
        
        # Should warn against actions outside recording
        assert "WRONG" in guide or "CORRECT" in guide or "DURING" in guide


class TestServerSetup:
    """Tests for server initialization."""

    def test_server_module_imports(self):
        """Test that the server module can be imported."""
        from recorder import server
        
        assert hasattr(server, 'server')
        assert hasattr(server, 'run')

    def test_server_has_tools(self):
        """Test that tools are defined."""
        from recorder import server
        
        # The server object should exist
        assert server.server is not None


class TestToolDefinitions:
    """Tests for tool definitions."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_expected_tools(self):
        """Test that list_tools returns expected tools."""
        from recorder.server import list_tools
        
        tools = await list_tools()
        tool_names = [t.name for t in tools]
        
        # Core recording tools
        expected_tools = [
            "start_recording",
            "stop_recording",
            "recording_status",
            "text_to_speech",
            "media_info",
            "concatenate_videos",
            "adjust_video_to_audio",
            # Protocol guides
            "planning_phase_1",
            "setup_phase_2",
            "recording_phase_3",
            "editing_phase_4",
            # Utility tools
            "list_windows",
            "window_tools",
        ]
        
        for expected in expected_tools:
            assert expected in tool_names, f"Missing tool: {expected}"

    @pytest.mark.asyncio
    async def test_removed_tools_not_present(self):
        """Test that removed tools are not in the list."""
        from recorder.server import list_tools
        
        tools = await list_tools()
        tool_names = [t.name for t in tools]
        
        removed_tools = [
            "replace_video_audio",
            "merge_audio_tracks",
            "trim_video",
            "get_audio_duration",
            "focus_window",
            "get_window_bounds",
            "list_screens",
            "get_demo_protocol",
        ]
        
        for removed in removed_tools:
            assert removed not in tool_names, f"Tool should be removed: {removed}"

    @pytest.mark.asyncio
    async def test_tools_have_descriptions(self):
        """Test that all tools have descriptions."""
        from recorder.server import list_tools
        
        tools = await list_tools()
        
        for tool in tools:
            assert tool.description, f"Tool {tool.name} missing description"
            assert len(tool.description) > 10, f"Tool {tool.name} has too short description"

    @pytest.mark.asyncio
    async def test_tools_have_input_schemas(self):
        """Test that all tools have input schemas."""
        from recorder.server import list_tools
        
        tools = await list_tools()
        
        for tool in tools:
            assert tool.inputSchema, f"Tool {tool.name} missing input schema"
            assert "type" in tool.inputSchema

    @pytest.mark.asyncio
    async def test_start_recording_has_simplified_schema(self):
        """Test that start_recording has simplified parameters."""
        from recorder.server import list_tools
        
        tools = await list_tools()
        start_recording = next(t for t in tools if t.name == "start_recording")
        
        properties = start_recording.inputSchema.get("properties", {})
        
        # Should have output_path and optionally window_title
        assert "output_path" in properties or properties == {}
        
        # Should NOT have width, height, fps (removed)
        assert "width" not in properties
        assert "height" not in properties
        assert "fps" not in properties

    @pytest.mark.asyncio
    async def test_text_to_speech_has_simplified_schema(self):
        """Test that text_to_speech has simplified parameters."""
        from recorder.server import list_tools
        
        tools = await list_tools()
        tts = next(t for t in tools if t.name == "text_to_speech")
        
        properties = tts.inputSchema.get("properties", {})
        
        # Should have text and output_path
        assert "text" in properties
        assert "output_path" in properties
        
        # Should NOT have voice, engine, api_key (removed)
        assert "voice" not in properties
        assert "engine" not in properties
        assert "api_key" not in properties


class TestFfmpegPath:
    """Tests for ffmpeg path detection."""

    def test_get_ffmpeg_path_common_paths(self):
        """Test that common ffmpeg paths are checked."""
        from recorder.server import get_ffmpeg_path
        
        # This may raise RuntimeError if ffmpeg is not installed
        # but it should not raise other exceptions
        try:
            path = get_ffmpeg_path()
            assert path is not None
            assert "ffmpeg" in path
        except RuntimeError as e:
            assert "ffmpeg not found" in str(e)


class TestOpenAICompatibility:
    """Tests for OpenAI function calling compatibility."""

    @pytest.mark.asyncio
    async def test_all_schemas_have_additional_properties_false(self):
        """Test that all tool schemas have additionalProperties: false for OpenAI strict mode."""
        from recorder.server import list_tools
        
        tools = await list_tools()
        
        for tool in tools:
            schema = tool.inputSchema
            assert "additionalProperties" in schema, f"Tool {tool.name} missing additionalProperties"
            assert schema["additionalProperties"] is False, f"Tool {tool.name} additionalProperties should be False"

    @pytest.mark.asyncio
    async def test_tool_names_are_valid(self):
        """Test that tool names only use allowed characters (a-z, A-Z, 0-9, _)."""
        from recorder.server import list_tools
        import re
        
        tools = await list_tools()
        valid_pattern = re.compile(r'^[a-zA-Z0-9_]+$')
        
        for tool in tools:
            assert valid_pattern.match(tool.name), f"Tool name '{tool.name}' contains invalid characters"

    @pytest.mark.asyncio
    async def test_descriptions_are_reasonable_length(self):
        """Test that descriptions are not too long (OpenAI recommends concise descriptions)."""
        from recorder.server import list_tools
        
        tools = await list_tools()
        max_length = 500  # Reasonable limit for descriptions
        
        for tool in tools:
            assert len(tool.description) <= max_length, f"Tool {tool.name} description too long ({len(tool.description)} chars)"

    @pytest.mark.asyncio
    async def test_required_properties_exist_in_properties(self):
        """Test that all required properties are defined in properties."""
        from recorder.server import list_tools
        
        tools = await list_tools()
        
        for tool in tools:
            schema = tool.inputSchema
            required = schema.get("required", [])
            properties = schema.get("properties", {})
            
            for req in required:
                assert req in properties, f"Tool {tool.name}: required property '{req}' not in properties"


class TestWindowManager:
    """Tests for window manager functionality."""

    def test_window_manager_imports(self):
        """Test that window manager can be imported."""
        from recorder import window_manager
        
        assert hasattr(window_manager, 'list_windows')
        assert hasattr(window_manager, 'check_dependencies')

    def test_window_manager_has_list_windows(self):
        """Test that list_windows function exists."""
        from recorder.window_manager import list_windows
        
        assert callable(list_windows)

    def test_window_manager_has_check_dependencies(self):
        """Test that check_dependencies function exists."""
        from recorder.window_manager import check_dependencies
        
        assert callable(check_dependencies)
        
        # Should return a dict with platform info
        result = check_dependencies()
        assert isinstance(result, dict)
        assert "platform" in result
