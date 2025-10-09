"""
Recordings dialog for viewing and managing past recordings.
"""
import os
import subprocess
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QSplitter, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from platformdirs import user_data_dir
import pyperclip


class RecordingsDialog(QDialog):
    """Dialog for viewing and managing recordings with transcriptions."""

    def __init__(self, model=None, parent=None):
        super().__init__(parent)
        self.model = model  # STT model for transcribing
        self.recordings_dir = Path(user_data_dir("maivi", "MaximeRivest")) / "recordings"
        self.current_recording = None
        self.transcription_cache = {}  # Cache transcriptions

        self.setWindowTitle("Recordings")
        self.setMinimumSize(800, 600)
        self.setup_ui()
        self.load_recordings()

    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout()

        # Title
        title = QLabel("<b>Recordings History</b>")
        title.setFont(QFont('Arial', 14))
        layout.addWidget(title)

        # Splitter for recordings list and details
        splitter = QSplitter(Qt.Horizontal)

        # Left side - Recordings list
        left_widget = QVBoxLayout()
        left_container = QDialog()
        left_container.setLayout(left_widget)

        list_label = QLabel("Recent Recordings:")
        left_widget.addWidget(list_label)

        self.recordings_list = QListWidget()
        self.recordings_list.itemClicked.connect(self.on_recording_selected)
        left_widget.addWidget(self.recordings_list)

        splitter.addWidget(left_container)

        # Right side - Recording details
        right_widget = QVBoxLayout()
        right_container = QDialog()
        right_container.setLayout(right_widget)

        # Recording info
        self.info_label = QLabel("Select a recording to view details")
        self.info_label.setWordWrap(True)
        right_widget.addWidget(self.info_label)

        # Transcription text
        transcription_label = QLabel("Transcription:")
        right_widget.addWidget(transcription_label)

        self.transcription_text = QTextEdit()
        self.transcription_text.setReadOnly(True)
        self.transcription_text.setPlaceholderText("Transcription will appear here...")
        right_widget.addWidget(self.transcription_text)

        # Action buttons
        button_layout = QHBoxLayout()

        self.play_button = QPushButton("▶ Play Audio")
        self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self.play_audio)
        button_layout.addWidget(self.play_button)

        self.copy_button = QPushButton("📋 Copy Text")
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self.copy_transcription)
        button_layout.addWidget(self.copy_button)

        self.transcribe_button = QPushButton("🎤 Transcribe Now")
        self.transcribe_button.setEnabled(False)
        self.transcribe_button.clicked.connect(self.transcribe_recording)
        button_layout.addWidget(self.transcribe_button)

        right_widget.addLayout(button_layout)

        splitter.addWidget(right_container)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self.setLayout(layout)

    def load_recordings(self):
        """Load list of recordings from the recordings directory."""
        self.recordings_list.clear()

        if not self.recordings_dir.exists():
            item = QListWidgetItem("No recordings found")
            item.setFlags(Qt.NoItemFlags)
            self.recordings_list.addItem(item)
            return

        # Get all recording files
        recording_files = sorted(
            self.recordings_dir.glob("recording_*.wav"),
            key=lambda p: p.stat().st_mtime,
            reverse=True  # Newest first
        )

        if not recording_files:
            item = QListWidgetItem("No recordings found")
            item.setFlags(Qt.NoItemFlags)
            self.recordings_list.addItem(item)
            return

        # Add recordings to list
        for recording_path in recording_files:
            # Parse filename
            filename = recording_path.name
            try:
                # Extract timestamp from filename: recording_YYYYMMDD_HHMMSS[_speed].wav
                parts = filename.replace("recording_", "").replace(".wav", "").split("_")
                date_str = parts[0]  # YYYYMMDD
                time_str = parts[1]  # HHMMSS

                # Format nicely
                date_obj = datetime.strptime(date_str, "%Y%m%d")
                time_obj = datetime.strptime(time_str, "%H%M%S")
                display_date = date_obj.strftime("%b %d, %Y")
                display_time = time_obj.strftime("%I:%M:%S %p")

                # Check for speed suffix
                speed_info = ""
                if len(parts) > 2:
                    speed_info = f" ({parts[2]})"

                # Get file size
                size_mb = recording_path.stat().st_size / (1024 * 1024)

                display_text = f"{display_date} - {display_time}{speed_info} ({size_mb:.1f} MB)"
            except Exception:
                # Fallback to filename if parsing fails
                display_text = filename

            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, str(recording_path))  # Store full path
            self.recordings_list.addItem(item)

    def on_recording_selected(self, item):
        """Handle recording selection."""
        recording_path = item.data(Qt.UserRole)
        if not recording_path:
            return

        self.current_recording = Path(recording_path)

        # Update info label
        size_mb = self.current_recording.stat().st_size / (1024 * 1024)
        mod_time = datetime.fromtimestamp(self.current_recording.stat().st_mtime)
        info_text = f"<b>File:</b> {self.current_recording.name}<br>"
        info_text += f"<b>Size:</b> {size_mb:.2f} MB<br>"
        info_text += f"<b>Modified:</b> {mod_time.strftime('%Y-%m-%d %H:%M:%S')}"
        self.info_label.setText(info_text)

        # Enable buttons
        self.play_button.setEnabled(True)
        self.transcribe_button.setEnabled(self.model is not None)

        # Check if we have cached transcription
        if str(self.current_recording) in self.transcription_cache:
            transcription = self.transcription_cache[str(self.current_recording)]
            self.transcription_text.setText(transcription)
            self.copy_button.setEnabled(True)
        else:
            self.transcription_text.setText("Click 'Transcribe Now' to generate transcription...")
            self.copy_button.setEnabled(False)

    def play_audio(self):
        """Play the selected audio file."""
        if not self.current_recording:
            return

        try:
            # Use system default audio player
            if os.name == 'nt':  # Windows
                os.startfile(str(self.current_recording))
            elif os.name == 'posix':  # macOS/Linux
                subprocess.run(['open', str(self.current_recording)], check=False)
        except Exception as e:
            QMessageBox.warning(self, "Playback Error", f"Could not play audio:\n{e}")

    def copy_transcription(self):
        """Copy the transcription to clipboard."""
        text = self.transcription_text.toPlainText()
        if text and text != "Click 'Transcribe Now' to generate transcription...":
            pyperclip.copy(text)
            QMessageBox.information(self, "Copied", "Transcription copied to clipboard!")

    def transcribe_recording(self):
        """Transcribe the selected recording."""
        if not self.current_recording or not self.model:
            return

        # Check if already cached
        if str(self.current_recording) in self.transcription_cache:
            transcription = self.transcription_cache[str(self.current_recording)]
            self.transcription_text.setText(transcription)
            self.copy_button.setEnabled(True)
            return

        # Disable button and show progress
        self.transcribe_button.setEnabled(False)
        self.transcription_text.setText("Transcribing... Please wait...")

        try:
            # Transcribe
            output = self.model.transcribe([str(self.current_recording)], timestamps=False)
            transcription = output[0].text.strip()

            if transcription:
                # Cache it
                self.transcription_cache[str(self.current_recording)] = transcription
                self.transcription_text.setText(transcription)
                self.copy_button.setEnabled(True)
            else:
                self.transcription_text.setText("No speech detected in recording.")
        except Exception as e:
            self.transcription_text.setText(f"Error during transcription:\n{e}")
        finally:
            self.transcribe_button.setEnabled(True)
