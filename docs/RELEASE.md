# Release Guide

This guide explains how to release a new version of Maia.

## Prerequisites

1. Ensure all tests pass: `pytest`
2. Ensure linting passes: `black src/ && isort src/ && flake8 src/`
3. Update version in `pyproject.toml`
4. Update CHANGELOG (if you have one)
5. Commit all changes

## PyPI Setup (First Time Only)

1. Create a PyPI account at https://pypi.org
2. Generate an API token at https://pypi.org/manage/account/token/
3. Add the token to GitHub Secrets:
   - Go to your repo's Settings → Secrets and variables → Actions
   - Add new secret: `PYPI_API_TOKEN`
   - Paste your PyPI API token

## Release Process

### 1. Update Version

Edit `pyproject.toml`:
```toml
[project]
version = "0.2.0"  # Update this
```

Commit the change:
```bash
git add pyproject.toml
git commit -m "Bump version to 0.2.0"
git push
```

### 2. Create and Push Tag

```bash
# Create annotated tag
git tag -a v0.2.0 -m "Release v0.2.0"

# Push tag to GitHub
git push origin v0.2.0
```

### 3. Automated Release

Once you push the tag, GitHub Actions will automatically:
1. Build the Python package
2. Publish to PyPI
3. Build executables for Linux, macOS, and Windows
4. Create a GitHub Release with all artifacts

### 4. Verify Release

Check that:
- [ ] Package is available on PyPI: `pip install maia==0.2.0`
- [ ] GitHub Release is created with executables
- [ ] Release notes are generated

## Manual Release (if needed)

If you need to release manually:

### Build Package

```bash
# Install build tools
pip install build twine

# Build
python -m build

# Check
twine check dist/*
```

### Test on TestPyPI

```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ maia
```

### Upload to PyPI

```bash
twine upload dist/*
```

### Build Executables

```bash
# Install PyInstaller
pip install pyinstaller

# Linux
pyinstaller --onefile --name maia-linux \
  --add-data "src/maia:maia" \
  --hidden-import=nemo \
  --hidden-import=nemo.collections.asr \
  --hidden-import=PySide6 \
  src/maia/__main__.py

# macOS (on macOS)
pyinstaller --onefile --name maia-macos \
  --add-data "src/maia:maia" \
  --hidden-import=nemo \
  --hidden-import=nemo.collections.asr \
  --hidden-import=PySide6 \
  src/maia/__main__.py

# Windows (on Windows)
pyinstaller --onefile --name maia-windows.exe \
  --add-data "src/maia;maia" \
  --hidden-import=nemo \
  --hidden-import=nemo.collections.asr \
  --hidden-import=PySide6 \
  src/maia/__main__.py
```

## Version Numbering

Follow Semantic Versioning (semver.org):

- **MAJOR** version (x.0.0): Incompatible API changes
- **MINOR** version (0.x.0): New features, backwards compatible
- **PATCH** version (0.0.x): Bug fixes, backwards compatible

Examples:
- `0.1.0` → `0.1.1`: Bug fix
- `0.1.1` → `0.2.0`: New feature
- `0.9.0` → `1.0.0`: First stable release

## Pre-releases

For alpha/beta releases:

```bash
# Alpha
git tag -a v0.2.0-alpha.1 -m "Release v0.2.0-alpha.1"

# Beta
git tag -a v0.2.0-beta.1 -m "Release v0.2.0-beta.1"

# Release candidate
git tag -a v0.2.0-rc.1 -m "Release v0.2.0-rc.1"
```

## Hotfix Process

For urgent bug fixes:

1. Create hotfix branch from main: `git checkout -b hotfix/0.1.1`
2. Fix the bug
3. Update version to 0.1.1
4. Commit, tag, and push
5. Merge back to main

## Post-Release

After a successful release:

1. Announce on social media / forums
2. Update documentation if needed
3. Close related GitHub issues
4. Plan next release

## Troubleshooting

### Build Fails

- Check all dependencies are installed
- Verify tests pass locally
- Check GitHub Actions logs

### PyPI Upload Fails

- Verify API token is correct
- Check version doesn't already exist on PyPI
- Ensure package builds correctly: `twine check dist/*`

### Executables Don't Work

- Test on target platform before release
- Check all dependencies are bundled
- Verify hidden imports are specified
