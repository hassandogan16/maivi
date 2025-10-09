# Maivi UI Improvements Plan

## Goals
1. Make settings apply without restart (hot reload)
2. Fix UI theme - zen, minimal, clean
3. Add microphone selection
4. Follow system theme (light/dark)

## Changes Needed

### 1. Settings Hot Reload (`settings_dialog.py`)
- Remove "requires restart" message
- Add signals for settings changes
- Emit signals when settings change
- Main app listens to signals and applies changes immediately

### 2. UI Theme Redesign (`qt_gui.py` - TranscriptionOverlay)
**Current Problems:**
- Dark background (#1e1e1e) with bright green text (#00ff00) - harsh
- Shadows not visible on dark background
- Border color too dark (#444444)

**New Zen Design:**
- Follow system theme (macOS light/dark mode)
- Clean, minimal styling
- Soft colors
- No harsh contrasts
- Proper spacing and typography

**Light Theme:**
- Background: #FFFFFF or #F5F5F5 (soft white/gray)
- Text: #333333 (dark gray, not black)
- Accent (recording): #FF6B6B (soft red)
- Border: #E0E0E0 (light gray)

**Dark Theme:**
- Background: #2D2D2D (softer than #1e1e1e)
- Text: #E0E0E0 (soft white, not bright)
- Accent (recording): #FF6B6B (soft red)
- Border: #404040 (visible but subtle)

### 3. Microphone Selection (`settings_dialog.py`)
- Add `QComboBox` for microphone selection
- List available audio input devices using `sounddevice.query_devices()`
- Save selected device to config
- Apply immediately (hot reload)

### 4. Config Updates (`config.py`)
- Add `audio_device` setting (stores device index or name)
- Add `theme` setting (auto/light/dark)

### 5. Audio Device Support (`core/streaming_recorder.py`)
- Accept `device` parameter
- Pass to sounddevice

## Implementation Order
1. Add microphone selection to settings dialog
2. Redesign overlay UI with zen theme
3. Implement settings hot reload system
4. Add system theme detection
5. Test all changes together
