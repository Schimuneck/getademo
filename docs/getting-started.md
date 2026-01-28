# Getting Started with getademo

This guide will help you set up getademo and create your first demo video.

## Prerequisites

Before you begin, ensure you have:

- **Python 3.10 or higher**
- **ffmpeg** installed and in your PATH
- **Cursor IDE** with MCP support
- (Optional) **OpenAI API key** for high-quality TTS

### Installing ffmpeg

**macOS (using Homebrew):**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows (using Chocolatey):**
```bash
choco install ffmpeg
```

Verify installation:
```bash
ffmpeg -version
```

## Installation

### Option 1: Automated Install (Recommended)

The easiest way to get started:

```bash
git clone https://github.com/Schimuneck/getademo.git
cd getademo
./install.sh
```

The installer handles everything:
- Checks Python 3.10+ and ffmpeg (offers to install if missing)
- Creates an isolated virtual environment
- Installs all dependencies
- Configures Cursor MCP automatically
- Prompts for OpenAI API key (optional)
- Guides you through macOS screen recording permissions

### Option 2: Install from PyPI

```bash
# Basic installation
pip install getademo

# With OpenAI TTS support
pip install "getademo[openai]"

# With free Edge TTS support
pip install "getademo[edge]"

# With both TTS engines
pip install "getademo[all]"
```

### Option 3: Install from Source (Manual)

```bash
git clone https://github.com/Schimuneck/getademo.git
cd getademo
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[all]"
```

## Configure Cursor

Add getademo to your Cursor MCP settings.

### Find your MCP config file

- **macOS/Linux:** `~/.cursor/mcp.json`
- **Windows:** `%APPDATA%\Cursor\mcp.json`

### Add the configuration

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

> **Note:** If you don't have an OpenAI API key, you can skip the `OPENAI_API_KEY` and use Edge TTS instead (free, no API key needed).

### Restart Cursor

After saving the configuration, restart Cursor to load the MCP server.

## Screen Recording Permission (macOS)

On macOS, you need to grant screen recording permission:

1. Go to **System Settings** → **Privacy & Security** → **Screen Recording**
2. Click the **+** button
3. Add **Cursor** (or your terminal app)
4. Restart Cursor

## Your First Demo

### Step 1: Read the Protocol

Before creating any demo, have the AI agent read the built-in protocol:

```
"Read the demo protocol first"
```

The agent will call `get_demo_protocol` to retrieve best practices.

### Step 2: Plan Your Demo

Structure your demo into steps:

```
Demo: How to Use Google Search
├── Step 1: Navigate to Google (5s)
├── Step 2: Type a search query (10s)
├── Step 3: View results (10s)
└── Step 4: Click a result (8s)
```

### Step 3: Create Each Step

For each step, the workflow is:

1. **Generate audio** using `text_to_speech`
2. **Start recording** using `start_recording`
3. **Perform actions** (navigate, click, type)
4. **Stop recording** using `stop_recording`
5. **Sync video to audio** using `adjust_video_to_audio_length`

### Step 4: Assemble Final Video

Combine all steps using `concatenate_videos`:

```
concatenate_videos(
    ["step_01_final.mp4", "step_02_final.mp4", "step_03_final.mp4"],
    "final_demo.mp4"
)
```

## Example Conversation

Here's an example of how to request a demo:

```
User: Create a demo showing how to search for "Python tutorials" on Google.

Agent: I'll create a demo of Google Search. Let me first read the demo protocol.
[Calls get_demo_protocol]

Agent: Now I'll create the demo step by step...

[Step 1: Generate narration]
[Calls text_to_speech with "Let's search for Python tutorials on Google"]

[Step 2: Record the action]
[Calls start_recording]
[Navigates to Google, types query, shows results]
[Calls stop_recording]

[Step 3: Sync audio and video]
[Calls adjust_video_to_audio_length]

Agent: Demo complete! The final video is saved at final_demo.mp4
```

## Using Edge TTS (Free Alternative)

If you don't have an OpenAI API key, use Edge TTS:

```
text_to_speech(
    text="Your narration here",
    output_path="audio.mp3",
    engine="edge",
    voice="en-US-AriaNeural"
)
```

Available Edge voices:
- `en-US-AriaNeural` - Female, natural
- `en-US-GuyNeural` - Male, natural
- `en-US-JennyNeural` - Female, friendly
- `en-GB-SoniaNeural` - British female

## Troubleshooting

### "ffmpeg not found"

Ensure ffmpeg is installed and in your PATH:
```bash
which ffmpeg  # macOS/Linux
where ffmpeg  # Windows
```

### "Screen recording failed"

On macOS, grant screen recording permission (see above).

### "OpenAI API key required"

Either:
1. Set `OPENAI_API_KEY` in your environment or MCP config
2. Use Edge TTS instead: `engine="edge"`

### Videos are choppy

Ensure your system can handle screen recording at 1920x1080. Try:
- Closing unnecessary applications
- Reducing browser tabs
- Using a lower resolution: `width=1280, height=720`

## Next Steps

- Read the [Tools Reference](tools-reference.md) for detailed API documentation
- Check the [Demo Protocol](../src/getademo/protocol.py) for best practices
- Explore example demos in the `docs/examples/` directory

