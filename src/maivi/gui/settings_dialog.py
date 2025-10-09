"""
Settings dialog for Maivi configuration.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDoubleSpinBox, QSpinBox, QCheckBox,
    QGroupBox, QFormLayout, QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence
from maivi import __version__


class HotkeyEdit(QLineEdit):
    """Custom line edit for capturing hotkey combinations."""

    hotkey_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("Click and press your desired hotkey...")
        self._current_keys = set()
        self._hotkey = ""

    def keyPressEvent(self, event):
        """Capture key press for hotkey binding."""
        if event.key() == Qt.Key_Escape:
            self.clear()
            return

        # Map key to string representation
        key_name = self._get_key_name(event)
        if key_name:
            self._current_keys.add(key_name)
            self._update_display()

    def keyReleaseEvent(self, event):
        """Handle key release."""
        key_name = self._get_key_name(event)
        if key_name and key_name in self._current_keys:
            # Only remove the specific key that was released
            pass

        # If we have keys, finalize the combination after a short delay
        if self._current_keys:
            self._finalize_hotkey()

    def _get_key_name(self, event):
        """Convert Qt key event to normalized key name."""
        key = event.key()

        # Modifier keys
        if key == Qt.Key_Control:
            return "ctrl"
        elif key == Qt.Key_Alt:
            return "alt"
        elif key == Qt.Key_Shift:
            return "shift"
        elif key == Qt.Key_Meta:
            return "meta"

        # Regular keys
        text = event.text().lower()
        if text and text.isalnum():
            return text

        # Special keys
        special_keys = {
            Qt.Key_Space: "space",
            Qt.Key_Return: "return",
            Qt.Key_Enter: "enter",
            Qt.Key_Tab: "tab",
            Qt.Key_Backspace: "backspace",
            Qt.Key_Delete: "delete",
            Qt.Key_Insert: "insert",
            Qt.Key_Home: "home",
            Qt.Key_End: "end",
            Qt.Key_PageUp: "pageup",
            Qt.Key_PageDown: "pagedown",
            Qt.Key_Up: "up",
            Qt.Key_Down: "down",
            Qt.Key_Left: "left",
            Qt.Key_Right: "right",
        }

        # F-keys
        for i in range(1, 13):
            special_keys[Qt.Key_F1 + i - 1] = f"f{i}"

        return special_keys.get(key)

    def _update_display(self):
        """Update the display with current key combination."""
        # Sort modifiers first
        modifiers = []
        keys = []

        for key in self._current_keys:
            if key in ["ctrl", "alt", "shift", "meta"]:
                modifiers.append(key)
            else:
                keys.append(key)

        modifiers.sort()
        display = "+".join(modifiers + keys)
        self.setText(display)

    def _finalize_hotkey(self):
        """Finalize the hotkey combination."""
        if not self._current_keys:
            return

        # Sort modifiers first
        modifiers = []
        keys = []

        for key in self._current_keys:
            if key in ["ctrl", "alt", "shift", "meta"]:
                modifiers.append(key)
            else:
                keys.append(key)

        modifiers.sort()
        self._hotkey = "+".join(modifiers + keys)
        self.setText(self._hotkey)
        self.hotkey_changed.emit(self._hotkey)
        self._current_keys.clear()

    def set_hotkey(self, hotkey: str):
        """Set the hotkey programmatically."""
        self._hotkey = hotkey
        self.setText(hotkey)

    def get_hotkey(self) -> str:
        """Get the current hotkey."""
        return self._hotkey or self.text()


class SettingsDialog(QDialog):
    """Settings dialog for configuring Maivi."""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle(f"Maivi Settings - v{__version__}")
        self.setMinimumWidth(500)
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout()

        # Version info
        version_label = QLabel(f"<b>Maivi v{__version__}</b>")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)

        # Hotkey settings
        hotkey_group = QGroupBox("Hotkey")
        hotkey_layout = QFormLayout()

        self.hotkey_edit = HotkeyEdit()
        hotkey_layout.addRow("Recording Hotkey:", self.hotkey_edit)

        hotkey_help = QLabel("Click the field and press your desired key combination.\nPress Esc to clear.")
        hotkey_help.setStyleSheet("color: gray; font-size: 9pt;")
        hotkey_layout.addRow("", hotkey_help)

        hotkey_group.setLayout(hotkey_layout)
        layout.addWidget(hotkey_group)

        # Audio settings
        audio_group = QGroupBox("Audio Settings")
        audio_layout = QFormLayout()

        self.window_spin = QDoubleSpinBox()
        self.window_spin.setRange(1.0, 30.0)
        self.window_spin.setSingleStep(0.5)
        self.window_spin.setSuffix(" seconds")
        self.window_spin.setToolTip("Audio chunk window size (larger = better quality but slower)")
        audio_layout.addRow("Window Size:", self.window_spin)

        self.slide_spin = QDoubleSpinBox()
        self.slide_spin.setRange(0.5, 20.0)
        self.slide_spin.setSingleStep(0.5)
        self.slide_spin.setSuffix(" seconds")
        self.slide_spin.setToolTip("Slide interval (smaller = more overlap, higher CPU usage)")
        audio_layout.addRow("Slide Interval:", self.slide_spin)

        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0.0, 10.0)
        self.delay_spin.setSingleStep(0.5)
        self.delay_spin.setSuffix(" seconds")
        self.delay_spin.setToolTip("Processing start delay")
        audio_layout.addRow("Start Delay:", self.delay_spin)

        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.5, 2.0)
        self.speed_spin.setSingleStep(0.1)
        self.speed_spin.setDecimals(1)
        self.speed_spin.setToolTip("Speed adjustment factor (experimental)")
        audio_layout.addRow("Speed Factor:", self.speed_spin)

        audio_group.setLayout(audio_layout)
        layout.addWidget(audio_group)

        # Behavior settings
        behavior_group = QGroupBox("Behavior")
        behavior_layout = QFormLayout()

        self.toggle_mode_check = QCheckBox()
        self.toggle_mode_check.setToolTip("Toggle mode: press once to start, once to stop\nUnchecked: hold mode (hold hotkey to record)")
        behavior_layout.addRow("Toggle Mode:", self.toggle_mode_check)

        self.auto_paste_check = QCheckBox()
        self.auto_paste_check.setToolTip("Automatically paste transcribed text (default: copy to clipboard only)")
        behavior_layout.addRow("Auto-paste:", self.auto_paste_check)

        behavior_group.setLayout(behavior_layout)
        layout.addWidget(behavior_group)

        # Recording settings
        recording_group = QGroupBox("Recording Management")
        recording_layout = QFormLayout()

        self.keep_recordings_spin = QSpinBox()
        self.keep_recordings_spin.setRange(-1, 1000)
        self.keep_recordings_spin.setSpecialValueText("Delete immediately")
        self.keep_recordings_spin.setToolTip("Number of recordings to keep\n-1: delete immediately\n0: keep all\n>0: keep last N")
        recording_layout.addRow("Keep Recordings:", self.keep_recordings_spin)

        recording_group.setLayout(recording_layout)
        layout.addWidget(recording_group)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.RestoreDefaults
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self.restore_defaults)

        layout.addWidget(button_box)

        self.setLayout(layout)

    def load_settings(self):
        """Load settings from config into UI."""
        self.hotkey_edit.set_hotkey(self.config.get("hotkey", "alt+q"))
        self.window_spin.setValue(self.config.get("window_seconds", 7.0))
        self.slide_spin.setValue(self.config.get("slide_seconds", 3.0))
        self.delay_spin.setValue(self.config.get("start_delay_seconds", 2.0))
        self.speed_spin.setValue(self.config.get("speed", 1.0))
        self.auto_paste_check.setChecked(self.config.get("auto_paste", False))
        self.toggle_mode_check.setChecked(self.config.get("toggle_mode", True))
        self.keep_recordings_spin.setValue(self.config.get("keep_recordings", 3))

    def save_settings(self):
        """Save settings from UI to config."""
        self.config.set("hotkey", self.hotkey_edit.get_hotkey())
        self.config.set("window_seconds", self.window_spin.value())
        self.config.set("slide_seconds", self.slide_spin.value())
        self.config.set("start_delay_seconds", self.delay_spin.value())
        self.config.set("speed", self.speed_spin.value())
        self.config.set("auto_paste", self.auto_paste_check.isChecked())
        self.config.set("toggle_mode", self.toggle_mode_check.isChecked())
        self.config.set("keep_recordings", self.keep_recordings_spin.value())
        self.config.save()

    def restore_defaults(self):
        """Restore default settings."""
        reply = QMessageBox.question(
            self,
            "Restore Defaults",
            "Are you sure you want to restore all settings to their default values?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.config.reset_to_defaults()
            self.load_settings()

    def accept(self):
        """Handle OK button."""
        self.save_settings()

        # Show restart message
        QMessageBox.information(
            self,
            "Settings Saved",
            "Settings have been saved.\n\nNote: Some settings (like hotkey) require a restart to take effect.",
            QMessageBox.Ok
        )

        super().accept()
