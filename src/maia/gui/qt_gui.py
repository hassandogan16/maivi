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
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont

import nemo.collections.asr as nemo_asr
import pyperclip
import soundfile as sf
from pynput import keyboard
from pynput.keyboard import Key, Controller

from maia.core.streaming_recorder import StreamingRecorder
from maia.core.chunk_merger import SimpleChunkMerger

# Cross-platform notifications
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

    def __init__(self, width=400, height=60):
        super().__init__()
        self.width = width
        self.height = height
        self.recording = False

        # Setup window
        self.setWindowTitle("STT Live")
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool  # Don't show in taskbar
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        # Dark theme
        self.bg_color = '#1e1e1e'
        self.text_color = '#00ff00'
        self.accent_color = '#ff4444'

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {self.bg_color};
                border: 2px solid #444444;
            }}
            QLabel {{
                color: {self.text_color};
                background-color: transparent;
                border: none;
            }}
        """)

        # Layout
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Status indicator
        self.status_label = QLabel("○")
        self.status_label.setFont(QFont('Arial', 16, QFont.Bold))
        self.status_label.setStyleSheet(f"color: #666666;")
        layout.addWidget(self.status_label)

        # Text display
        self.text_label = QLabel("Ready - Press Alt+Q to record")
        self.text_label.setFont(QFont('Courier', 10))
        self.text_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self.text_label, stretch=1)

        # Word count
        self.count_label = QLabel("")
        self.count_label.setFont(QFont('Arial', 8))
        self.count_label.setStyleSheet("color: #888888;")
        layout.addWidget(self.count_label)

        self.setLayout(layout)

        # Position at bottom-right
        self.resize(self.width, self.height)
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - self.width - 20
        y = screen.height() - self.height - 60  # Above taskbar
        self.move(x, y)

    def set_recording(self, is_recording):
        """Update recording indicator."""
        self.recording = is_recording
        if is_recording:
            self.status_label.setText("●")
            self.status_label.setStyleSheet(f"color: {self.accent_color};")
            self.text_label.setText("🎤 Listening...")
        else:
            self.status_label.setText("○")
            self.status_label.setStyleSheet("color: #666666;")

    def update_text(self, text, word_count=0):
        """Update scrolling text (last 50 chars)."""
        display_text = text[-50:] if len(text) > 50 else text
        self.text_label.setText(display_text or "Ready - Press Alt+Q to record")
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
    ):
        super().__init__()

        self.auto_paste = auto_paste
        self.speed = speed
        self.toggle_mode = toggle_mode

        # Model and recorder
        self.model = None
        self.recorder = StreamingRecorder(
            window_seconds=window_seconds,
            slide_seconds=slide_seconds,
            start_delay_seconds=start_delay_seconds,
            speed=speed,
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
        print("Loading model...")
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

        self.model = nemo_asr.models.ASRModel.from_pretrained(
            model_name="nvidia/parakeet-tdt-0.6b-v3"
        )
        self.model = self.model.cpu()
        self.model.eval()
        print("✓ Model loaded\n")

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
        menu.addAction("STT Server").setEnabled(False)
        menu.addAction("Recording" if self.is_recording else "Ready").setEnabled(False)
        menu.addSeparator()
        menu.addAction("Exit", self.quit_app)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

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
                print("⏳ Waiting for model to load...")
                return None

            chunk_file = self.recorder.save_chunk_to_file(chunk_np, chunk_id)
            if not chunk_file:
                return None

            output = self.model.transcribe([chunk_file], timestamps=False)
            text = output[0].text.strip()

            if text:
                prev_len = len(self.chunk_merger.result_words)
                merged = self.chunk_merger.add_chunk(text, chunk_id, is_final=is_last_chunk)
                new_len = len(self.chunk_merger.result_words)

                # Update GUI via signal (thread-safe)
                self.signals.update_text.emit(merged, new_len)

                return text
            return None

        except Exception as e:
            print(f"Error: {e}")
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
            self.is_transcribing = False
            if self.transcription_thread:
                self.transcription_thread.join(timeout=2.0)

            try:
                # Wait for model to load
                if self.model is None:
                    print("⏳ Model still loading, cannot transcribe yet")
                    return

                output = self.model.transcribe([audio_file], timestamps=False)
                text = output[0].text.strip()

                if text:
                    pyperclip.copy(text)
                    self.signals.update_text.emit(f"✓ Copied: {text}", len(text.split()))

                    if NOTIFICATIONS_AVAILABLE:
                        preview = text[:50] + "..." if len(text) > 50 else text
                        notification.notify(
                            title="Copied to clipboard!",
                            message=preview,
                            app_name='STT Server',
                            timeout=2
                        )

                    if self.auto_paste:
                        time.sleep(0.2)
                        self.keyboard_controller.press(Key.ctrl)
                        self.keyboard_controller.press("v")
                        self.keyboard_controller.release("v")
                        self.keyboard_controller.release(Key.ctrl)
            except Exception as e:
                print(f"Error: {e}")

        else:
            # Long recording - finalize streaming
            self.is_transcribing = False
            if self.transcription_thread:
                self.transcription_thread.join(timeout=30.0)

            final_text = self.chunk_merger.get_result()
            if final_text:
                pyperclip.copy(final_text)
                self.signals.update_text.emit(f"✓ Copied: {final_text}", len(final_text.split()))

                if NOTIFICATIONS_AVAILABLE:
                    preview = final_text[:50] + "..." if len(final_text) > 50 else final_text
                    notification.notify(
                        title="Copied to clipboard!",
                        message=preview,
                        app_name='STT Server',
                        timeout=2
                    )

    def on_press(self, key):
        """Handle key press."""
        if self.is_shutting_down:
            return False

        try:
            self.current_keys.add(key)
        except:
            pass

        # Check for Alt+Q
        alt_pressed = Key.alt_l in self.current_keys or Key.alt in self.current_keys or Key.alt_r in self.current_keys
        try:
            q_pressed = keyboard.KeyCode.from_char('q') in self.current_keys
        except:
            q_pressed = False

        hotkey_combo = alt_pressed and q_pressed

        if self.toggle_mode and hotkey_combo and not self.hotkey_pressed:
            self.hotkey_pressed = True
            if not self.is_recording:
                self.start_recording()
            else:
                self.stop_recording()

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

        # Reset debounce
        alt_pressed = Key.alt_l in self.current_keys or Key.alt in self.current_keys or Key.alt_r in self.current_keys
        try:
            q_pressed = keyboard.KeyCode.from_char('q') in self.current_keys
        except:
            q_pressed = False

        if not (alt_pressed and q_pressed):
            self.hotkey_pressed = False

    def run(self):
        """Run the Qt application."""
        self.app = QApplication(sys.argv)

        # Create overlay window
        self.overlay = TranscriptionOverlay()
        self.overlay.show()

        # Load model in background
        model_thread = threading.Thread(target=self.load_model, daemon=True)
        model_thread.start()

        # Create system tray
        self.create_tray_icon()

        # Start keyboard listener in background
        keyboard_listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )
        keyboard_listener.start()

        print("✓ STT Server running")
        print("  Press Alt+Q to start/stop recording")
        print("  Press Esc to exit\n")

        try:
            sys.exit(self.app.exec())
        finally:
            # Cleanup
            keyboard_listener.stop()
            self.recorder.cleanup()
