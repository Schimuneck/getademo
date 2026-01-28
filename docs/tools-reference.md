# Tools Reference

Complete API reference for all getademo MCP tools.

## Recording Tools

### start_recording

Start screen recording. Returns immediately while recording runs in the background.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `output_path` | string | Yes | - | Full path where the video will be saved (e.g., `/path/to/demo.mp4`) |
| `width` | integer | No | 1920 | Recording width in pixels |
| `height` | integer | No | 1080 | Recording height in pixels |
| `fps` | integer | No | 30 | Frames per second |
| `screen_index` | integer | No | 1 | Screen device index (macOS: 1=screen 0, 2=screen 1) |

**Example:**
```json
{
  "output_path": "/Users/demo/recordings/step_01.mp4",
  "width": 1920,
  "height": 1080,
  "screen_index": 1
}
```

**Returns:**
```
Recording started!
Output: /Users/demo/recordings/step_01.mp4
Resolution: 1920x1080 @ 30fps
Screen: 1
Started at: 14:30:45

Use 'stop_recording' when done.
```

---

### stop_recording

Stop the current screen recording and save the file.

**Parameters:** None

**Example:**
```json
{}
```

**Returns:**
```
Recording stopped!
Output: /Users/demo/recordings/step_01.mp4
Duration: 15.2 seconds
File size: 2.4 MB
```

---

### recording_status

Check if recording is in progress and get details.

**Parameters:** None

**Example:**
```json
{}
```

**Returns:**
```
Recording in progress
Output: /Users/demo/recordings/step_01.mp4
Duration: 8.5 seconds
Started: 14:30:45
```

---

## Text-to-Speech Tools

### text_to_speech

Convert text to speech audio file using OpenAI TTS or Edge TTS.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `text` | string | Yes | - | The text to convert to speech |
| `output_path` | string | Yes | - | Full path where the audio will be saved |
| `voice` | string | No | "onyx" | Voice to use (see voice options below) |
| `engine` | string | No | "openai" | TTS engine: "openai" or "edge" |
| `api_key` | string | No | - | OpenAI API key (uses env var if not provided) |

**OpenAI Voices:**
- `onyx` - Deep, authoritative
- `nova` - Friendly, approachable
- `alloy` - Neutral, balanced
- `echo` - Warm, conversational
- `fable` - British accent
- `shimmer` - Soft, gentle

**Edge TTS Voices:**
- `en-US-AriaNeural` - Female, natural
- `en-US-GuyNeural` - Male, natural
- `en-US-JennyNeural` - Female, friendly
- `en-GB-SoniaNeural` - British female

**Example:**
```json
{
  "text": "Welcome to this demo of Google Search.",
  "output_path": "/Users/demo/recordings/step_01_audio.mp3",
  "voice": "onyx",
  "engine": "openai"
}
```

**Returns:**
```
Audio generated!
Output: /Users/demo/recordings/step_01_audio.mp3
Engine: openai (onyx)
Duration: 3.5 seconds
Size: 56.2 KB
Text length: 42 characters
```

---

## Video Editing Tools

### adjust_video_to_audio_length

**KEY TOOL**: Speed up or slow down video to match audio length exactly. Does NOT cut/trim - ALL visual content is preserved.

- Video longer than audio → speeds up
- Video shorter than audio → slows down

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `video_path` | string | Yes | - | Path to the input video file |
| `audio_path` | string | Yes | - | Path to the audio file (determines target duration) |
| `output_path` | string | Yes | - | Path for the output video with adjusted speed |
| `add_audio` | boolean | No | true | Merge the audio into the output video |

**Example:**
```json
{
  "video_path": "/Users/demo/recordings/step_01_raw.mp4",
  "audio_path": "/Users/demo/recordings/step_01_audio.mp3",
  "output_path": "/Users/demo/recordings/step_01_final.mp4",
  "add_audio": true
}
```

**Returns:**
```
Video speed adjusted to match audio!
Action: speed up
Speed: 1.25x faster
Video: 15.00s -> 12.00s
Audio: 12.00s
Audio merged: true
Output: /Users/demo/recordings/step_01_final.mp4
Size: 1.8 MB
ALL visual content preserved (no frames cut)
```

---

### concatenate_videos

Concatenate multiple videos into one.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `video_paths` | array[string] | Yes | - | List of video file paths in order |
| `output_path` | string | Yes | - | Path for the concatenated video |

**Example:**
```json
{
  "video_paths": [
    "/Users/demo/recordings/step_01_final.mp4",
    "/Users/demo/recordings/step_02_final.mp4",
    "/Users/demo/recordings/step_03_final.mp4"
  ],
  "output_path": "/Users/demo/recordings/final_demo.mp4"
}
```

**Returns:**
```
Videos concatenated!
Output: /Users/demo/recordings/final_demo.mp4
Videos merged: 3
```

---

### replace_video_audio

Replace the audio track in a video with a new audio file.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `video_path` | string | Yes | - | Path to the input video file |
| `audio_path` | string | Yes | - | Path to the new audio file |
| `output_path` | string | Yes | - | Path for the output video |
| `audio_start_time` | number | No | 0 | When to start the audio in the video (seconds) |
| `trim_to_audio` | boolean | No | true | Trim video to match audio duration |

**Example:**
```json
{
  "video_path": "/Users/demo/recordings/video.mp4",
  "audio_path": "/Users/demo/recordings/new_audio.mp3",
  "output_path": "/Users/demo/recordings/video_with_new_audio.mp4"
}
```

**Returns:**
```
Audio replaced!
Output: /Users/demo/recordings/video_with_new_audio.mp4
Audio start: 0s
File size: 2.1 MB
```

---

### merge_audio_tracks

Merge multiple audio files with specified start times onto a video.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `video_path` | string | Yes | - | Path to the input video file |
| `audio_tracks` | array[object] | Yes | - | List of audio tracks with start times |
| `output_path` | string | Yes | - | Path for the output video |
| `keep_original_audio` | boolean | No | false | Keep the original video audio |

**Audio track object:**
```json
{
  "path": "/path/to/audio.mp3",
  "start_time": 5.0
}
```

**Example:**
```json
{
  "video_path": "/Users/demo/recordings/video.mp4",
  "audio_tracks": [
    {"path": "/Users/demo/audio1.mp3", "start_time": 0},
    {"path": "/Users/demo/audio2.mp3", "start_time": 10}
  ],
  "output_path": "/Users/demo/recordings/merged.mp4",
  "keep_original_audio": false
}
```

**Returns:**
```
Audio tracks merged!
Output: /Users/demo/recordings/merged.mp4
Tracks merged: 2
Original audio kept: false
```

---

### trim_video

Trim a video to a specific time range.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `video_path` | string | Yes | - | Path to the input video file |
| `output_path` | string | Yes | - | Path for the trimmed video |
| `start_time` | number | No | 0 | Start time in seconds |
| `end_time` | number | No | - | End time in seconds (trims to end if not specified) |
| `duration` | number | No | - | Duration in seconds (alternative to end_time) |

**Example:**
```json
{
  "video_path": "/Users/demo/recordings/video.mp4",
  "output_path": "/Users/demo/recordings/trimmed.mp4",
  "start_time": 5,
  "end_time": 20
}
```

**Returns:**
```
Video trimmed!
Output: /Users/demo/recordings/trimmed.mp4
Start: 5s
```

---

## Information Tools

### get_media_info

Get information about a video or audio file (duration, resolution, etc.).

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `file_path` | string | Yes | - | Path to the media file |

**Example:**
```json
{
  "file_path": "/Users/demo/recordings/demo.mp4"
}
```

**Returns:**
```
Media Info: demo.mp4
Duration: 45.3s (0.8m)
Size: 8.2 MB
Video: 1920x1080 @ 30/1 (h264)
Audio: 44100Hz, 2ch (aac)
```

---

### get_audio_duration

Get the exact duration of an audio file in seconds.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `audio_path` | string | Yes | - | Path to the audio file |

**Example:**
```json
{
  "audio_path": "/Users/demo/recordings/voiceover.mp3"
}
```

**Returns:**
```
Audio Duration
File: voiceover.mp3
Duration: 12.456 seconds (0.21 minutes)
```

---

### get_demo_protocol

Get the comprehensive demo recording protocol document. **READ THIS FIRST** before creating any demo.

**Parameters:** None

**Example:**
```json
{}
```

**Returns:** The full demo recording protocol document with best practices for:
- Preparation
- Recording
- Error recovery
- Final assembly

---

## Typical Workflow

Here's how to use these tools together for a typical demo:

```
# For each step:
1. text_to_speech → Generate narration audio
2. start_recording → Begin screen capture
3. [Perform browser actions]
4. stop_recording → End capture
5. adjust_video_to_audio_length → Sync video to narration

# After all steps:
6. concatenate_videos → Combine into final demo
7. get_media_info → Verify final output
```


