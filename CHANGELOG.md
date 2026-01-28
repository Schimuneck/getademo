# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-01-28

### Added

- Initial release of getademo MCP server
- **Screen Recording**
  - `start_recording` - Start screen capture with configurable resolution
  - `stop_recording` - Stop and save recording
  - `recording_status` - Check recording status
  - Cross-platform support (macOS, Linux, Windows)
- **Text-to-Speech**
  - `text_to_speech` - Generate voiceover audio
  - OpenAI TTS integration (alloy, echo, fable, onyx, nova, shimmer voices)
  - Edge TTS integration (free, no API key required)
- **Video Editing**
  - `adjust_video_to_audio_length` - Sync video speed to match audio duration
  - `concatenate_videos` - Join multiple videos
  - `replace_video_audio` - Replace audio track
  - `merge_audio_tracks` - Layer multiple audio files
  - `trim_video` - Cut video to time range
- **Information Tools**
  - `get_media_info` - Get video/audio metadata
  - `get_audio_duration` - Get exact audio duration
- **Demo Protocol**
  - `get_demo_protocol` - Built-in best practices document
  - Comprehensive guidelines for professional demo creation
- Documentation
  - README with installation and configuration guide
  - Getting started tutorial
  - Complete tools reference
  - Contributing guidelines

### Technical Details

- Built on Model Context Protocol (MCP) for Cursor IDE integration
- Uses ffmpeg for all video/audio processing
- Supports Python 3.10+
- MIT licensed

[Unreleased]: https://github.com/Schimuneck/getademo/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Schimuneck/getademo/releases/tag/v0.1.0


