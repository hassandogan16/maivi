"""
FFmpeg installation utility for Maivi.
Automatically downloads and installs FFmpeg if not available.
"""
import os
import sys
import shutil
import subprocess
import urllib.request
import tarfile
import zipfile
from pathlib import Path
from platformdirs import user_data_dir


def is_ffmpeg_installed():
    """Check if FFmpeg is already installed."""
    return shutil.which("ffmpeg") is not None


def get_ffmpeg_dir():
    """Get the directory where FFmpeg should be installed."""
    return Path(user_data_dir("maivi", "MaximeRivest")) / "ffmpeg"


def add_to_path(ffmpeg_dir):
    """Add FFmpeg directory to PATH for current session."""
    bin_dir = str(ffmpeg_dir / "bin")
    if bin_dir not in os.environ["PATH"]:
        os.environ["PATH"] = bin_dir + os.pathsep + os.environ["PATH"]


def install_ffmpeg_linux():
    """
    Install FFmpeg on Linux.
    Downloads static build from official sources.
    """
    print("📥 Downloading FFmpeg for Linux...")

    ffmpeg_dir = get_ffmpeg_dir()
    ffmpeg_dir.mkdir(parents=True, exist_ok=True)
    bin_dir = ffmpeg_dir / "bin"
    bin_dir.mkdir(exist_ok=True)

    # Use johnvansickle's static builds (widely trusted in the community)
    arch = "amd64" if sys.maxsize > 2**32 else "i686"
    url = f"https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-{arch}-static.tar.xz"

    try:
        # Download
        tar_path = ffmpeg_dir / "ffmpeg.tar.xz"
        print(f"  Downloading from {url}...")
        urllib.request.urlretrieve(url, tar_path)

        # Extract
        print("  Extracting...")
        with tarfile.open(tar_path, 'r:xz') as tar:
            # Find ffmpeg and ffprobe binaries
            for member in tar.getmembers():
                if member.name.endswith('/ffmpeg') or member.name.endswith('/ffprobe'):
                    member.name = os.path.basename(member.name)
                    tar.extract(member, bin_dir)

        # Make executable
        (bin_dir / "ffmpeg").chmod(0o755)
        (bin_dir / "ffprobe").chmod(0o755)

        # Cleanup
        tar_path.unlink()

        # Add to PATH
        add_to_path(ffmpeg_dir)

        print("✓ FFmpeg installed successfully!")
        return True

    except Exception as e:
        print(f"❌ Failed to install FFmpeg: {e}")
        print("   Please install FFmpeg manually:")
        print("   - Ubuntu/Debian: sudo apt install ffmpeg")
        print("   - Fedora: sudo dnf install ffmpeg")
        print("   - Arch: sudo pacman -S ffmpeg")
        return False


def install_ffmpeg_macos():
    """
    Install FFmpeg on macOS.
    First tries Homebrew, then falls back to static binary.
    """
    print("📥 Installing FFmpeg for macOS...")

    # Try Homebrew first
    if shutil.which("brew"):
        print("  Using Homebrew to install FFmpeg...")
        try:
            result = subprocess.run(
                ["brew", "install", "ffmpeg"],
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode == 0:
                print("✓ FFmpeg installed via Homebrew!")
                return True
            else:
                print(f"  Homebrew installation failed: {result.stderr}")
        except Exception as e:
            print(f"  Homebrew installation failed: {e}")

    # Fallback to static binary
    print("  Downloading static FFmpeg binary...")
    ffmpeg_dir = get_ffmpeg_dir()
    ffmpeg_dir.mkdir(parents=True, exist_ok=True)
    bin_dir = ffmpeg_dir / "bin"
    bin_dir.mkdir(exist_ok=True)

    # Use evermeet.cx static builds (official macOS builds)
    try:
        for tool in ["ffmpeg", "ffprobe"]:
            url = f"https://evermeet.cx/ffmpeg/getrelease/{tool}/zip"
            zip_path = ffmpeg_dir / f"{tool}.zip"

            print(f"  Downloading {tool}...")
            urllib.request.urlretrieve(url, zip_path)

            print(f"  Extracting {tool}...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(bin_dir)

            # Make executable
            (bin_dir / tool).chmod(0o755)

            # Cleanup
            zip_path.unlink()

        # Add to PATH
        add_to_path(ffmpeg_dir)

        print("✓ FFmpeg installed successfully!")
        return True

    except Exception as e:
        print(f"❌ Failed to install FFmpeg: {e}")
        print("   Please install FFmpeg manually:")
        print("   - Using Homebrew: brew install ffmpeg")
        print("   - Or download from: https://evermeet.cx/ffmpeg/")
        return False


def install_ffmpeg_windows():
    """
    Install FFmpeg on Windows.
    Downloads official static build.
    """
    print("📥 Downloading FFmpeg for Windows...")

    ffmpeg_dir = get_ffmpeg_dir()
    ffmpeg_dir.mkdir(parents=True, exist_ok=True)
    bin_dir = ffmpeg_dir / "bin"
    bin_dir.mkdir(exist_ok=True)

    # Use gyan.dev builds (official Windows builds)
    url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

    try:
        # Download
        zip_path = ffmpeg_dir / "ffmpeg.zip"
        print(f"  Downloading from {url}...")
        urllib.request.urlretrieve(url, zip_path)

        # Extract
        print("  Extracting...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Find bin directory in the archive
            for member in zip_ref.namelist():
                if '/bin/' in member and (member.endswith('ffmpeg.exe') or member.endswith('ffprobe.exe')):
                    # Extract to our bin directory
                    filename = os.path.basename(member)
                    source = zip_ref.open(member)
                    target = open(bin_dir / filename, 'wb')
                    with source, target:
                        shutil.copyfileobj(source, target)

        # Cleanup
        zip_path.unlink()

        # Add to PATH
        add_to_path(ffmpeg_dir)

        print("✓ FFmpeg installed successfully!")
        return True

    except Exception as e:
        print(f"❌ Failed to install FFmpeg: {e}")
        print("   Please install FFmpeg manually:")
        print("   - Download from: https://www.gyan.dev/ffmpeg/builds/")
        print("   - Or use Chocolatey: choco install ffmpeg")
        return False


def ensure_ffmpeg_installed(silent=False):
    """
    Ensure FFmpeg is installed.
    If not, attempt to install it automatically.

    Args:
        silent: If True, suppress output messages

    Returns:
        bool: True if FFmpeg is available, False otherwise
    """
    # Check if already installed
    if is_ffmpeg_installed():
        if not silent:
            print("✓ FFmpeg is already installed")
        return True

    # Check if we have it in our local directory
    ffmpeg_dir = get_ffmpeg_dir()
    if (ffmpeg_dir / "bin" / "ffmpeg").exists() or (ffmpeg_dir / "bin" / "ffmpeg.exe").exists():
        add_to_path(ffmpeg_dir)
        if is_ffmpeg_installed():
            if not silent:
                print("✓ FFmpeg found in local installation")
            return True

    if not silent:
        print("\n" + "=" * 60)
        print("FFmpeg is not installed")
        print("=" * 60)
        print("FFmpeg is needed for advanced audio processing.")
        print("Would you like to install it automatically? (y/n)")

        try:
            response = input().strip().lower()
            if response != 'y':
                print("Skipping FFmpeg installation.")
                print("Note: Some audio features may not work without FFmpeg.")
                return False
        except (EOFError, KeyboardInterrupt):
            print("\nSkipping FFmpeg installation.")
            return False

    # Install based on platform
    print()
    if sys.platform == "linux":
        success = install_ffmpeg_linux()
    elif sys.platform == "darwin":
        success = install_ffmpeg_macos()
    elif sys.platform == "win32":
        success = install_ffmpeg_windows()
    else:
        print(f"❌ Unsupported platform: {sys.platform}")
        return False

    # Verify installation
    if success and is_ffmpeg_installed():
        print("✓ FFmpeg is now ready to use!")
        return True

    return False


def get_ffmpeg_version():
    """Get FFmpeg version string."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # First line usually contains version
            first_line = result.stdout.split('\n')[0]
            return first_line
        return None
    except Exception:
        return None


if __name__ == "__main__":
    # Test the installer
    print("Testing FFmpeg installer...")
    if ensure_ffmpeg_installed():
        version = get_ffmpeg_version()
        if version:
            print(f"\n{version}")
    else:
        print("\nFFmpeg installation failed or was declined.")
