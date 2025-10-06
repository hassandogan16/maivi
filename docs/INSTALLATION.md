# Installation Guide

This guide covers installation of Maia on different platforms.

## Quick Install (PyPI)

```bash
pip install maia
```

## Platform-Specific Setup

### Linux

**Ubuntu/Debian:**
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install portaudio19-dev python3-pyaudio

# Install Maia
pip install maia
```

**Fedora/RHEL:**
```bash
sudo dnf install portaudio-devel
pip install maia
```

**Arch Linux:**
```bash
sudo pacman -S portaudio
pip install maia
```

### macOS

```bash
# Install PortAudio via Homebrew
brew install portaudio

# Install Maia
pip install maia
```

### Windows

PortAudio is typically included with PyAudio on Windows, so no additional setup is needed:

```bash
pip install maia
```

## Installation from Source

```bash
# Clone the repository
git clone https://github.com/maximerivest/maia.git
cd maia

# Install in development mode
pip install -e .

# Or install with dev dependencies
pip install -e .[dev]
```

## Using Pre-built Executables

Download the appropriate executable for your platform from [Releases](https://github.com/maximerivest/maia/releases):

- **Linux:** `maia-linux`
- **macOS:** `maia-macos`
- **Windows:** `maia-windows.exe`

Make it executable (Linux/macOS):
```bash
chmod +x maia-linux  # or maia-macos
./maia-linux
```

## Verifying Installation

```bash
# Check Maia is installed
maia --help

# Verify dependencies
python -c "import maia; print(maia.__version__)"
python -c "import nemo.collections.asr; print('NeMo OK')"
python -c "from PySide6.QtWidgets import QApplication; print('Qt OK')"
```

## Common Installation Issues

### PyAudio Installation Fails

**Linux:**
```bash
sudo apt-get install portaudio19-dev python3-dev
pip install pyaudio
```

**macOS:**
```bash
brew install portaudio
pip install pyaudio
```

### NeMo Installation Issues

NeMo requires PyTorch. If you encounter issues:

```bash
# Install PyTorch first
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# Then install Maia
pip install maia
```

### Qt/PySide6 Issues

If you have Qt conflicts:

```bash
pip uninstall PySide6 PyQt6 PyQt5
pip install PySide6
```

### Permission Errors

On Linux, you may need to add your user to the `audio` group:

```bash
sudo usermod -a -G audio $USER
# Log out and back in for changes to take effect
```

## First Run

The first time you run Maia, it will download the NVIDIA Parakeet model (~600MB). This may take a few minutes depending on your internet connection.

```bash
# Launch Maia GUI
maia

# Or CLI mode
maia-cli
```

## Uninstallation

```bash
pip uninstall maia
```

To also remove the model cache:
```bash
rm -rf ~/.cache/huggingface/hub/models--nvidia--parakeet-tdt-0.6b-v3
```

## Next Steps

- Read the [Usage Guide](USAGE.md)
- Check out [Configuration](CONFIGURATION.md)
- See [Troubleshooting](TROUBLESHOOTING.md)
