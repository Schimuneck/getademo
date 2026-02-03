# Demo Recorder MCP

An MCP (Model Context Protocol) server that enables AI agents to create professional demo videos with synchronized voiceover narration. Works with **any website or web application**.

## Features

- **Screen Recording** - Capture browser windows at 30fps
- **Text-to-Speech** - Generate voiceover using OpenAI TTS (with API key) or Edge TTS (free)
- **Audio-Video Sync** - Adjust video speed to match narration length (preserves all content)
- **Scene-Based Workflow** - Built-in guides enforce short, manageable recordings
- **Multiple Modes** - Container (recommended), HTTP/SSE, or native host mode

## Three Access Modes

| Mode | Transport | Browser | Use Case |
|------|-----------|---------|----------|
| **Container STDIO** | STDIO | Playwright (included) | **Recommended** - Self-contained, all 36 tools |
| **Container HTTP** | HTTP/SSE | Playwright (included) | OpenAI Responses API, remote access |
| **Host** | STDIO | cursor-browser-extension | Native browser, macOS screen capture |

## Quick Start

### Option 1: Container STDIO Mode (Recommended)

This is the **preferred way** to run demo-recorder-mcp. It includes Playwright browser automation and works fully self-contained with all 36 tools (14 demo-recorder + 22 Playwright).

```bash
# Clone and build
git clone https://github.com/Schimuneck/demo-recorder-mcp.git
cd demo-recorder-mcp
podman build -t demo-recorder-mcp .  # or: docker build -t demo-recorder-mcp .
```

Add to Cursor MCP settings (`~/.cursor/mcp.json`):

**For Podman (macOS/Linux):**
```json
{
  "mcpServers": {
    "demo-recorder": {
      "command": "podman",
      "args": [
        "run", "-i", "--rm",
        "-v", "/path/to/recordings:/app/recordings",
        "-e", "OPENAI_API_KEY=sk-your-key",
        "demo-recorder-mcp",
        "/app/run-mcp.sh", "multi-stdio"
      ]
    }
  }
}
```

**For Docker:**
```json
{
  "mcpServers": {
    "demo-recorder": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "--add-host=host.docker.internal:host-gateway",
        "-v", "/path/to/recordings:/app/recordings",
        "-e", "OPENAI_API_KEY=sk-your-key",
        "demo-recorder-mcp",
        "/app/run-mcp.sh", "multi-stdio"
      ]
    }
  }
}
```

> **Note:** To access local dev servers from the container, see [Accessing Host Services](#accessing-host-services-from-container).

### Option 2: Container HTTP/SSE Mode

For OpenAI Responses API or remote access:

```bash
# Build HTTP image
podman build -f Dockerfile.http -t demo-recorder-mcp:http .

# Start container with HTTP server
podman run -d --name demo-recorder \
  -p 8081:8081 -p 8080:8080 \
  -v ./recordings:/app/recordings \
  -e OPENAI_API_KEY=sk-your-key \
  demo-recorder-mcp:http
```

Add to Cursor MCP settings:

```json
{
  "mcpServers": {
    "demo-recorder": {
      "url": "http://localhost:8081/mcp/",
      "transport": "streamable-http"
    }
  }
}
```

### Option 3: Host Mode (Native)

```bash
# Clone and run installer (recommended)
git clone https://github.com/Schimuneck/demo-recorder-mcp.git
cd demo-recorder-mcp
./install.sh
```

The installer will:
- Check/install ffmpeg
- Check/install window tools (Linux only)
- Create virtual environment and install package
- Configure Cursor MCP automatically
- Remind about screen recording permission (macOS)

**Manual installation** (if you prefer):
```bash
git clone https://github.com/Schimuneck/demo-recorder-mcp.git
cd demo-recorder-mcp
python -m venv .venv && source .venv/bin/activate
pip install -e ".[all]"
```

Add to Cursor MCP settings:

```json
{
  "mcpServers": {
    "demo-recorder-local": {
      "command": "/path/to/demo-recorder-mcp/.venv/bin/recorder",
      "env": {
        "OPENAI_API_KEY": "sk-your-key",
        "RECORDINGS_DIR": "/path/to/recordings"
      }
    }
  }
}
```

Host mode uses **cursor-browser-extension** for browser automation - the demo-recorder captures the visible browser window.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Container Mode                            │
│  ┌───────────────┐  ┌───────────────┐  ┌─────────────────────┐  │
│  │    Xvfb       │  │   Playwright  │  │   Demo Recorder     │  │
│  │  DISPLAY=:99  │◄─│    Browser    │  │   MCP (FFmpeg)      │  │
│  │  2560x1440    │  │   (Firefox)   │  │                     │  │
│  └───────────────┘  └───────────────┘  └─────────────────────┘  │
│         │                                        │               │
│         └──────────► x11grab capture ◄───────────┘               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                          Host Mode                               │
│  ┌───────────────────────┐      ┌─────────────────────────────┐ │
│  │  cursor-browser-ext   │      │      Demo Recorder          │ │
│  │  (opens real browser) │◄────▶│      MCP (FFmpeg)           │ │
│  │                       │      │   AVFoundation/gdigrab      │ │
│  └───────────────────────┘      └─────────────────────────────┘ │
│                                          │                       │
│                  native screen capture ◄─┘                       │
└─────────────────────────────────────────────────────────────────┘
```

## Available Tools

### Recording Tools
| Tool | Description |
|------|-------------|
| `start_recording` | Start video recording (auto-detects browser window) |
| `stop_recording` | Stop recording and save the video file |
| `recording_status` | Check if recording is in progress |

### Audio Tools
| Tool | Description |
|------|-------------|
| `text_to_speech` | Generate voiceover (OpenAI TTS with API key, else Edge TTS) |

### Video Editing Tools
| Tool | Description |
|------|-------------|
| `adjust_video_to_audio` | Sync video duration to audio by adjusting playback speed |
| `concatenate_videos` | Join multiple scene videos into final demo |
| `media_info` | Get duration, resolution, codec info for media files |
| `list_media_files` | List all recordings with URLs (container mode) |

### Protocol Guides
| Tool | Description |
|------|-------------|
| `planning_phase_1` | Demo planning guide - call FIRST |
| `setup_phase_2` | Browser setup guide |
| `recording_phase_3` | Recording actions guide |
| `editing_phase_4` | Post-recording assembly guide |

### Utility Tools
| Tool | Description |
|------|-------------|
| `list_windows` | List visible windows |
| `window_tools` | Check window management tool availability |

**Container mode** also includes all 22 **Playwright browser tools** (`browser_navigate`, `browser_click`, `browser_snapshot`, etc.) through the proxy multiplexer.

## Project Structure

```
demo-recorder-mcp/
├── src/recorder/
│   ├── server.py           # Entry point (~40 lines)
│   ├── core/               # Shared types and config
│   │   ├── types.py        # WindowBounds, RecordingState, etc.
│   │   └── config.py       # Environment detection, paths
│   ├── backends/           # Recording implementations
│   │   ├── base.py         # Abstract RecordingBackend interface
│   │   ├── container.py    # x11grab + Xvfb
│   │   └── host.py         # AVFoundation (macOS), gdigrab (Win)
│   ├── tools/              # MCP tool definitions
│   │   ├── recording.py    # start/stop_recording
│   │   ├── tts.py          # text_to_speech
│   │   ├── video.py        # concatenate, adjust, media_info
│   │   ├── guides.py       # Protocol phase guides
│   │   └── windows.py      # list_windows, window_tools
│   ├── transports/         # HTTP/SSE server and multiplexer
│   │   ├── http.py
│   │   └── multiplexer.py
│   └── utils/              # Shared utilities
│       ├── ffmpeg.py       # FFmpeg helpers
│       ├── window_manager.py  # Cross-platform window detection
│       └── protocol.py     # Recording workflow guides
├── scripts/                # Container startup scripts
├── tests/                  # Test suite
├── Dockerfile              # STDIO container
├── Dockerfile.http         # HTTP/SSE container
└── pyproject.toml
```

## Scene-Based Workflow

Demos are recorded as **short scenes (10-30 seconds each)**, not one long video.

### Per-Scene Process

```
SCENE N:
1. browser_snapshot()            # Verify starting position
2. start_recording()             # START recording
3. browser_wait_for(time=2)      # Viewer sees initial state
4. [scroll, click, or type]      # ACTION captured on video!
5. browser_wait_for(time=2)      # Viewer sees result
6. stop_recording()              # STOP recording
7. text_to_speech("...")         # Generate audio
8. adjust_video_to_audio(...)    # Sync video to audio
9. [Repeat for next scene]
```

### Critical: Actions DURING Recording

**WRONG** (static video):
```python
browser_scroll(400)           # NOT recorded
start_recording()
browser_wait_for(time=5)      # Static page
stop_recording()
```

**CORRECT** (dynamic video):
```python
start_recording()
browser_wait_for(time=2)
browser_scroll(400)           # CAPTURED!
browser_wait_for(time=2)
stop_recording()
```

## Complete Example

```python
# === SETUP ===
browser_navigate(url="https://example.com")
browser_resize(width=1920, height=1080)

# === SCENE 1: Homepage ===
browser_snapshot()
start_recording(filename="scene1_raw.mp4")
browser_wait_for(time=2)
browser_scroll(direction="down", amount=400)
browser_wait_for(time=2)
stop_recording()

text_to_speech(
    text="Welcome. As we scroll down, see the key features.",
    filename="scene1_audio.mp3"
)

adjust_video_to_audio(
    video_filename="scene1_raw.mp4",
    audio_filename="scene1_audio.mp3",
    output_filename="scene1_final.mp4"
)

# === FINAL ===
concatenate_videos(
    filenames=["scene1_final.mp4", "scene2_final.mp4"],
    output_filename="demo_final.mp4"
)

media_info(filename="demo_final.mp4")
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | (none) | OpenAI API key for TTS |
| `RECORDINGS_DIR` | `~/recordings` (host), `/app/recordings` (container) | Output directory |
| `VIDEO_SERVER_PORT` | `8080` | Video HTTP server port (container) |
| `VIDEO_SERVER_HOST` | `localhost` | Video server hostname |

## Text-to-Speech

The `text_to_speech` tool automatically selects the best available engine:

| Engine | When Used | Voice |
|--------|-----------|-------|
| OpenAI TTS | When `OPENAI_API_KEY` set | "onyx" (professional) |
| Edge TTS | Fallback (free) | "en-US-GuyNeural" |

## Accessing Host Services from Container

When running in container mode, you may want to record demos for local development servers (e.g., `localhost:3000`). By default, `localhost` inside a container refers to the container itself, not your host machine.

### Podman (macOS/Linux)

Podman automatically provides `host.containers.internal` which resolves to your host machine:

```python
# Navigate to your local dev server
browser_navigate(url="http://host.containers.internal:3000")
```

**No extra flags needed** - this works out of the box with Podman.

**Important:** Your dev server must allow connections from this hostname. For Vite, add to `vite.config.ts`:

```typescript
export default defineConfig({
  server: {
    host: true,
    allowedHosts: ['host.containers.internal'],
  },
})
```

### Docker

Docker requires the `--add-host` flag to enable host access:

```json
"args": [
    "run", "-i", "--rm",
    "--add-host=host.docker.internal:host-gateway",
    "-v", "/path/to/recordings:/app/recordings",
    "-e", "OPENAI_API_KEY=sk-your-key",
    "demo-recorder-mcp",
    "/app/run-mcp.sh", "multi-stdio"
]
```

Then navigate using:

```python
browser_navigate(url="http://host.docker.internal:3000")
```

**Important:** Your dev server must allow connections from this hostname. For Vite, add to `vite.config.ts`:

```typescript
export default defineConfig({
  server: {
    host: true,
    allowedHosts: ['host.docker.internal'],
  },
})
```

### Summary Table

| Runtime | Hostname | Extra Flags Needed |
|---------|----------|-------------------|
| Podman | `host.containers.internal` | None |
| Docker | `host.docker.internal` | `--add-host=host.docker.internal:host-gateway` |

## Troubleshooting

### Container: No Windows Found

`list_windows()` requires a browser window to exist:
```python
browser_navigate(url="https://example.com")  # First!
list_windows()  # Now returns Firefox window
```

### Host Mode: Screen Recording Permission (macOS)

1. **System Settings → Privacy & Security → Screen Recording**
2. Add **Cursor** to allowed list
3. Restart Cursor

### Video Out of Sync

Break demos into shorter scenes (10-30 seconds). Long recordings need extreme speed adjustments.

### Container HTTP: Health Check

```bash
curl http://localhost:8081/health
# {"status":"healthy","service":"demo-recorder-mcp","tools_count":36}
```

## Development

```bash
# Setup
git clone https://github.com/Schimuneck/demo-recorder-mcp.git
cd demo-recorder-mcp
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Build container
podman build -t demo-recorder-mcp .
podman build -f Dockerfile.http -t demo-recorder-mcp:http .
```

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT License - see [LICENSE](LICENSE).
