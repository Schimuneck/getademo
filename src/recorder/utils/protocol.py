"""
Demo Recording Protocol - Split into 4 Phase-Based Guides

This module contains the demo recording protocol split into focused guides:
1. get_planning_guide() - Phase 1: How to plan your demo
2. get_setup_guide() - Phase 2: Pre-recording setup and verification
3. get_recording_guide() - Phase 3: What to do DURING recording
4. get_assembly_guide() - Phase 4: Post-recording assembly and troubleshooting

The original get_protocol() is deprecated but kept for backwards compatibility.

Guides are MODE-AWARE: Container mode shows Xvfb/Firefox-specific content,
while Host mode shows platform-native (macOS/Linux/Windows) content.
"""

from ..core.config import is_container_environment

# =============================================================================
# PHASE 1: PLANNING GUIDE
# =============================================================================

PLANNING_GUIDE = """
# Phase 1: Demo Planning

Call this FIRST. Covers demo structure, workflow, and scripting.
Next phase: setup_phase_2()

---

## CRITICAL RULE: ONE SCENE = ONE RECORDING

**NEVER record one long continuous video for an entire demo.**

WHY: Audio-video sync only works per-scene. If you record a 2-minute video and
generate a 90-second audio, the ENTIRE video plays at 1.3x speed - making some
parts too fast and others out of sync with narration.

**CORRECT approach:**
```
Scene 1: start_recording(window_title="Google Chrome") -> actions -> stop_recording() -> audio -> sync
Scene 2: start_recording(window_title="Google Chrome") -> actions -> stop_recording() -> audio -> sync
Scene 3: start_recording(window_title="Google Chrome") -> actions -> stop_recording() -> audio -> sync
Final:   concatenate_videos([scene1, scene2, scene3])
```

**WRONG approach:**
```
start_recording()
[all demo actions for 2+ minutes]
stop_recording()
# Now audio sync is impossible!
```

Each scene should be 10-30 seconds. Stop and restart recording for each logical
section, even if continuing on the same page.

---

## Core Workflow: Per-Scene Process

Complete EACH scene fully before starting the next:

```
SCENE N:
1. PRE-SCREENSHOT   - browser_snapshot() - verify starting position
2. START RECORDING  - start_recording()
3. PERFORM ACTIONS  - scroll, click, type DURING recording
4. STOP RECORDING   - stop_recording()
5. POST-SCREENSHOT  - browser_snapshot() - verify ending state
6. WRITE SCRIPT     - Describe the action and result
7. GENERATE AUDIO   - text_to_speech(script)
8. SYNC             - adjust_video_to_audio()
9. NEXT SCENE       - Repeat for scene N+1
```

## CRITICAL: Actions DURING Recording, Not Before

**WRONG** - Static boring video:
```python
browser_scroll(...)           # Action happens BEFORE recording
browser_click(...)            # Viewer sees nothing
start_recording(window_title="Google Chrome")  # Records static result
browser_wait_for(time=3)
stop_recording()              # Boring! No motion captured
```

**CORRECT** - Dynamic engaging video:
```python
start_recording(window_title="Google Chrome")  # Start FIRST, specify browser!
browser_wait_for(time=2)      # Brief pause
browser_scroll(...)           # Action captured on video!
browser_wait_for(time=2)      # Viewer sees result
stop_recording()              # Exciting! Motion captured
```

The whole point of video is to show MOTION. If you do actions before recording,
you're just taking an expensive screenshot.

Why this order:
- Video captures the ACTION, not just the result
- Viewers see what's happening, not just what happened
- Script describes the motion: "Watch as we scroll down..."

---

## Demo Structure

One demo = multiple scenes. Each scene = one recording + one audio file.

```
Demo: "Product Tour"
  Scene 1: Homepage intro       - 15s video, 15s audio
  Scene 2: Feature overview     - 20s video, 18s audio  
  Scene 3: Click-through demo   - 25s video, 22s audio
  Scene 4: Conclusion           - 10s video, 12s audio
  Final:   Concatenate all      - ~70s total
```

Scene duration guidelines:
| Type              | Duration    |
|-------------------|-------------|
| Intro             | 10-15s      |
| Simple action     | 15-25s      |
| Complex workflow  | 20-30s      |
| Conclusion        | 10-15s      |

**MAX scene length: 30 seconds.** Longer scenes = harder to sync audio.

---

## Per-Scene Template

```
SCENE N: [Name] (target: 15-25 seconds)

A. PRE-RECORD (outside recording)
   browser_snapshot()                    # Verify starting position
   # Do NOT perform actions here - they won't be recorded!

B. RECORD (actions happen HERE)
   start_recording(output_path="sceneN_raw.mp4")
   browser_wait_for(time=2)              # Viewer sees starting state
   # === ACTION HERE - THIS IS WHAT GETS RECORDED ===
   # scroll, click, hover, type - all captured on video
   browser_wait_for(time=2)              # Viewer sees result
   stop_recording()

C. POST-RECORD (outside recording)
   browser_snapshot()                    # Verify ending state

D. SCRIPT
   Describe the ACTION: "Watch as we scroll..." "Clicking here reveals..."

E. AUDIO
   text_to_speech(text="...", output_path="sceneN_audio.mp3")

F. SYNC
   adjust_video_to_audio(...)

G. NEXT SCENE
```

**CRITICAL: Actions between start_recording() and stop_recording() are captured.
Actions before start_recording() are NOT captured - the video would be static.**

---

## When to Split Scenes

Split into separate scenes when:
- Showing a different feature
- Navigating to a new page  
- Performing a different type of action
- Narration focus changes

Example - BAD (one long recording):
```
start_recording()
[scroll page, click button, fill form, submit, show results]
stop_recording()
# 90 second video - impossible to sync narration!
```

Example - GOOD (multiple scenes):
```
Scene 1: Scroll to feature section (15s)
Scene 2: Click button, show modal (20s)
Scene 3: Fill form fields (20s)
Scene 4: Submit and show results (15s)
# Each scene synced to its own narration
```

---

## Script Guidelines

- Conversational tone
- 15-25 seconds per scene (matches video length)
- Describe what viewer sees
- Match narration timing to action timing

---

## Final Assembly

After ALL scenes recorded and synced:
```
concatenate_videos(
    video_paths=["scene1_final.mp4", "scene2_final.mp4", ...],
    output_path="demo_final.mp4"
)
```

---

NEXT: Call setup_phase_2() for browser setup and verification.
"""


# =============================================================================
# PHASE 2: RECORDING SETUP GUIDE (MODE-AWARE)
# =============================================================================

# Common sections shared between container and host modes
SETUP_GUIDE_HEADER = """
# Phase 2: Recording Setup

Pre-recording setup and verification. Call after planning_phase_1().
Next phase: recording_phase_3()

---
"""

# Container-specific environment section
SETUP_GUIDE_CONTAINER_ENV = """
## REMINDER: Real Video Recording Works

Use start_recording() and stop_recording() - they produce REAL video files.
Do NOT fall back to screenshots. Do NOT use Playwright video features.

The container has Xvfb (virtual display) which makes the browser recordable.
This is not a workaround - this is the intended, working approach.

---

## Container Environment

Xvfb virtual display at :99, resolution 2560x1440 (plenty of headroom).
Firefox browser renders to this display with NO window decorations.
Recording captures via FFmpeg x11grab.
"""

# Host-specific environment section
SETUP_GUIDE_HOST_ENV = """
## Recording Environment

Recording uses native screen capture for your platform:
- macOS: AVFoundation with multi-monitor support
- Linux: x11grab from your display
- Windows: gdigrab

The recorder auto-detects your browser window (Chrome, Firefox, Safari, Arc, Brave, Edge, or Cursor IDE's embedded browser).

## RECOMMENDED: Make Window Fullscreen

For the best demo quality, make your browser window fullscreen before recording:

```python
maximize_window(window_title="Google Chrome")  # Fills screen, keeps title stable
```

This tool:
- macOS: Enters native fullscreen mode (green button)
- Linux: Sets fullscreen state via wmctrl
- Windows: Maximizes the window

**Wait 1-2 seconds after fullscreen** before starting to record (especially on macOS where the animation takes time).
"""

# Container recording flow section
SETUP_GUIDE_CONTAINER_FLOW = """
## Simple Recording Flow

1. browser_navigate(url)     # Opens browser
2. start_recording(window_title="Google Chrome")  # Specify your browser!
3. [perform demo actions]
4. stop_recording()          # Saves video

---

## One-Time Setup (Start of Demo)

Execute these steps IN ORDER before recording any steps:

```
1. NAVIGATE FIRST (creates the browser window)
   browser_navigate(url="https://your-target-site.com")
   # CRITICAL: Browser window only exists AFTER navigation
   # Without this step, list_windows() will find nothing

2. VERIFY WINDOW EXISTS
   list_windows()
   # Expected output includes the browser window title
   # If empty: You forgot step 1 (navigate). Go back.

3. VERIFY CONTENT
   browser_snapshot()
   # Examine: Is correct page showing? Is content visible?
```

IMPORTANT: The browser window does NOT exist until browser_navigate() is called.
If list_windows() returns empty, ensure you navigated to a URL first.

---
"""

# Host recording flow section (includes fullscreen step)
SETUP_GUIDE_HOST_FLOW = """
## Simple Recording Flow

1. browser_navigate(url)     # Opens browser
2. maximize_window(window_title="Google Chrome")    # Fill screen (recommended)
3. start_recording(window_title="Google Chrome")    # Start recording
4. [perform demo actions]
5. stop_recording()          # Saves video

---

## One-Time Setup (Start of Demo)

Execute these steps IN ORDER before recording any steps:

```
1. NAVIGATE FIRST (creates the browser window)
   browser_navigate(url="https://your-target-site.com")
   # CRITICAL: Browser window only exists AFTER navigation
   # Without this step, list_windows() will find nothing

2. VERIFY WINDOW EXISTS
   list_windows()
   # Expected output includes the browser window title
   # If empty: You forgot step 1 (navigate). Go back.

3. MAXIMIZE WINDOW (recommended for best quality)
   maximize_window(window_title="Google Chrome")  # Fills screen, keeps title stable
   # No animation delay needed with maximize (unlike fullscreen)

4. VERIFY CONTENT
   browser_snapshot()
   # Examine: Is correct page showing? Is content visible?
```

IMPORTANT: The browser window does NOT exist until browser_navigate() is called.
If list_windows() returns empty, ensure you navigated to a URL first.

---
"""

# Container-specific recording configuration
SETUP_GUIDE_CONTAINER_CONFIG = """
## Recording Configuration

```python
start_recording(
    window_title="Firefox",           # From list_windows() output
    output_path="stepN_raw.mp4"       # Saved to /app/recordings/
)
```

The tool automatically:
- Captures the Firefox window from Xvfb
- Uses 30fps
- Detects window dimensions
"""

# Host-specific recording configuration
SETUP_GUIDE_HOST_CONFIG = """
## Recording Configuration

```python
start_recording(
    window_title="Google Chrome",     # From list_windows() output (or your browser)
    output_path="stepN_raw.mp4"       # Saved to ~/recordings/
)
```

The tool automatically:
- Captures the browser window using native screen capture
- Uses 30fps
- Detects window dimensions
"""

# Common verification section
SETUP_GUIDE_VERIFICATION = """
---

## Per-Step Verification

Before EACH recording:
```
1. browser_snapshot()              # Capture current state
2. Examine screenshot              # Verify correct content
3. IF wrong content:
   - Navigate/scroll to fix
   - Re-take snapshot
   - Re-verify
4. ONLY record when content verified
```

After EACH recording:
```
1. browser_snapshot()              # Capture end state
2. Examine screenshot              # Verify recording captured intended content
3. IF wrong:
   - Delete recording
   - Re-record step
```

---

## Tools Reference

Recording:
| Tool                   | Purpose                              |
|------------------------|--------------------------------------|
| start_recording        | Begin video capture                  |
| stop_recording         | End capture, save file               |
| recording_status       | Check if recording active            |
| text_to_speech         | Generate audio from text             |
| adjust_video_to_audio  | Sync video speed to audio duration   |
| concatenate_videos     | Join videos into final output        |
| media_info             | Get file duration/resolution         |
"""

# Container-specific window tools section
SETUP_GUIDE_CONTAINER_TOOLS = """
Window:
| Tool          | Purpose                              |
|---------------|--------------------------------------|
| list_windows  | List windows in virtual display      |
| window_tools  | Check tool availability              |
"""

# Host-specific window tools section
SETUP_GUIDE_HOST_TOOLS = """
Window:
| Tool          | Purpose                              |
|---------------|--------------------------------------|
| list_windows  | List windows on your display         |
| window_tools  | Check tool availability              |
"""

# Common browser tools section
SETUP_GUIDE_BROWSER_TOOLS = """
Browser (from Playwright MCP):
| Tool             | Purpose                           |
|------------------|-----------------------------------|
| browser_navigate | Navigate to URL                   |
| browser_snapshot | Capture page state/screenshot     |
| browser_click    | Click element                     |
| browser_type     | Type text                         |
| browser_evaluate | Execute JavaScript                |

---
"""

# Container-specific common issues
SETUP_GUIDE_CONTAINER_ISSUES = """
## Common Issues

| Issue                    | Cause                      | Fix                           |
|--------------------------|----------------------------|-------------------------------|
| list_windows() empty     | No browser navigation yet  | Call browser_navigate(url) FIRST |
| Window not found         | Wrong window_title         | Run list_windows(), use exact pattern |
| Recording empty/black    | Browser not in Xvfb        | Verify with browser_snapshot() |
| Wrong content recorded   | Skipped verification       | Always snapshot before recording |
"""

# Host-specific common issues
SETUP_GUIDE_HOST_ISSUES = """
## Common Issues

| Issue                    | Cause                      | Fix                           |
|--------------------------|----------------------------|-------------------------------|
| list_windows() empty     | No browser navigation yet  | Call browser_navigate(url) FIRST |
| Window not found         | Wrong window_title         | Run list_windows(), use exact pattern |
| Recording empty/black    | Window not visible/minimized | Ensure browser window is visible |
| Permission denied (macOS)| Screen recording not allowed | Grant permission in System Settings > Privacy > Screen Recording |
| Wrong content recorded   | Skipped verification       | Always snapshot before recording |
| Wrong window recorded    | Auto-detect picked wrong app | Specify window_title='Chrome' explicitly |

**TIP**: When recording, always check the "Window:" line in the output to verify
the correct window is being recorded. If using Playwright MCP with Chrome, it
should say "Google Chrome", not "Cursor".
"""

SETUP_GUIDE_FOOTER = """
---

NEXT: Call recording_phase_3() for in-recording actions.
"""


def _build_setup_guide(is_container: bool) -> str:
    """Build the setup guide with mode-appropriate content."""
    if is_container:
        return (
            SETUP_GUIDE_HEADER +
            SETUP_GUIDE_CONTAINER_ENV +
            SETUP_GUIDE_CONTAINER_FLOW +
            SETUP_GUIDE_CONTAINER_CONFIG +
            SETUP_GUIDE_VERIFICATION +
            SETUP_GUIDE_CONTAINER_TOOLS +
            SETUP_GUIDE_BROWSER_TOOLS +
            SETUP_GUIDE_CONTAINER_ISSUES +
            SETUP_GUIDE_FOOTER
        )
    else:
        return (
            SETUP_GUIDE_HEADER +
            SETUP_GUIDE_HOST_ENV +
            SETUP_GUIDE_HOST_FLOW +
            SETUP_GUIDE_HOST_CONFIG +
            SETUP_GUIDE_VERIFICATION +
            SETUP_GUIDE_HOST_TOOLS +
            SETUP_GUIDE_BROWSER_TOOLS +
            SETUP_GUIDE_HOST_ISSUES +
            SETUP_GUIDE_FOOTER
        )


# =============================================================================
# PHASE 3: RECORDING ACTIONS GUIDE
# =============================================================================

RECORDING_GUIDE = """
# Phase 3: Recording Actions

What to do DURING recording for engaging demos. Call after setup_phase_2().
Next phase: editing_phase_4()

---

## REMINDER: Keep Scenes SHORT (10-30 seconds max)

Audio sync adjusts playback speed - long recordings play too fast.
See planning_phase_1() for duration guidelines and scene structure.

---

## Recording Pattern

**ALL actions happen INSIDE the recording:**

```
1. Verify position (snapshot BEFORE recording)
2. START recording
3. WAIT 2s (viewer sees initial state)
4. PERFORM action (scroll, click, type) - THIS IS RECORDED
5. WAIT 2s (viewer absorbs result)
6. STOP recording
7. SYNC with audio before next scene
```

## REMINDER: Actions DURING Recording

**All actions must happen BETWEEN start_recording() and stop_recording().**
See planning_phase_1() for the full WRONG vs CORRECT pattern.

Key rule: If you want viewers to SEE an action, it must happen DURING recording.

---

## Scrolling

Use browser_evaluate for smooth scrolling:

```python
# Scroll by fixed amount (recommended)
browser_evaluate(function='() => { window.scrollBy({ top: 400, behavior: "smooth" }); }')
browser_wait_for(time=2)  # ALWAYS wait after scroll

# Scroll to element
browser_evaluate(function='() => { document.querySelector("#section").scrollIntoView({ behavior: "smooth" }); }')
browser_wait_for(time=2)

# Scroll to top
browser_evaluate(function='() => { window.scrollTo({ top: 0, behavior: "smooth" }); }')
browser_wait_for(time=2)
```

Scroll amounts:
- Small reveal: 200-300px
- Section jump: 400-500px
- Full page: 600-800px

CRITICAL: Always call browser_wait_for(time=2) after scrolling.

---

## Clicking

```python
# Hover then click for visibility
browser_hover(ref="...", element="Submit button")
browser_wait_for(time=1)
browser_click(ref="...", element="Submit button")
browser_wait_for(time=2)  # Wait for result
```

---

## Typing

```python
# Type with slowly=True for character-by-character
browser_type(ref="...", text="hello@example.com", slowly=True)
browser_wait_for(time=1)  # Pause to show completed input
```

---

## Complete Scene Example

```python
# === SCENE 1: Scroll to features ===

browser_snapshot()  # Verify starting position (NOT recorded)

# RECORDING STARTS - all actions now captured
start_recording(output_path="scene1_raw.mp4")
browser_wait_for(time=2)                    # Viewer sees starting state
browser_evaluate(function='() => { window.scrollBy({ top: 400, behavior: "smooth" }); }')
browser_wait_for(time=2)                    # Viewer sees scroll complete
stop_recording()
# RECORDING ENDS

browser_snapshot()  # Verify ending position (NOT recorded)

text_to_speech(
    text="As we scroll down, you can see the main features of our platform...",
    output_path="scene1_audio.mp3"
)

adjust_video_to_audio(
    video_path="scene1_raw.mp4",
    audio_path="scene1_audio.mp3",
    output_path="scene1_final.mp4"
)

# === SCENE 2: Click button and see result ===

browser_snapshot()  # Verify position

# RECORDING STARTS
start_recording(output_path="scene2_raw.mp4")
browser_wait_for(time=2)
browser_hover(ref="...", element="Learn More")  # Hover captured!
browser_wait_for(time=1)
browser_click(ref="...", element="Learn More")  # Click captured!
browser_wait_for(time=3)                         # Result captured!
stop_recording()
# RECORDING ENDS

browser_snapshot()

text_to_speech(
    text="Clicking Learn More opens the detailed view with all specifications...",
    output_path="scene2_audio.mp3"
)

adjust_video_to_audio(
    video_path="scene2_raw.mp4",
    audio_path="scene2_audio.mp3",
    output_path="scene2_final.mp4"
)

# === FINAL: Concatenate all scenes ===
concatenate_videos(
    video_paths=["scene1_final.mp4", "scene2_final.mp4"],
    output_path="demo_final.mp4"
)
```

**Notice:** Every scroll, hover, and click happens BETWEEN start_recording and stop_recording.

---

## Timing Guidelines

| Action               | Wait After |
|----------------------|------------|
| Scroll               | 2-3s       |
| Click                | 2-3s       |
| Type                 | 1-2s       |
| Page navigation      | 3-4s       |
| Animation/transition | 2-3s       |
| Key content display  | 3-5s       |

---

## Mistakes to Avoid

| Problem                  | Fix                                    |
|--------------------------|----------------------------------------|
| **Actions before recording** | **Move actions AFTER start_recording()** |
| Static/boring video      | Do scroll/click/type DURING recording  |
| No pauses between actions| Add browser_wait_for() after each action|
| Rushed content           | Pause 3-5s on key information          |
| Scroll without waiting   | Always wait 2s after scroll            |
| Skipped verification     | Snapshot before and after recording    |

**#1 Mistake:** Performing actions before start_recording() and wondering why 
the video is static. The recording only captures what happens AFTER it starts.

---

## Verification

Always snapshot BEFORE and AFTER each recording to verify content.
See setup_phase_2() for the detailed verification workflow.

---

## Failure Recovery

If recording captures wrong content:
1. STOP - do not continue
2. DELETE the bad recording
3. Navigate to correct content
4. Re-verify with snapshot
5. Re-record entire step

---

NEXT: Call editing_phase_4() for audio sync and final assembly.
"""


# =============================================================================
# PHASE 4: VIDEO ASSEMBLY GUIDE (MODE-AWARE)
# =============================================================================

ASSEMBLY_GUIDE_MAIN = """
# Phase 4: Video Assembly

Post-recording: script writing, audio sync, and final concatenation.
Call after recording_phase_3().

---

## CRITICAL: Process Each Scene Before Recording Next

The workflow is SCENE-BY-SCENE, not batch:

```
CORRECT (process each scene fully):
  Record Scene 1 -> Script 1 -> Audio 1 -> Sync 1
  Record Scene 2 -> Script 2 -> Audio 2 -> Sync 2
  Record Scene 3 -> Script 3 -> Audio 3 -> Sync 3
  Concatenate all

WRONG (batch approach):
  Record Scene 1, 2, 3, 4, 5...
  Write all scripts
  Generate all audio
  Try to sync (FAILS - out of sync!)
```

Why scene-by-scene:
- Audio length controls video speed via adjust_video_to_audio()
- Script is based on what you JUST recorded
- Errors caught immediately, not at the end

---

## Per-Scene Assembly Workflow

```
For EACH scene (do not skip ahead):
1. RECORD      -> sceneN_raw.mp4 (10-30 seconds)
2. SCREENSHOT  -> Capture end state
3. SCRIPT      -> Write 15-25 second narration based on screenshots
4. AUDIO       -> text_to_speech() -> sceneN_audio.mp3
5. SYNC        -> adjust_video_to_audio() -> sceneN_final.mp4
6. VERIFY      -> media_info() - confirm video matches audio duration
7. NEXT        -> Only NOW record scene N+1
```

Do NOT record multiple scenes before syncing. Sync each scene immediately.

---

## Script Writing

Write scripts AFTER recording, based on screenshots:

```python
# You have:
# - Pre-recording screenshot (starting state)
# - stepN_raw.mp4 (the recording)
# - Post-recording screenshot (ending state)

# Script describes the visual journey:
script = (
    "Here we see [pre-screenshot content]. "
    "Now we [action performed]. "
    "As you can see, [post-screenshot content]."
)

text_to_speech(text=script, output_path="stepN_audio.mp3")
```

---

## Audio-Video Sync

adjust_video_to_audio() speeds up or slows down video to match audio duration.
It NEVER cuts/trims - all visual content is preserved.

```python
adjust_video_to_audio(
    video_path="stepN_raw.mp4",
    audio_path="stepN_audio.mp3",
    output_path="stepN_final.mp4"
)

# Verify
media_info(file_path="stepN_final.mp4")
```

---

## Final Concatenation

After all steps are synced:

```python
concatenate_videos(
    video_paths=[
        "step1_final.mp4",
        "step2_final.mp4",
        "step3_final.mp4"
    ],
    output_path="demo_final.mp4"
)

# Verify final video
media_info(file_path="demo_final.mp4")
```

---
"""

# Container-specific file structure
ASSEMBLY_GUIDE_CONTAINER_FILES = """
## File Structure

```
/app/recordings/
  step1_raw.mp4
  step1_audio.mp3
  step1_final.mp4
  step2_raw.mp4
  step2_audio.mp3
  step2_final.mp4
  ...
  demo_final.mp4
```
"""

# Host-specific file structure
ASSEMBLY_GUIDE_HOST_FILES = """
## File Structure

```
~/recordings/
  step1_raw.mp4
  step1_audio.mp3
  step1_final.mp4
  step2_raw.mp4
  step2_audio.mp3
  step2_final.mp4
  ...
  demo_final.mp4
```

Note: You can customize the recordings directory by setting the RECORDINGS_DIR environment variable.
"""

ASSEMBLY_GUIDE_FOOTER = """
---

## Quality Checklist

Before delivery:
- Audio synced with visuals
- All content readable
- No glitches or artifacts
- Smooth step transitions
- Correct total duration

---

## Common Issues

| Issue                      | Fix                                          |
|----------------------------|----------------------------------------------|
| **Audio/video out of sync**| **Scene too long! Keep recordings under 30s**|
| Video plays too fast       | Recording was too long for the audio         |
| Video plays too slow       | Recording was too short (ok, adds pause)     |
| Window not found           | Run list_windows(), use correct pattern      |
| Wrong content recorded     | Verify with snapshot before recording        |
| Wrong window recorded      | Check "Window:" output, use window_title param |

**The #1 cause of sync problems is recording too long.** Split into shorter scenes.

**IMPORTANT**: Always verify the "Window:" line when recording starts. If it shows
the wrong app (e.g., "Cursor" instead of "Google Chrome"), stop immediately and
restart with: `start_recording(window_title="Google Chrome")`

---

## Error Recovery

If step N fails:
1. Keep completed steps (1 to N-1)
2. Delete failed step N files
3. Re-record step N
4. Continue with N+1

---

## Review Phases

- planning_phase_1() - Demo structure
- setup_phase_2() - Browser setup
- recording_phase_3() - Recording actions
- editing_phase_4() - This guide
"""


def _build_assembly_guide(is_container: bool) -> str:
    """Build the assembly guide with mode-appropriate content."""
    if is_container:
        return (
            ASSEMBLY_GUIDE_MAIN +
            ASSEMBLY_GUIDE_CONTAINER_FILES +
            ASSEMBLY_GUIDE_FOOTER
        )
    else:
        return (
            ASSEMBLY_GUIDE_MAIN +
            ASSEMBLY_GUIDE_HOST_FILES +
            ASSEMBLY_GUIDE_FOOTER
        )


# =============================================================================
# DEPRECATED: Original Protocol (for backwards compatibility)
# =============================================================================

DEPRECATED_NOTICE = """
# DEPRECATED: get_demo_protocol

This tool returns too much information at once (800+ lines), which can overwhelm agents.

**Use the phase-based tools instead:**

1. **`planning_phase_1()`** (Phase 1)
   - How to structure and script your demo
   - Timing guidelines and templates
   - Call this FIRST

2. **`setup_phase_2()`** (Phase 2)
   - Pre-recording checklist
   - Window management and viewport optimization
   - Screen verification workflow

3. **`recording_phase_3()`** (Phase 3)
   - What to do DURING recording
   - Interactive actions (scrolling, clicking, typing)
   - CRITICAL for engaging, non-boring demos

4. **`editing_phase_4()`** (Phase 4)
   - Audio synchronization
   - Video concatenation
   - Quality checks and troubleshooting

**Workflow:**
```
planning_phase_1() -> setup_phase_2() -> recording_phase_3() -> editing_phase_4()
```

Each guide is focused (~200 lines) and provides clear next steps.
"""


# =============================================================================
# Public Functions
# =============================================================================

def get_planning_guide() -> str:
    """Phase 1: Return the demo planning guide.
    
    This guide is mode-independent (same content for container and host).
    """
    return PLANNING_GUIDE


def get_setup_guide() -> str:
    """Phase 2: Return the recording setup guide.
    
    This guide is MODE-AWARE:
    - Container mode: Shows Xvfb, Firefox, /app/recordings/ content
    - Host mode: Shows platform-native capture, ~/recordings/ content
    """
    return _build_setup_guide(is_container_environment())


def get_recording_guide() -> str:
    """Phase 3: Return the recording actions guide.
    
    This guide is mode-independent (same content for container and host).
    """
    return RECORDING_GUIDE


def get_assembly_guide() -> str:
    """Phase 4: Return the video assembly guide.
    
    This guide is MODE-AWARE:
    - Container mode: Shows /app/recordings/ file structure
    - Host mode: Shows ~/recordings/ file structure
    """
    return _build_assembly_guide(is_container_environment())


def get_protocol() -> str:
    """DEPRECATED: Return the deprecation notice pointing to new tools."""
    return DEPRECATED_NOTICE
