"""
Qt-based STT Server with system tray and overlay window.
Cross-platform: Windows, macOS, Linux (proper threading support)
"""
import os
import sys
import time
import threading
from pathlib import Path

from PySide6.QtWidgets import QApplication, QWidget, QLabel, QHBoxLayout, QSystemTrayIcon, QMenu
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QThread
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QFontDatabase

import nemo.collections.asr as nemo_asr
import pyperclip
import soundfile as sf
from pynput import keyboard
from pynput.keyboard import Key, Controller

from maivi.core.streaming_recorder import StreamingRecorder
from maivi.core.chunk_merger import SimpleChunkMerger
from maivi.utils.macos_permissions import (
    ensure_accessibility_permissions,
    open_system_settings_privacy,
)
from maivi.config import Config
from maivi.gui.settings_dialog import SettingsDialog
from maivi.gui.recordings_dialog import RecordingsDialog
from maivi import __version__

# Cross-platform notifications
import platform
NOTIFICATIONS_AVAILABLE = False
notification = None


def detect_system_theme():
    """Detect system theme (light/dark) on macOS, returns 'light' or 'dark'."""
    if platform.system() == 'Darwin':
        try:
            import subprocess
            result = subprocess.run(
                ['defaults', 'read', '-g', 'AppleInterfaceStyle'],
                capture_output=True,
                text=True,
                check=False
            )
            # If the command succeeds and returns "Dark", system is in dark mode
            if result.returncode == 0 and 'Dark' in result.stdout:
                return 'dark'
            else:
                return 'light'
        except Exception:
            return 'light'  # Default to light if detection fails
    # For other platforms, default to light (can be extended later)
    return 'light'

# Try to use macOS native notifications first
if platform.system() == 'Darwin':
    try:
        import subprocess
        def _macos_notify(title, message, timeout=10):
            """Use macOS native osascript for notifications"""
            script = f'display notification "{message}" with title "{title}"'
            subprocess.run(['osascript', '-e', script], check=False, capture_output=True)

        class MacOSNotification:
            @staticmethod
            def notify(title="", message="", timeout=10):
                _macos_notify(title, message, timeout)

        notification = MacOSNotification()
        NOTIFICATIONS_AVAILABLE = True
    except Exception:
        pass

# Fall back to plyer for other platforms
if not NOTIFICATIONS_AVAILABLE:
    try:
        from plyer import notification
        NOTIFICATIONS_AVAILABLE = True
    except ImportError:
        NOTIFICATIONS_AVAILABLE = False


class TranscriptionSignals(QObject):
    """Signals for thread-safe GUI updates."""
    update_text = Signal(str, int)  # text, word_count
    set_recording = Signal(bool)


class TranscriptionOverlay(QWidget):
    """Small overlay window showing scrolling transcription near taskbar."""

    def __init__(self, width=400, height=60, hotkey="alt+q", theme="auto"):
        super().__init__()
        self.width = width
        self.height = height
        self.recording = False
        self.hotkey = hotkey
        self.theme = theme

        # Setup window
        self.setWindowTitle("STT Live")
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool  # Don't show in taskbar
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        # Apply zen theme
        self._apply_theme()

        # Layout
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        # Status indicator
        self.status_label = QLabel("○")
        self.status_label.setFont(QFont('Arial', 14, QFont.Bold))
        layout.addWidget(self.status_label)

        # Text display
        self.text_label = QLabel(f"Ready - Press {self.hotkey.upper()} to record")
        fixed_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        fixed_font.setPointSize(10)
        self.text_label.setFont(fixed_font)
        self.text_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self.text_label, stretch=1)

        # Word count
        self.count_label = QLabel("")
        self.count_label.setFont(QFont('Arial', 9))
        layout.addWidget(self.count_label)

        self.setLayout(layout)

        # Position at bottom-right
        self.resize(self.width, self.height)
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - self.width - 20
        y = screen.height() - self.height - 60  # Above taskbar
        self.move(x, y)

    def _apply_theme(self):
        """Apply zen theme based on theme setting (auto/light/dark)."""
        # Determine actual theme to use
        if self.theme == "auto":
            actual_theme = detect_system_theme()
        else:
            actual_theme = self.theme

        # Zen theme colors
        if actual_theme == "dark":
            # Dark theme - softer colors
            self.bg_color = '#2D2D2D'
            self.text_color = '#E0E0E0'
            self.accent_color = '#FF6B6B'
            self.border_color = '#404040'
            self.status_inactive_color = '#666666'
            self.count_color = '#999999'
        else:
            # Light theme - clean and minimal
            self.bg_color = '#FFFFFF'
            self.text_color = '#333333'
            self.accent_color = '#FF6B6B'
            self.border_color = '#E0E0E0'
            self.status_inactive_color = '#CCCCCC'
            self.count_color = '#777777'

        # Apply stylesheet
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {self.bg_color};
                border: 1px solid {self.border_color};
                border-radius: 8px;
            }}
            QLabel {{
                color: {self.text_color};
                background-color: transparent;
                border: none;
            }}
        """)

        # Update status label color if already initialized
        if hasattr(self, 'status_label'):
            if self.recording:
                self.status_label.setStyleSheet(f"color: {self.accent_color};")
            else:
                self.status_label.setStyleSheet(f"color: {self.status_inactive_color};")

        # Update count label color if already initialized
        if hasattr(self, 'count_label'):
            self.count_label.setStyleSheet(f"color: {self.count_color};")

    def set_theme(self, theme):
        """Update theme dynamically."""
        self.theme = theme
        self._apply_theme()

    def set_recording(self, is_recording):
        """Update recording indicator."""
        self.recording = is_recording
        if is_recording:
            self.status_label.setText("●")
            self.status_label.setStyleSheet(f"color: {self.accent_color};")
            self.text_label.setText("🎤 Listening...")
        else:
            self.status_label.setText("○")
            self.status_label.setStyleSheet(f"color: {self.status_inactive_color};")

    def update_text(self, text, word_count=0):
        """Update scrolling text (last 50 chars)."""
        display_text = text[-50:] if len(text) > 50 else text
        self.text_label.setText(display_text or f"Ready - Press {self.hotkey.upper()} to record")
        if word_count > 0:
            self.count_label.setText(f"{word_count}w")
        else:
            self.count_label.setText("")


class QtSTTServer(QObject):
    """Qt-based STT server with system tray."""

    def __init__(
        self,
        auto_paste=False,
        window_seconds=7.0,  # Chunk size (context window)
        slide_seconds=3.0,   # Slide interval (4s overlap for merging)
        start_delay_seconds=2.0,
        speed=1.0,
        toggle_mode=True,
        keep_recordings=3,  # Keep last N recordings
        config=None,  # Config object
    ):
        super().__init__()

        self.print_lock = threading.Lock()

        # Load or create config
        self.config = config if config is not None else Config()

        # Use passed parameters if they differ from defaults, otherwise use config
        # This allows CLI args to override config
        self.auto_paste = auto_paste if auto_paste != False else self.config.get("auto_paste", auto_paste)
        self.speed = speed if speed != 1.0 else self.config.get("speed", speed)
        self.toggle_mode = toggle_mode if toggle_mode != True else self.config.get("toggle_mode", toggle_mode)
        self.keep_recordings = keep_recordings if keep_recordings != 3 else self.config.get("keep_recordings", keep_recordings)
        self.window_seconds = window_seconds if window_seconds != 7.0 else self.config.get("window_seconds", window_seconds)
        self.slide_seconds = slide_seconds if slide_seconds != 3.0 else self.config.get("slide_seconds", slide_seconds)
        self.clear_clipboard_after_paste = self.config.get("clear_clipboard_after_paste", False)
        self.start_delay_seconds = start_delay_seconds if start_delay_seconds != 2.0 else self.config.get("start_delay_seconds", start_delay_seconds)

        # Parse hotkey from config
        self.hotkey = self.config.get("hotkey", "alt+q")
        self.hotkey_parts = self._parse_hotkey(self.hotkey)

        # Get theme and audio device from config
        self.theme = self.config.get("theme", "auto")
        self.audio_device = self.config.get("audio_device", None)

        # Model and recorder
        self.model = None
        self.recorder = StreamingRecorder(
            window_seconds=self.window_seconds,
            slide_seconds=self.slide_seconds,
            start_delay_seconds=self.start_delay_seconds,
            speed=self.speed,
            keep_recordings=self.keep_recordings,
            device=self.audio_device,
        )
        self.keyboard_controller = Controller()
        self.is_shutting_down = False

        # State
        self.current_keys = set()
        self.hotkey_pressed = False
        self.is_recording = False
        self.chunk_counter = 0
        self.chunk_merger = SimpleChunkMerger()
        self.is_transcribing = False
        self.transcription_thread = None

        # GUI components
        self.app = None
        self.overlay = None
        self.tray_icon = None

        # Signals for thread-safe updates
        self.signals = TranscriptionSignals()
        self.signals.update_text.connect(self._update_text_slot)
        self.signals.set_recording.connect(self._set_recording_slot)

    def _print(self, message="", *, end="\n", flush=True):
        """Thread-safe printing helper for coordinated console output."""
        with self.print_lock:
            print(message, end=end, flush=flush)

    def _parse_hotkey(self, hotkey_str):
        """Parse hotkey string into component parts."""
        parts = hotkey_str.lower().split("+")
        return {
            "modifiers": set(p for p in parts if p in ["ctrl", "alt", "shift", "meta"]),
            "keys": [p for p in parts if p not in ["ctrl", "alt", "shift", "meta"]]
        }

    def _check_hotkey_pressed(self):
        """Check if the configured hotkey combination is currently pressed."""
        # Check modifiers
        modifiers_pressed = set()
        if Key.ctrl_l in self.current_keys or Key.ctrl in self.current_keys or Key.ctrl_r in self.current_keys:
            modifiers_pressed.add("ctrl")
        if Key.alt_l in self.current_keys or Key.alt in self.current_keys or Key.alt_r in self.current_keys:
            modifiers_pressed.add("alt")
        if Key.shift_l in self.current_keys or Key.shift in self.current_keys or Key.shift_r in self.current_keys:
            modifiers_pressed.add("shift")
        if hasattr(Key, 'cmd') and (Key.cmd in self.current_keys or Key.cmd_l in self.current_keys or Key.cmd_r in self.current_keys):
            modifiers_pressed.add("meta")

        # Check if required modifiers match
        if modifiers_pressed != self.hotkey_parts["modifiers"]:
            return False

        # Check keys
        for required_key in self.hotkey_parts["keys"]:
            key_found = False
            try:
                # Check regular character keys
                if keyboard.KeyCode.from_char(required_key) in self.current_keys:
                    key_found = True
                # On macOS, some key combinations produce special characters
                # For example, Option+Q produces 'œ'
                if required_key == 'q' and keyboard.KeyCode.from_char('œ') in self.current_keys:
                    key_found = True
            except:
                pass

            # Check special keys
            special_keys = {
                'space': Key.space,
                'return': Key.enter,
                'enter': Key.enter,
                'tab': Key.tab,
                'backspace': Key.backspace,
                'delete': Key.delete,
                'home': Key.home,
                'end': Key.end,
                'pageup': Key.page_up,
                'pagedown': Key.page_down,
                'up': Key.up,
                'down': Key.down,
                'left': Key.left,
                'right': Key.right,
            }

            # Add insert key only if it exists (not available on macOS)
            if hasattr(Key, 'insert'):
                special_keys['insert'] = Key.insert

            # F-keys
            for i in range(1, 13):
                special_keys[f'f{i}'] = getattr(Key, f'f{i}', None)

            if required_key in special_keys and special_keys[required_key] in self.current_keys:
                key_found = True

            if not key_found:
                return False

        return True

    def _update_text_slot(self, text, word_count):
        """Qt slot for updating text (runs in main thread)."""
        if self.overlay:
            self.overlay.update_text(text, word_count)

    def _set_recording_slot(self, is_recording):
        """Qt slot for updating recording state (runs in main thread)."""
        if self.overlay:
            self.overlay.set_recording(is_recording)

    def load_model(self):
        """Load STT model in background."""
        import logging

        # Reduce NeMo logging verbosity
        nemo_logger = logging.getLogger('nemo_logger')
        nemo_logger.setLevel(logging.ERROR)

        # Tips to display while loading
        tips = [
            f"💡 Press {self.hotkey.upper()} to start recording, press again to stop",
            "💡 Your transcription is automatically copied to clipboard",
            "💡 Press Esc to exit the application at any time",
            "💡 The overlay window shows real-time transcription progress",
            "💡 Audio is processed in 7-second chunks with 4-second overlap",
            "💡 Overlap merging ensures no words are cut mid-syllable",
            "💡 First run downloads ~600MB model, subsequent runs are faster",
            "💡 CPU-only mode is optimized for speed without GPU requirements",
            "💡 Use --help flag to see all available command-line options",
            "💡 Customize chunk size with --window and --slide parameters",
            "💡 Enable auto-paste mode with --auto-paste flag",
            "💡 Recordings saved to system app data directory (keeps last 3)",
            "💡 Use --keep-recordings N to control how many files to keep",
            "💡 Use --reprocess FILE to transcribe an existing recording",
            "💡 Right-click the system tray icon to access Settings",
        ]

        # Start tips display in background
        tips_active = threading.Event()
        tips_active.set()

        def show_tips():
            """Show rotating tips while loading."""
            self._print("\n📥 Loading AI model (nvidia/parakeet-tdt-0.6b-v3)...")
            self._print("=" * 60)
            tip_idx = 0
            dots = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            dot_idx = 0

            while tips_active.is_set():
                # Show current tip with spinner
                tip = tips[tip_idx % len(tips)]
                spinner = dots[dot_idx % len(dots)]
                # Clear line and show tip
                self._print(f"\r{spinner} {tip:<58}", end="", flush=True)

                dot_idx += 1

                # Change tip every 3 seconds (30 iterations at 0.1s each)
                if dot_idx % 30 == 0:
                    tip_idx += 1

                time.sleep(0.1)

            # Clear the line
            self._print("\r" + " " * 60 + "\r", end="", flush=True)
            self._print("=" * 60)

        tips_thread = threading.Thread(target=show_tips, daemon=True)
        tips_thread.start()

        os.environ["CUDA_VISIBLE_DEVICES"] = ""

        self.model = nemo_asr.models.ASRModel.from_pretrained(
            model_name="nvidia/parakeet-tdt-0.6b-v3"
        )
        self.model = self.model.cpu()
        self.model.eval()

        tips_active.clear()
        time.sleep(0.2)  # Let tips thread finish
        self._print("✓ Model loaded successfully\n")

    def create_tray_icon(self):
        """Create system tray icon."""
        # Create simple icon
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor('#1e1e1e'))

        painter = QPainter(pixmap)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor('#00ff00'))
        # Microphone shape
        painter.drawEllipse(16, 10, 32, 30)  # Head
        painter.drawRect(28, 35, 8, 15)  # Stem
        painter.drawLine(20, 50, 44, 50)  # Base
        painter.end()

        icon = QIcon(pixmap)

        # Create tray icon
        self.tray_icon = QSystemTrayIcon(icon, self.app)

        # Create menu
        menu = QMenu()
        menu.addAction(f"Maivi v{__version__}").setEnabled(False)
        menu.addAction("Recording" if self.is_recording else "Ready").setEnabled(False)
        menu.addSeparator()
        menu.addAction("📁 Recordings...", self.open_recordings)
        menu.addAction("⚙️ Settings...", self.open_settings)
        menu.addSeparator()
        menu.addAction("Exit", self.quit_app)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

    def open_settings(self):
        """Open settings dialog."""
        dialog = SettingsDialog(self.config, self.overlay)
        # Connect to settings_changed signal for hot reload
        dialog.settings_changed.connect(self.apply_settings_changes)
        dialog.exec()

    def open_recordings(self):
        """Open recordings dialog."""
        dialog = RecordingsDialog(model=self.model, parent=self.overlay)
        dialog.exec()

    def apply_settings_changes(self, changed_settings):
        """Apply changed settings immediately (hot reload)."""
        print(f"🔄 Applying settings changes: {list(changed_settings.keys())}")

        # Apply theme changes
        if "theme" in changed_settings:
            self.theme = changed_settings["theme"]
            if self.overlay:
                self.overlay.set_theme(self.theme)
            print(f"✓ Theme updated to: {self.theme}")

        # Apply audio device changes
        if "audio_device" in changed_settings:
            self.audio_device = changed_settings["audio_device"]
            # Update recorder with new device
            self.recorder.device = self.audio_device
            device_name = "Default" if self.audio_device is None else f"Device #{self.audio_device}"
            print(f"✓ Audio device updated to: {device_name}")

        # Apply hotkey changes
        if "hotkey" in changed_settings:
            self.hotkey = changed_settings["hotkey"]
            self.hotkey_parts = self._parse_hotkey(self.hotkey)
            if self.overlay:
                self.overlay.hotkey = self.hotkey
                # Update overlay text if not recording
                if not self.is_recording:
                    self.overlay.update_text("", 0)
            print(f"✓ Hotkey updated to: {self.hotkey}")

        # Apply other settings changes
        if "auto_paste" in changed_settings:
            self.auto_paste = changed_settings["auto_paste"]
            print(f"✓ Auto-paste: {self.auto_paste}")

        if "toggle_mode" in changed_settings:
            self.toggle_mode = changed_settings["toggle_mode"]
            mode = "toggle" if self.toggle_mode else "hold"
            print(f"✓ Recording mode: {mode}")

        if "window_seconds" in changed_settings:
            self.window_seconds = changed_settings["window_seconds"]
            print(f"✓ Window size: {self.window_seconds}s")

        if "slide_seconds" in changed_settings:
            self.slide_seconds = changed_settings["slide_seconds"]
            print(f"✓ Slide interval: {self.slide_seconds}s")

        if "start_delay_seconds" in changed_settings:
            self.start_delay_seconds = changed_settings["start_delay_seconds"]
            print(f"✓ Start delay: {self.start_delay_seconds}s")

        if "speed" in changed_settings:
            self.speed = changed_settings["speed"]
            print(f"✓ Speed: {self.speed}x")

        if "keep_recordings" in changed_settings:
            self.keep_recordings = changed_settings["keep_recordings"]
            self.recorder.keep_recordings = self.keep_recordings
            if self.keep_recordings == -1:
                print("✓ Recordings: Delete immediately")
            elif self.keep_recordings == 0:
                print("✓ Recordings: Keep all")
            else:
                print(f"✓ Recordings: Keep last {self.keep_recordings}")

        if "clear_clipboard_after_paste" in changed_settings:
            self.clear_clipboard_after_paste = changed_settings["clear_clipboard_after_paste"]
            print(f"✓ Clear clipboard after paste: {self.clear_clipboard_after_paste}")

        print("✓ All settings applied successfully!")

    def quit_app(self):
        """Quit the application."""
        self.is_shutting_down = True
        if self.app:
            self.app.quit()

    def transcribe_chunk(self, chunk_np, chunk_id, is_last_chunk=False):
        """Transcribe a single audio chunk."""
        try:
            # Wait for model to load
            if self.model is None:
                self._print("⏳ Waiting for model to load...")
                return None

            chunk_file = self.recorder.save_chunk_to_file(chunk_np, chunk_id)
            if not chunk_file:
                return None

            output = self.model.transcribe([chunk_file], timestamps=False)
            text = output[0].text.strip()

            if text:
                # Show chunk transcription in terminal
                self._print(f"[Chunk {chunk_id}] {text}")

                merged = self.chunk_merger.add_chunk(text, is_final=is_last_chunk)
                word_count = len(merged.split()) if merged else 0

                # Update GUI via signal (thread-safe)
                self.signals.update_text.emit(merged, word_count)

                return text
            return None

        except Exception as e:
            self._print(f"Error: {e}")
            return None

    def streaming_transcription_loop(self):
        """Process audio chunks."""
        self.chunk_counter = 0
        self.chunk_merger.reset()

        while self.is_transcribing or not self.recorder.processing_queue.empty():
            chunk_np = self.recorder.get_next_chunk()

            if chunk_np is not None:
                self.chunk_counter += 1
                is_last = not self.is_transcribing and self.recorder.processing_queue.empty()
                self.transcribe_chunk(chunk_np, self.chunk_counter, is_last_chunk=is_last)
            else:
                time.sleep(0.1)

    def start_recording(self):
        """Start recording."""
        if self.is_recording:
            return

        self.is_recording = True
        self.signals.set_recording.emit(True)

        self.recorder.start_recording()
        self.is_transcribing = True
        self.transcription_thread = threading.Thread(target=self.streaming_transcription_loop, daemon=True)
        self.transcription_thread.start()

    def stop_recording(self):
        """Stop recording and finalize."""
        if not self.is_recording:
            return

        self.is_recording = False
        self.signals.set_recording.emit(False)

        audio_file = self.recorder.stop_recording()

        # Check duration
        try:
            data, samplerate = sf.read(audio_file)
            duration = len(data) / samplerate
        except:
            duration = 0

        if duration < self.recorder.start_delay_seconds:
            # Short recording - transcribe all at once
            self._print(
                f"🎯 Short recording detected ({duration:.1f}s), transcribing whole file..."
            )

            self.is_transcribing = False
            if self.transcription_thread:
                self.transcription_thread.join(timeout=2.0)

            try:
                # Wait for model to load (up to 60 seconds)
                wait_count = 0
                while self.model is None and wait_count < 600:
                    if wait_count == 0:
                        self._print("⏳ Waiting for model to load...")
                    time.sleep(0.1)
                    wait_count += 1

                if self.model is None:
                    self._print("❌ Error: Model failed to load")
                    return

                output = self.model.transcribe([audio_file], timestamps=False)
                text = output[0].text.strip()

                if text:
                    self._print(f"[Short recording] {text}")
                    pyperclip.copy(text)
                    self.signals.update_text.emit(f"✓ Copied: {text}", len(text.split()))

                    if NOTIFICATIONS_AVAILABLE:
                        try:
                            preview = text[:50] + "..." if len(text) > 50 else text
                            notification.notify(
                                title="Copied to clipboard!",
                                message=preview,
                                app_name='STT Server',
                                timeout=2
                            )
                        except:
                            pass  # Silently fail if notifications don't work

                    if self.auto_paste:
                        time.sleep(0.2)
                        self.keyboard_controller.press(Key.ctrl)
                        self.keyboard_controller.press("v")
                        self.keyboard_controller.release("v")
                        self.keyboard_controller.release(Key.ctrl)

                        # Clear clipboard after paste if configured
                        if self.clear_clipboard_after_paste:
                            time.sleep(0.1)  # Small delay to ensure paste completes
                            pyperclip.copy("")  # Clear clipboard
                else:
                    self._print("⚠️  No speech detected in recording")
            except Exception as e:
                self._print(f"Error: {e}")

        else:
            # Long recording - finalize streaming
            self._print(f"⏹️  Stopping recording ({duration:.1f}s), finalizing transcription...")

            self.is_transcribing = False
            if self.transcription_thread:
                self.transcription_thread.join(timeout=30.0)

            final_text = self.chunk_merger.get_result()

            # Fallback: if streaming didn't produce results (2-3s recordings),
            # transcribe the whole file instead
            if not final_text:
                self._print("⚠️  No chunks processed, transcribing whole file as fallback...")
                try:
                    # Wait for model to load (should already be loaded)
                    wait_count = 0
                    while self.model is None and wait_count < 600:
                        if wait_count == 0:
                            self._print("⏳ Waiting for model to load...")
                        time.sleep(0.1)
                        wait_count += 1

                    if self.model is None:
                        self._print("❌ Error: Model failed to load")
                        return

                    output = self.model.transcribe([audio_file], timestamps=False)
                    final_text = output[0].text.strip()

                    if final_text:
                        self._print(f"[Fallback transcription] {final_text}")
                except Exception as e:
                    self._print(f"Error in fallback transcription: {e}")
                    return

            if final_text:
                self._print(f"\n📋 Final transcription:\n{final_text}\n")
                pyperclip.copy(final_text)
                self.signals.update_text.emit(f"✓ Copied: {final_text}", len(final_text.split()))

                if NOTIFICATIONS_AVAILABLE:
                    try:
                        preview = final_text[:50] + "..." if len(final_text) > 50 else final_text
                        notification.notify(
                            title="Copied to clipboard!",
                            message=preview,
                            app_name='STT Server',
                            timeout=2
                        )
                    except:
                        pass  # Silently fail if notifications don't work
            else:
                self._print("⚠️  No speech detected in recording")

        # Delete recording immediately if keep_recordings == -1
        if self.keep_recordings == -1 and audio_file:
            try:
                from pathlib import Path
                Path(audio_file).unlink()
                # Optionally print deletion (commented to reduce noise)
                # print(f"🗑️  Deleted recording: {Path(audio_file).name}")
            except Exception as e:
                self._print(f"Warning: Could not delete {audio_file}: {e}")

    def on_press(self, key):
        """Handle key press."""
        if self.is_shutting_down:
            return False

        try:
            self.current_keys.add(key)
        except:
            pass

        # Check for configured hotkey
        hotkey_combo = self._check_hotkey_pressed()

        if self.toggle_mode and hotkey_combo and not self.hotkey_pressed:
            self.hotkey_pressed = True
            if not self.is_recording:
                self.start_recording()
            else:
                self.stop_recording()
            # Note: We don't return False here because:
            # 1. On macOS, returning False stops the entire listener (breaks toggle)
            # 2. pynput can't reliably suppress keys on macOS anyway (OS limitation)
            # Users should choose hotkeys that don't produce characters (F-keys, etc)
            # or accept that the character may appear briefly

    def on_release(self, key):
        """Handle key release."""
        if self.is_shutting_down:
            return False

        if key == Key.esc:
            self.quit_app()
            return False

        try:
            if key in self.current_keys:
                self.current_keys.remove(key)
        except:
            pass

        # Reset debounce if hotkey is no longer pressed
        if not self._check_hotkey_pressed():
            self.hotkey_pressed = False

    def run(self):
        """Run the Qt application."""
        self.app = QApplication(sys.argv)

        # Create overlay window
        self.overlay = TranscriptionOverlay(hotkey=self.hotkey, theme=self.theme)
        self.overlay.show()

        # Load model in background
        model_thread = threading.Thread(target=self.load_model, daemon=True)
        model_thread.start()

        # Create system tray
        self.create_tray_icon()

        # macOS requires accessibility permission for global hotkeys
        accessibility_ready = ensure_accessibility_permissions(prompt=True)
        if not accessibility_ready:
            self._print("⚠️  Grant macOS accessibility permissions so Alt+Q can be captured.")
            opened_accessibility = open_system_settings_privacy("Privacy_Accessibility")
            if opened_accessibility:
                self._print(
                    "   → Opened System Settings → Privacy & Security → Accessibility for you."
                )
            else:
                self._print(
                    "   1. Open System Settings → Privacy & Security → Accessibility manually."
                )

            opened_input = open_system_settings_privacy("Privacy_ListenEvent")
            if opened_input:
                self._print(
                    "   → Opened the Input Monitoring pane so you can enable Maivi."
                )
            else:
                self._print(
                    "   2. Enable Maivi (Python) under Input Monitoring to remove the warning."
                )

            self._print("   Restart Maivi after granting access if the hotkey does not respond.")

        # Start keyboard listener in background
        keyboard_listener = None
        try:
            keyboard_listener = keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release
            )
            keyboard_listener.start()
        except Exception as error:
            self._print(f"❌ Unable to start keyboard listener: {error}")
            if sys.platform == "darwin":
                self._print(
                    "   Check System Settings → Privacy & Security → Accessibility and Input Monitoring."
                )

        self._print("✓ STT Server running")
        self._print(f"  Press {self.hotkey.upper()} to start/stop recording")
        self._print("  Press Esc to exit")

        # Show recording retention policy and directory location
        from platformdirs import user_data_dir
        from pathlib import Path
        recordings_dir = Path(user_data_dir("maivi", "MaximeRivest")) / "recordings"

        if self.keep_recordings == 0:
            self._print(f"  📁 Keeping all recordings in {recordings_dir}")
        elif self.keep_recordings == -1:
            self._print("  🗑️  Deleting recordings immediately after transcription")
        else:
            self._print(f"  📁 Keeping last {self.keep_recordings} recording(s) in {recordings_dir}")
        self._print()

        try:
            sys.exit(self.app.exec())
        finally:
            # Cleanup
            if keyboard_listener:
                keyboard_listener.stop()
            self.recorder.cleanup()
