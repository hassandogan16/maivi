# Contributing to Maia

Thank you for your interest in contributing to Maia! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/maia.git`
3. Create a new branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test your changes
6. Commit with a descriptive message
7. Push to your fork
8. Create a Pull Request

## Development Setup

```bash
# Clone the repository
git clone https://github.com/maximerivest/maia.git
cd maia

# Install in development mode with dev dependencies
pip install -e .[dev]

# Run tests
pytest

# Run linters
black src/
isort src/
flake8 src/
```

## Code Style

- Follow PEP 8 guidelines
- Use Black for code formatting (line length: 100)
- Use isort for import sorting
- Add type hints where appropriate
- Write docstrings for all public functions and classes

## Testing

- Write tests for all new features
- Ensure all tests pass before submitting a PR
- Aim for >80% code coverage
- Use pytest for testing

## Pull Request Guidelines

- Keep PRs focused on a single feature or bug fix
- Update documentation as needed
- Add tests for new functionality
- Ensure all CI checks pass
- Reference any related issues in the PR description

## Reporting Issues

When reporting issues, please include:
- Your operating system and version
- Python version
- Maia version
- Steps to reproduce the issue
- Expected vs actual behavior
- Any error messages or logs

## Feature Requests

We welcome feature requests! Please:
- Check if the feature has already been requested
- Clearly describe the feature and its use case
- Explain why it would be valuable to other users

## Code of Conduct

Be respectful and constructive in all interactions. We're all here to make Maia better!

## Questions?

Feel free to open an issue for any questions about contributing.
