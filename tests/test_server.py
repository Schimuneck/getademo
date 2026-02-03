"""Tests for demo-recorder MCP server."""

import pytest
from pathlib import Path


class TestProtocol:
    """Tests for the demo protocol guides."""

    def test_get_planning_guide_returns_string(self):
        """Test that get_planning_guide returns the planning document."""
        from recorder.utils.protocol import get_planning_guide
        
        guide = get_planning_guide()
        
        assert isinstance(guide, str)
        assert len(guide) > 0
        assert "PLANNING" in guide or "Demo Planning" in guide

    def test_get_setup_guide_returns_string(self):
        """Test that get_setup_guide returns the setup document."""
        from recorder.utils.protocol import get_setup_guide
        
        guide = get_setup_guide()
        
        assert isinstance(guide, str)
        assert len(guide) > 0
        assert "browser" in guide.lower() or "setup" in guide.lower()

    def test_get_recording_guide_returns_string(self):
        """Test that get_recording_guide returns the recording document."""
        from recorder.utils.protocol import get_recording_guide
        
        guide = get_recording_guide()
        
        assert isinstance(guide, str)
        assert len(guide) > 0
        assert "recording" in guide.lower()

    def test_get_assembly_guide_returns_string(self):
        """Test that get_assembly_guide returns the assembly document."""
        from recorder.utils.protocol import get_assembly_guide
        
        guide = get_assembly_guide()
        
        assert isinstance(guide, str)
        assert len(guide) > 0

    def test_guides_contain_tool_references(self):
        """Test that guides reference the core tools."""
        from recorder.utils.protocol import get_planning_guide, get_recording_guide, get_assembly_guide
        
        all_guides = get_planning_guide() + get_recording_guide() + get_assembly_guide()
        
        assert "start_recording" in all_guides
        assert "stop_recording" in all_guides
        assert "text_to_speech" in all_guides

    def test_guides_emphasize_actions_during_recording(self):
        """Test that guides emphasize performing actions during recording."""
        from recorder.utils.protocol import get_recording_guide
        
        guide = get_recording_guide()
        
        # Should warn against actions outside recording
        assert "WRONG" in guide or "CORRECT" in guide or "DURING" in guide


class TestServerSetup:
    """Tests for server initialization."""

    def test_server_module_imports(self):
        """Test that the server module can be imported."""
        from recorder import server
        
        assert hasattr(server, 'mcp')
        assert hasattr(server, 'run')
        assert hasattr(server, 'backend')

    def test_backend_is_initialized(self):
        """Test that backend is initialized on import."""
        from recorder.server import backend
        
        assert backend is not None
        assert hasattr(backend, 'get_name')
        assert hasattr(backend, 'get_recordings_dir')


class TestCoreTypes:
    """Tests for core types."""
    
    def test_window_bounds_dataclass(self):
        """Test WindowBounds dataclass."""
        from recorder.core.types import WindowBounds
        
        bounds = WindowBounds(x=0, y=0, width=1920, height=1080)
        assert bounds.x == 0
        assert bounds.y == 0
        assert bounds.width == 1920
        assert bounds.height == 1080
    
    def test_window_info_dataclass(self):
        """Test WindowInfo dataclass."""
        from recorder.core.types import WindowInfo, WindowBounds
        
        bounds = WindowBounds(x=0, y=0, width=100, height=100)
        info = WindowInfo(
            title="Test Window",
            window_id="123",
            pid=456,
            bounds=bounds,
            app_name="TestApp"
        )
        assert info.title == "Test Window"
        assert info.pid == 456
        assert info.bounds.width == 100
    
    def test_recording_result_dataclass(self):
        """Test RecordingResult dataclass."""
        from recorder.core.types import RecordingResult
        
        result = RecordingResult(
            success=True,
            message="Recording started",
            file_path=Path("/tmp/test.mp4")
        )
        assert result.success is True
        assert result.message == "Recording started"
    
    def test_recording_state_dataclass(self):
        """Test RecordingState dataclass."""
        from recorder.core.types import RecordingState
        
        state = RecordingState()
        assert state.is_recording() is False
        
        state.reset()
        assert state.process is None


class TestCoreConfig:
    """Tests for core configuration."""
    
    def test_is_container_environment(self):
        """Test container detection."""
        from recorder.core.config import is_container_environment
        
        # On host machine, this should return False
        result = is_container_environment()
        assert isinstance(result, bool)
    
    def test_get_recordings_dir(self):
        """Test recordings directory path."""
        from recorder.core.config import HOST_RECORDINGS_DIR, CONTAINER_RECORDINGS_DIR, is_container_environment
        
        # Just test the path values, not directory creation
        if is_container_environment():
            assert CONTAINER_RECORDINGS_DIR == Path("/app/recordings")
        else:
            assert isinstance(HOST_RECORDINGS_DIR, Path)
    
    def test_get_ffmpeg_path(self):
        """Test ffmpeg path detection."""
        from recorder.core.config import get_ffmpeg_path
        
        try:
            path = get_ffmpeg_path()
            assert path is not None
            assert "ffmpeg" in path
        except RuntimeError as e:
            assert "ffmpeg not found" in str(e)


class TestBackends:
    """Tests for recording backends."""
    
    def test_get_backend_returns_host_on_non_container(self):
        """Test that get_backend returns HostBackend outside container."""
        from recorder.backends import get_backend, HostBackend
        from recorder.core.config import is_container_environment
        
        backend = get_backend()
        
        if not is_container_environment():
            assert isinstance(backend, HostBackend)
    
    def test_backend_has_required_methods(self):
        """Test that backend has all required methods."""
        from recorder.backends import get_backend
        
        backend = get_backend()
        
        assert hasattr(backend, 'get_name')
        assert hasattr(backend, 'get_recordings_dir')
        assert hasattr(backend, 'detect_browser_window')
        assert hasattr(backend, 'get_capture_args')
        assert hasattr(backend, 'get_window_bounds')
        assert hasattr(backend, 'focus_window')
        assert hasattr(backend, 'get_media_url')
        assert hasattr(backend, 'start_recording')
        assert hasattr(backend, 'stop_recording')
        assert hasattr(backend, 'get_recording_status')
    
    def test_host_backend_name(self):
        """Test HostBackend name."""
        from recorder.backends import HostBackend
        import sys
        
        backend = HostBackend()
        name = backend.get_name()
        
        assert "Host" in name
        if sys.platform == "darwin":
            assert "macOS" in name or "AVFoundation" in name


class TestWindowManager:
    """Tests for window manager functionality."""

    def test_window_manager_imports(self):
        """Test that window manager can be imported."""
        from recorder.utils import window_manager
        
        assert hasattr(window_manager, 'list_windows')
        assert hasattr(window_manager, 'check_dependencies')

    def test_window_manager_has_list_windows(self):
        """Test that list_windows function exists."""
        from recorder.utils.window_manager import list_windows
        
        assert callable(list_windows)

    def test_window_manager_has_check_dependencies(self):
        """Test that check_dependencies function exists."""
        from recorder.utils.window_manager import check_dependencies
        
        assert callable(check_dependencies)
        
        # Should return a dict with platform info
        result = check_dependencies()
        assert isinstance(result, dict)
        assert "platform" in result
        assert "available" in result
        assert "missing" in result
        assert "message" in result


class TestUtils:
    """Tests for utility functions."""
    
    def test_ffmpeg_utils_imports(self):
        """Test FFmpeg utilities import."""
        from recorder.utils.ffmpeg import (
            get_ffmpeg_path,
            get_ffprobe_path,
            get_media_info,
        )
        
        assert callable(get_ffmpeg_path)
        assert callable(get_ffprobe_path)
        assert callable(get_media_info)
    
    def test_protocol_utils_imports(self):
        """Test protocol utilities import."""
        from recorder.utils.protocol import (
            get_planning_guide,
            get_setup_guide,
            get_recording_guide,
            get_assembly_guide,
        )
        
        assert callable(get_planning_guide)
        assert callable(get_setup_guide)
        assert callable(get_recording_guide)
        assert callable(get_assembly_guide)


class TestToolsModule:
    """Tests for tools module."""
    
    def test_tools_module_imports(self):
        """Test that tools module can be imported."""
        from recorder.tools import register_all_tools
        
        assert callable(register_all_tools)
    
    def test_individual_tool_modules_import(self):
        """Test individual tool modules import."""
        from recorder.tools import (
            register_recording_tools,
            register_tts_tools,
            register_video_tools,
            register_guide_tools,
            register_window_tools,
        )
        
        assert callable(register_recording_tools)
        assert callable(register_tts_tools)
        assert callable(register_video_tools)
        assert callable(register_guide_tools)
        assert callable(register_window_tools)
