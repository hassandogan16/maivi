# Setup Instructions for Maia

This document contains instructions for setting up the GitHub repository and preparing for the first release.

## ✅ What's Already Done

The repository has been created with:
- ✅ Clean Python package structure (`src/maia/`)
- ✅ Migrated all core files from experimental repo
- ✅ Updated all imports to use proper package structure
- ✅ PyPI-ready `pyproject.toml` with dependencies and entry points
- ✅ Comprehensive README with installation and usage instructions
- ✅ MIT License
- ✅ `.gitignore` for Python projects
- ✅ GitHub Actions for:
  - PyPI releases (automated on tag push)
  - Executable builds (Linux, macOS, Windows)
  - CI/CD tests
- ✅ Basic unit tests
- ✅ Contributing guidelines
- ✅ Installation and release documentation
- ✅ Local git repository initialized with commits

## 🚀 Next Steps

### 1. Create GitHub Repository

Since the `gh` CLI requires authentication, you'll need to create the repository manually:

**Option A: Using GitHub CLI (Recommended)**
```bash
cd /home/maxime/Projects/maia

# Authenticate with GitHub
gh auth login

# Create repository and push
gh repo create maia --public --source=. --description "Maia - My AI Assistant: Real-time voice-to-text with hotkey support" --push
```

**Option B: Using GitHub Web Interface**
1. Go to https://github.com/new
2. Repository name: `maia`
3. Description: "Maia - My AI Assistant: Real-time voice-to-text with hotkey support"
4. Public repository
5. Don't initialize with README (we already have one)
6. Create repository

Then push your local repo:
```bash
cd /home/maxime/Projects/maia
git remote add origin https://github.com/YOUR_USERNAME/maia.git
git branch -M main
git push -u origin main
```

### 2. Set Up PyPI

1. **Create PyPI Account**
   - Go to https://pypi.org/account/register/
   - Verify your email

2. **Generate API Token**
   - Go to https://pypi.org/manage/account/token/
   - Create a new API token
   - Scope: "Entire account" (or specific to "maia" project after first upload)
   - Copy the token (starts with `pypi-...`)

3. **Add Token to GitHub Secrets**
   - Go to your repo: Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `PYPI_API_TOKEN`
   - Value: Paste your PyPI API token
   - Click "Add secret"

### 3. Test the Package Locally

Before releasing, test that everything works:

```bash
cd /home/maxime/Projects/maia

# Install in development mode
pip install -e .

# Test imports
python -c "from maia.core.chunk_merger import SimpleChunkMerger; print('✓ Imports work')"

# Run tests
pip install pytest
pytest

# Test CLI
maia-cli --help

# Note: GUI test requires display server
# maia
```

### 4. First Release

When you're ready to release:

```bash
# Make sure everything is committed
git status

# Create and push a version tag
git tag -a v0.1.0 -m "Release v0.1.0 - Initial public release"
git push origin v0.1.0
```

This will automatically:
1. ✅ Build the Python package
2. ✅ Publish to PyPI (if secrets are configured)
3. ✅ Build executables for Linux, macOS, Windows
4. ✅ Create a GitHub Release with all artifacts

### 5. Verify Release

After the GitHub Actions complete (check Actions tab):

1. **Check PyPI**
   ```bash
   pip install maia
   maia --help
   ```

2. **Check GitHub Releases**
   - Go to https://github.com/YOUR_USERNAME/maia/releases
   - Verify v0.1.0 release exists
   - Download and test executables

3. **Update Repository Settings**
   - Add topics: `python`, `speech-to-text`, `voice`, `ai`, `nemo`, `transcription`
   - Add website: Link to PyPI or documentation
   - Enable Issues and Discussions

## 📋 Package Entry Points

The package provides two entry points:

1. **`maia`** - Launches Qt GUI (recommended for end users)
   ```bash
   maia
   ```

2. **`maia-cli`** - CLI interface with options
   ```bash
   maia-cli --show-ui
   ```

## 🔧 Configuration Files

### pyproject.toml
- Package metadata and dependencies
- Entry points for `maia` and `maia-cli`
- Development and build dependencies

### GitHub Actions
- `.github/workflows/pypi-release.yml` - Publishes to PyPI on tag push
- `.github/workflows/build-executables.yml` - Builds cross-platform executables
- `.github/workflows/tests.yml` - Runs tests on PRs and commits

## 🐛 Troubleshooting

### Import Errors After Installation

If you get import errors, make sure you're using the correct package structure:
```python
from maia.core.chunk_merger import SimpleChunkMerger
from maia.core.streaming_recorder import StreamingRecorder
from maia.gui.qt_gui import QtSTTServer
```

### GitHub Actions Failing

- **PyPI Upload Fails**: Check that `PYPI_API_TOKEN` secret is set correctly
- **Build Fails**: Check the Actions logs for specific errors
- **Tests Fail**: Run `pytest` locally to debug

### Model Download Issues

The NVIDIA Parakeet model (~600MB) downloads on first run. If it fails:
```bash
python -c "import nemo.collections.asr as nemo_asr; nemo_asr.models.ASRModel.from_pretrained('nvidia/parakeet-tdt-0.6b-v3')"
```

## 📚 Additional Documentation

- `README.md` - User-facing documentation
- `CONTRIBUTING.md` - Contribution guidelines
- `docs/INSTALLATION.md` - Detailed installation guide
- `docs/RELEASE.md` - Release process documentation

## 🎯 Success Checklist

Before considering the release complete:

- [ ] GitHub repository created and pushed
- [ ] PyPI API token configured in GitHub Secrets
- [ ] Local tests pass (`pytest`)
- [ ] Package installs correctly (`pip install -e .`)
- [ ] Both entry points work (`maia` and `maia-cli`)
- [ ] First tag created and pushed (`v0.1.0`)
- [ ] GitHub Actions complete successfully
- [ ] Package available on PyPI
- [ ] GitHub Release created with executables
- [ ] README displays correctly on GitHub

## 🚀 Post-Release

After successful release:

1. **Announce**
   - Share on Twitter/X, Reddit, HN
   - Add to awesome-python lists
   - Write a blog post

2. **Monitor**
   - Watch GitHub Issues
   - Monitor PyPI download stats
   - Gather user feedback

3. **Plan v0.2**
   - macOS/Windows testing
   - Feature requests
   - Bug fixes

---

Good luck with the release! 🎉
