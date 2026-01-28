"""
Demo Recording Protocol

This module contains the comprehensive protocol document that agents should read
before creating any demo recording. It covers best practices, step-by-step workflows,
and troubleshooting guidance.

Use the get_demo_protocol tool to retrieve this document.
"""

DEMO_RECORDING_PROTOCOL = """
# Demo Recording Protocol

This document describes the complete workflow for creating professional demo recordings
with synchronized voiceover narration. Follow this protocol to ensure consistent,
high-quality demos.

---

## MANDATORY RULES (NOT SUGGESTIONS)

These are **RULES** that MUST be followed. Failure to follow them will result in
audio-video desync and poor quality demos.

### RULE 1: ONE STEP = ONE VIDEO + ONE AUDIO

Each demo step MUST have:
- **Exactly 1 video file** (recording of that step's actions)
- **Exactly 1 audio file** (TTS voiceover for that step)

WRONG: Recording the entire demo as one video, then adding voiceover
RIGHT: Recording each step separately, syncing each step, then concatenating

### RULE 2: SPEED ADJUST, NEVER CUT

To sync video with audio:
- **SPEED UP** the video if it's longer than audio
- **SLOW DOWN** the video if it's shorter than audio
- **NEVER trim/cut** the video - ALL visual content must be preserved

Use `adjust_video_to_audio_length` which automatically speeds up or slows down.

### RULE 3: USE ONLY MCP TOOLS

**DO NOT** use manual FFmpeg or terminal commands.
**ALWAYS** use the MCP tools below.

This ensures:
- Consistent behavior across machines
- Reusable workflows for other users
- Proper error handling
- Portability and easy installation

### RULE 4: FULL WALKTHROUGH EACH STEP

During recording, you MUST show the complete action:
- Scroll through content slowly
- Show the action being performed
- Show the result/output
- Pause briefly on important information

WRONG: Start recording -> instantly run cell -> stop recording
RIGHT: Start recording -> scroll to cell -> run cell -> wait for output -> scroll to show output -> pause -> stop recording

### RULE 5: VISUAL MUST MATCH NARRATION

**What the audio says = What the screen shows**

Before recording each step:
1. READ the narration text
2. IDENTIFY what visual content the narration describes
3. PLAN the screen actions to show that exact content
4. CENTER the most relevant content in the viewport

During recording:
- When audio says "let's look at the results" -> results must be visible
- When audio says "notice the vector search" -> vector search output must be centered
- When audio mentions specific text/code -> that text/code must be on screen

WRONG: Audio describes search results while screen shows title
RIGHT: Audio describes search results while screen shows and highlights search results

### RULE 6: FOCUS THE RELEVANT CONTENT

The most important content must be:
- **Centered** in the viewport (not at edges)
- **Fully visible** (not cut off or partially scrolled)
- **Given time** to be seen (pause 2-3 seconds on key content)

Planning template for each step:
```
Narration: "[What the audio will say]"
Visual:    "[What must be visible on screen]"
Focus:     "[What should be centered/highlighted]"
```

### RULE 7: VERIFY POSITION BEFORE AND AFTER RECORDING

**Before starting EVERY step recording:**
1. **SCROLL** to the target section using `scrollIntoView()` or keyboard navigation
2. **TAKE A SCREENSHOT** to verify the correct content is visible
3. **COMPARE** the screenshot to your planned visual - is the right content centered?
4. **ONLY THEN** start recording

**After scrolling DURING recording:**
1. **ASSUME** the scroll may not have worked (browser quirks, timing issues)
2. **USE** reliable scroll methods: `element.scrollIntoView()` or Page Down key
3. **WAIT** 1-2 seconds after scroll for smooth animation to complete
4. **IF** scroll failed (detected by next screenshot), RE-RECORD the entire step

WRONG: Start recording immediately without verifying position
RIGHT: Screenshot -> verify -> start recording -> action -> screenshot -> verify -> stop

### RULE 8: IN-RECORDING ACTIONS ARE MANDATORY

Most demo steps require ACTIONS during recording, not just static viewing:
- **Scrolling** to reveal code, output, or results
- **Typing** to show how to use features
- **Clicking** to demonstrate interactions
- **Waiting** for operations to complete

**These actions ARE the demo** - without them, viewers see nothing happening.

#### Standard In-Recording Action Pattern:

```
1. START recording
2. WAIT 2-3 seconds (let viewer see initial state)
3. PERFORM action (scroll/type/click)
4. WAIT for result (animation complete, output visible)
5. FOCUS result (center it in viewport)
6. PAUSE 3-5 seconds (let viewer read the result)
7. (Optional) SCROLL to show more detail
8. STOP recording
```

#### Scrolling During Recording - BEST PRACTICES:

Use these scroll methods (in order of reliability):

1. **JavaScript `scrollIntoView`** (MOST RELIABLE):
   ```javascript
   element.scrollIntoView({ behavior: 'smooth', block: 'start' });
   ```

2. **Keyboard Page Down** (RELIABLE):
   - Press `PageDown` key for large jumps
   - Press `ArrowDown` for fine control

3. **JavaScript `scrollBy`** (LESS RELIABLE in some contexts):
   ```javascript
   window.scrollBy({ top: 300, behavior: 'smooth' });
   ```

**After each scroll, WAIT at least 2 seconds** for the smooth scroll animation.

#### Typing During Recording:

For demos showing typing:
1. Use `browser_type` with `slowly: true` to show character-by-character
2. WAIT after typing for any autocomplete/feedback
3. Show the result of the typed content

#### Clicking During Recording:

For demos showing clicks:
1. HOVER over the element first (visual cue)
2. WAIT 1 second (viewer sees what will be clicked)
3. CLICK the element
4. WAIT for result

---

## MCP Tools Reference

### Recording Tools

| Tool | Purpose |
|------|---------|
| `text_to_speech` | Generate voiceover audio (OpenAI/Edge TTS) |
| `start_recording` | Start screen recording |
| `stop_recording` | Stop recording and save file |
| `recording_status` | Check if recording is in progress |
| `adjust_video_to_audio_length` | **KEY TOOL**: Speed up/slow down video to match audio (preserves ALL frames) |
| `concatenate_videos` | Join step videos into final demo |
| `get_media_info` | Get duration/resolution info |
| `get_audio_duration` | Get exact audio duration |
| `get_demo_protocol` | Retrieve this document |

### Browser Tools (from cursor-browser-extension MCP)

These tools control the browser and work with ANY website/web app:

| Tool | Purpose |
|------|---------|
| `browser_navigate` | Go to any URL |
| `browser_snapshot` | Get page state and element refs |
| `browser_take_screenshot` | **VERIFY POSITION** - confirm correct content visible |
| `browser_evaluate` | Execute JS (scrollIntoView, custom actions) |
| `browser_press_key` | Keyboard input (PageDown, Enter, shortcuts) |
| `browser_wait_for` | Wait N seconds or for text to appear |
| `browser_click` | Click elements by ref |
| `browser_type` | Type text (use `slowly: true` for visible typing) |
| `browser_hover` | Hover over elements |
| `browser_resize` | Set browser dimensions (1920x1080 recommended) |
| `browser_tabs` | Manage multiple tabs |

### Verification Workflow (works for ANY website)

```
1. browser_navigate -> go to target URL
2. browser_resize -> set to 1920x1080
3. browser_snapshot -> get element references
4. browser_evaluate -> scrollIntoView() to target element
5. browser_wait_for -> 2 seconds for animation
6. browser_take_screenshot -> verify correct content visible
7. (IF wrong) -> repeat scroll and verify
8. (IF correct) -> start_recording
```

---

## Demo Types - Universal Approach

This protocol works for ANY type of demo:

### Web Application Demos
```
Examples: Google Search, Gmail, GitHub, any SaaS app
Actions: Navigate, search, click, type, show results
```

### Jupyter Notebook Demos
```
Examples: Data science tutorials, ML demos
Actions: Execute cells, scroll to show code/output
```

### Documentation/Tutorial Demos
```
Examples: README walkthroughs, API docs
Actions: Navigate sections, highlight code blocks
```

### Multi-Page Workflow Demos
```
Examples: E-commerce checkout, user registration
Actions: Fill forms, navigate between pages, show confirmations
```

### The Same Tools Work for ALL Types

The getademo MCP provides: recording, audio, video editing
The browser MCP provides: navigation, interaction, verification

**Together they can demo ANYTHING in a browser.**

---

## Phase 1: Preparation

### 1.1 Pre-Recording Checklist

Before starting any demo:

- [ ] **Screen Recording Permission**: Verify macOS System Settings -> Privacy & Security -> Screen Recording has your terminal/Cursor enabled
- [ ] **Screen Resolution**: Set to 1920x1080 (Full HD) for best compatibility
- [ ] **Browser Setup**:
  - Use a clean browser profile or incognito mode
  - Hide bookmarks bar (Cmd+Shift+B in Chrome)
  - Hide extensions toolbar
  - Set browser to full-screen mode (Cmd+Shift+F or F11)
  - Close unnecessary tabs
- [ ] **Desktop Cleanup**: Hide desktop icons, close unrelated applications
- [ ] **Do Not Disturb**: Enable to prevent notification interruptions
- [ ] **Output Directory**: Create a dedicated folder for the demo recordings

### 1.2 Demo Structure Planning

Before recording, create a structured plan:

```
Demo: [Title]
├── Step 1: [Description] - [Expected duration: Xs]
├── Step 2: [Description] - [Expected duration: Xs]
├── ...
└── Step N: [Description] - [Expected duration: Xs]

Total Expected Duration: X minutes
```

### 1.3 Script Writing Guidelines

Write narration scripts that are:

- **Conversational**: Write as if explaining to a colleague
- **Concise**: Aim for 15-30 seconds per step
- **Technical but accessible**: Define terms when first used
- **Action-oriented**: Describe what's happening on screen
- **Paced for viewing**: Allow time for viewers to see the results

Example script structure:
```
[Step N: Title]
"Now we [action being performed].
Notice how [key observation].
This is important because [explanation].
The result shows [outcome]."
```

---

## Phase 2: Step-by-Step Recording

### 2.1 Per-Step Workflow

For EACH step in your demo:

```
PLANNING PHASE:
1. WRITE the narration text for this step
2. PLAN the visual content:
   - What must be visible when each phrase is spoken?
   - What should be centered/focused?
   - What IN-RECORDING ACTIONS are needed? (scroll, type, click)
3. GENERATE TTS audio using text_to_speech tool
4. NOTE the audio duration (returned by tool)

PRE-RECORDING VERIFICATION:
5. SCROLL to starting position using reliable method (scrollIntoView or PageDown)
6. TAKE SCREENSHOT to verify correct position
7. CHECK: Is the right content visible and centered?
   - If NO -> scroll again and re-verify
   - If YES -> proceed to recording

RECORDING PHASE:
8. START screen recording using start_recording tool
9. WAIT 2-3 seconds (viewer sees initial state)
10. EXECUTE IN-RECORDING ACTIONS matching the narration:
    - SCROLL to reveal content as audio describes it
    - WAIT after each scroll (2 seconds minimum)
    - PAUSE on key information (3-5 seconds)
    - SHOW the results/output
11. WAIT 2-3 seconds at end (viewer absorbs final state)
12. STOP recording using stop_recording tool

POST-RECORDING:
13. ADJUST video speed to match audio using adjust_video_to_audio_length tool
    (This speeds up or slows down - NEVER cuts content)
14. VERIFY: The final duration should match audio duration
15. PROCEED to next step
```

**IMPORTANT**: If scrolling during recording fails or content isn't showing correctly,
DELETE the raw recording and RE-RECORD the entire step. Do not try to fix partial steps.

### 2.2 Recording Best Practices

During recording:

- **Move slowly and deliberately** - viewers need time to follow
- **Pause after each action** - let results fully render (2-3 seconds)
- **Keep cursor movements smooth** - avoid jerky motions
- **Center important content** - position key elements in the middle of screen
- **Avoid excessive scrolling** - plan content to fit in viewport when possible

### 2.3 Timing Guidelines

| Content Type | Recommended Duration |
|--------------|---------------------|
| Title/intro | 5-10 seconds |
| Simple action | 10-20 seconds |
| Code execution | 15-30 seconds |
| Complex output | 20-40 seconds |
| Summary/conclusion | 10-15 seconds |

---

## Phase 3: Error Recovery

### 3.1 If a Step Recording Fails

When step N fails or has issues:

1. **KEEP** all completed steps (1 to N-1)
2. **DELETE** the failed step N segment
3. **RE-RECORD** step N from scratch
4. **CONTINUE** with step N+1 onwards

### 3.2 If Re-recording Affects Later Steps

If re-recording step N changes timing or flow that affects later steps:

1. **KEEP** steps 1 to N-1
2. **DISCARD** steps N onwards
3. **RE-RECORD** from step N to the end

### 3.3 Common Issues and Fixes

| Issue | Solution |
|-------|----------|
| Recording permission denied | System Settings -> Privacy -> Screen Recording, restart Cursor |
| Audio too fast/slow | Adjust script text length, regenerate TTS |
| Video too short for audio | Tool will SLOW DOWN video (no frame freeze) |
| Video too long for audio | Tool will SPEED UP video (no cutting) |
| Browser not maximized | Use browser_resize(1920, 1080) or F11 |
| Cursor not visible | Ensure screen_index=1 in start_recording |
| **Scroll not working** | Use `scrollIntoView()` instead of `scrollBy()`, or use PageDown key |
| **Page at wrong position** | Take screenshot to verify BEFORE recording, scroll again if needed |
| **Content not visible after scroll** | Wait 2+ seconds for smooth scroll animation to complete |
| **Jupyter notebook scroll issues** | Use `scrollIntoView()` on heading elements, not `window.scrollBy()` |

---

## Phase 4: Final Assembly

### 4.1 Concatenation

After all steps are recorded and adjusted:

```
1. LIST all step segments in order: step_01.mp4, step_02.mp4, ...
2. USE concatenate_videos tool to join them
3. VERIFY final video plays correctly
```

### 4.2 Quality Checks

Before delivery, verify:

- [ ] Audio and video are synchronized throughout
- [ ] All content is visible and readable
- [ ] No recording artifacts or glitches
- [ ] Transitions between steps are smooth
- [ ] Total duration matches expectations

### 4.3 File Organization

Recommended folder structure:
```
demo_recordings/
├── [demo_name]/
│   ├── steps/
│   │   ├── step_01_raw.mp4      # Raw recording
│   │   ├── step_01_audio.mp3    # TTS audio
│   │   ├── step_01_final.mp4    # Adjusted with audio
│   │   ├── step_02_raw.mp4
│   │   └── ...
│   ├── scripts/
│   │   └── voiceover_script.md
│   └── final/
│       └── [demo_name]_final.mp4
```

---

## Quick Start Template

```
# Demo: [Title]

## Step 1: [Name]

Narration: "[Narration text - what audio will say]"

Pre-recording:
  - Scroll to: [element/heading to find]
  - Verify shows: [what must be visible]
  - Screenshot: (take one to confirm)

In-recording actions:
  1. [0-2s] WAIT - initial view
  2. [2-5s] SCROLL to [target] - reveal content
  3. [5-10s] WAIT - viewer reads
  4. [10-12s] SCROLL to [output] - show results
  5. [12-15s] WAIT - final pause

Expected duration: ~Xs audio

## Step 2: [Name]

Narration: "[Narration text]"

Pre-recording:
  - Scroll to: [element]
  - Verify shows: [content]
  - Screenshot:

In-recording actions:
  1. [0-2s] WAIT
  2. [2-Xs] [Actions...]

Expected duration: ~Xs

[Continue for all steps...]
```

---

## Tips for Professional Results

1. **Voice Selection**: Use "onyx" for authoritative tone, "nova" for friendly tone
2. **Pacing**: Add brief pauses in scripts using "..." for natural rhythm
3. **Emphasis**: Important terms can be emphasized with slightly slower speech
4. **Consistency**: Use the same voice and tone throughout the demo
5. **Accessibility**: Speak clearly, avoid jargon without explanation
6. **Testing**: Always preview the final video before delivery

---

Remember: A good demo tells a story. Each step should build on the previous one,
leading the viewer through the narrative naturally. The voiceover guides their
attention while the visuals provide proof and context.

**The same MCP tools work for ANY website or web application.**
"""


def get_protocol() -> str:
    """Return the demo recording protocol document."""
    return DEMO_RECORDING_PROTOCOL


