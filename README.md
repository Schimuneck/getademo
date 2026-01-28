# getademo

An MCP (Model Context Protocol) server that enables AI agents to create professional demo videos with synchronized voiceover narration. Works with **any website or web application**.

## Features

- **Screen Recording** - Start/stop screen capture with configurable resolution (macOS, Linux, Windows)
- **Text-to-Speech** - Generate voiceover audio using OpenAI TTS or Edge TTS (free)
- **Video Editing** - Trim, concatenate, merge audio tracks
- **Audio-Video Sync** - Automatically adjust video speed to match narration (never cuts content)
- **Demo Protocol** - Built-in best practices guide for creating professional demos

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                     YOUR DEMO REQUEST                       │
│              "Create a demo of Google Search"               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│           cursor-browser-extension MCP                      │
│   (Browser Control: navigate, click, type, screenshot)      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    getademo MCP                             │
│   (Recording, TTS, Video Editing, Audio-Video Sync)         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FINAL DEMO VIDEO                         │
│     Professional demo with synced voiceover narration       │
└─────────────────────────────────────────────────────────────┘
```

## What Can You Demo?

| Demo Type | Examples |
|-----------|----------|
| Search Engines | Google, Bing, DuckDuckGo |
| Web Applications | Gmail, GitHub, Jira, Notion, any SaaS |
| Documentation | README walkthroughs, API docs |
| Data Science | Jupyter notebooks, Google Colab |
| E-commerce | Product browsing, checkout flows |
| Dashboards | Analytics, monitoring tools |
| **Any Website** | If it's in a browser, you can demo it |

## Requirements

- **Python 3.10+**
- **ffmpeg** - For screen recording and video processing
- **OpenAI API key** (optional) - For high-quality TTS voices
- **Cursor IDE** - For MCP integration with AI agents

### Install ffmpeg

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows (with Chocolatey)
choco install ffmpeg
```

## Installation

### Quick Install (Recommended)

The easiest way to install is using the automated installer:

```bash
git clone https://github.com/Schimuneck/getademo.git
cd getademo
./install.sh
```

The installer will:
- Check and install dependencies (ffmpeg, Python 3.10+)
- Create a virtual environment
- Install the package with all TTS engines
- Configure Cursor MCP automatically
- Guide you through screen recording permissions (macOS)

### Manual Installation

#### From PyPI

```bash
pip install getademo

# With OpenAI TTS support
pip install "getademo[openai]"

# With Edge TTS support (free, no API key needed)
pip install "getademo[edge]"

# With both TTS engines
pip install "getademo[all]"
```

#### From Source

```bash
git clone https://github.com/Schimuneck/getademo.git
cd getademo
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[all]"
```

## Configure in Cursor

Add to your Cursor MCP settings (`~/.cursor/mcp.json`):

### Option 1: Using installed package

```json
{
  "mcpServers": {
    "getademo": {
      "command": "getademo",
      "env": {
        "OPENAI_API_KEY": "sk-your-api-key-here"
      }
    }
  }
}
```

### Option 2: Using Python module

```json
{
  "mcpServers": {
    "getademo": {
      "command": "python",
      "args": ["-m", "getademo.server"],
      "env": {
        "OPENAI_API_KEY": "sk-your-api-key-here"
      }
    }
  }
}
```

### Option 3: From source directory

```json
{
  "mcpServers": {
    "getademo": {
      "command": "python",
      "args": ["-m", "getademo.server"],
      "cwd": "/path/to/getademo",
      "env": {
        "PYTHONPATH": "/path/to/getademo/src",
        "OPENAI_API_KEY": "sk-your-api-key-here"
      }
    }
  }
}
```

## Quick Start

### 1. Read the Protocol First

Before creating any demo, the AI agent should read the built-in protocol:

```
get_demo_protocol → Returns mandatory rules and workflow
```

### 2. Basic Demo Workflow

For each step in your demo:

```
1. text_to_speech("Your narration here", "step_01_audio.mp3")
2. start_recording("step_01_raw.mp4")
3. [Perform actions in browser]
4. stop_recording()
5. adjust_video_to_audio_length("step_01_raw.mp4", "step_01_audio.mp3", "step_01_final.mp4")
```

### 3. Final Assembly

```
concatenate_videos(["step_01_final.mp4", "step_02_final.mp4", ...], "final_demo.mp4")
```

## Available Tools

| Tool | Description |
|------|-------------|
| `start_recording` | Start screen recording (1920x1080 default) |
| `stop_recording` | Stop recording and save file |
| `recording_status` | Check if recording is in progress |
| `text_to_speech` | Generate voiceover audio (OpenAI or Edge TTS) |
| `adjust_video_to_audio_length` | **Key tool**: Speed up/slow down video to match audio |
| `concatenate_videos` | Join multiple videos into one |
| `replace_video_audio` | Replace audio track in video |
| `merge_audio_tracks` | Layer multiple audio files on video |
| `trim_video` | Cut video to time range |
| `get_media_info` | Get video/audio metadata |
| `get_audio_duration` | Get exact audio duration |
| `get_demo_protocol` | Retrieve best practices document |

## Key Principle: Speed Adjust, Never Cut

When syncing video with audio, getademo uses **speed adjustment**:

- Video longer than audio → **Speeds up** (faster playback)
- Video shorter than audio → **Slows down** (slower playback)
- **ALL visual content is preserved** - no frames are ever cut

This ensures smooth, professional demos where every action is visible.

## TTS Voice Options

### OpenAI Voices (requires API key)

| Voice | Description |
|-------|-------------|
| `onyx` | Deep, authoritative (recommended for tutorials) |
| `nova` | Friendly, approachable |
| `alloy` | Neutral, balanced |
| `echo` | Warm, conversational |
| `fable` | British accent |
| `shimmer` | Soft, gentle |

### Edge TTS Voices (free, no API key)

| Voice | Description |
|-------|-------------|
| `en-US-AriaNeural` | Female, natural |
| `en-US-GuyNeural` | Male, natural |
| `en-US-JennyNeural` | Female, friendly |
| `en-GB-SoniaNeural` | British female |

## Example: Creating a Google Search Demo

```python
# Step 1: Navigate to Google
browser_navigate("https://www.google.com")
browser_resize(1920, 1080)

# Step 2: Generate audio and record
text_to_speech(
    "Let's search for information about Python programming.",
    "step_01_audio.mp3"
)

start_recording("step_01_raw.mp4")
browser_wait_for(time=2)
browser_type(ref="search_box", text="Python programming", slowly=True)
browser_press_key("Enter")
browser_wait_for(time=3)
stop_recording()

# Step 3: Sync video with audio
adjust_video_to_audio_length(
    "step_01_raw.mp4",
    "step_01_audio.mp3",
    "step_01_final.mp4"
)
```

## Troubleshooting

### Screen Recording Permission (macOS)

If recording fails:
1. Go to **System Settings → Privacy & Security → Screen Recording**
2. Add **Cursor** (or your terminal app) to the allowed list
3. Restart Cursor

### ffmpeg Not Found

Ensure ffmpeg is installed and in your PATH:

```bash
ffmpeg -version
```

### OpenAI API Key Not Working

Set the environment variable:

```bash
export OPENAI_API_KEY="sk-your-key-here"
```

Or provide it in the MCP config (see Configuration section).

## File Organization

Recommended folder structure for demos:

```
demo_recordings/
├── my_demo/
│   ├── steps/
│   │   ├── step_01_raw.mp4
│   │   ├── step_01_audio.mp3
│   │   ├── step_01_final.mp4
│   │   └── ...
│   └── final/
│       └── my_demo_final.mp4
```

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Links

- [GitHub Repository](https://github.com/Schimuneck/getademo)
- [Issue Tracker](https://github.com/Schimuneck/getademo/issues)
- [Changelog](CHANGELOG.md)
