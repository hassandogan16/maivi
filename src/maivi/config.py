"""
Configuration management for Maivi.
Handles settings persistence and loading.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from platformdirs import user_config_dir


class Config:
    """Manages application configuration."""

    DEFAULT_SETTINGS = {
        "hotkey": "alt+q",
        "window_seconds": 7.0,
        "slide_seconds": 3.0,
        "start_delay_seconds": 2.0,
        "speed": 1.0,
        "auto_paste": False,
        "toggle_mode": True,
        "keep_recordings": 3,
    }

    def __init__(self):
        """Initialize config manager."""
        self.config_dir = Path(user_config_dir("maivi", "MaximeRivest"))
        self.config_file = self.config_dir / "config.json"
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.load()

    def load(self) -> None:
        """Load settings from config file."""
        if not self.config_file.exists():
            return

        try:
            with open(self.config_file, 'r') as f:
                loaded = json.load(f)
                # Merge with defaults to handle new settings
                self.settings.update(loaded)
        except Exception as e:
            print(f"Warning: Could not load config: {e}")

    def save(self) -> None:
        """Save settings to config file."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a setting value."""
        self.settings[key] = value

    def update(self, settings: Dict[str, Any]) -> None:
        """Update multiple settings at once."""
        self.settings.update(settings)

    def reset_to_defaults(self) -> None:
        """Reset all settings to defaults."""
        self.settings = self.DEFAULT_SETTINGS.copy()
