#!/usr/bin/env python3
"""
Entry point for Maia - My AI Assistant (Voice-to-Text).
Launches the Qt GUI by default.
"""

def main():
    """Main entry point for Maia GUI."""
    import sys
    from maia.gui.qt_gui import QtSTTServer

    server = QtSTTServer(
        auto_paste=False,
        window_seconds=7.0,  # Chunk size (context window)
        slide_seconds=3.0,   # Slide interval (4s overlap)
        start_delay_seconds=2.0,  # Start processing delay
        speed=1.0,
        toggle_mode=True,
    )
    sys.exit(server.run())


if __name__ == "__main__":
    main()
