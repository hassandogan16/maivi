#!/bin/bash
# Script to add GitHub Actions workflows after granting workflow scope

echo "🔐 Step 1: Re-authenticate with workflow scope..."
echo "Run this command and follow the prompts:"
echo ""
echo "  gh auth refresh -h github.com -s workflow"
echo ""
read -p "Press Enter after you've authenticated..."

echo ""
echo "📦 Step 2: Adding workflows and pushing..."
git add .github/workflows/
git commit -m "Add GitHub Actions workflows for CI/CD

- PyPI release workflow (automated on tag push)
- Executable builds (Linux, macOS, Windows)
- CI/CD tests workflow

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
"

git push

echo ""
echo "✅ Done! Check your GitHub Actions: https://github.com/MaximeRivest/maia/actions"
