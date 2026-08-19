#!/usr/bin/env bash
set -e

# Linux Build Script for FB Poster Standalone Executable

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "=== FB Poster Linux Build ==="

# 1. Locate Python environment
if [ -d ".venv" ]; then
    PYTHON_CMD="$PROJECT_ROOT/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
else
    echo "Error: Python binary not found." >&2
    exit 1
fi

echo "Using Python: $($PYTHON_CMD --version)"

# 2. Verify PyInstaller is installed
if ! $PYTHON_CMD -c "import PyInstaller" &>/dev/null; then
    echo "Installing PyInstaller..."
    $PYTHON_CMD -m pip install pyinstaller
fi

# 3. Set Playwright bundled browsers path and install Chromium
echo "Ensuring Playwright Chromium is installed in package directory..."
export PLAYWRIGHT_BROWSERS_PATH=0
$PYTHON_CMD -m playwright install chromium

# 4. Clean previous build artifacts
echo "Cleaning previous build artifacts..."
rm -rf build dist

# 5. Build distributions using FBPoster.spec
echo "Building distributions from FBPoster.spec..."
$PYTHON_CMD -m PyInstaller --noconfirm FBPoster.spec

if [ -f "dist/FBPoster/FBPoster" ]; then
    chmod +x dist/FBPoster/FBPoster
    echo "✓ ONEDIR package ready: $PROJECT_ROOT/dist/FBPoster/FBPoster"
fi

if [ -f "dist/FBPoster-standalone" ]; then
    chmod +x dist/FBPoster-standalone
    echo "✓ ONEFILE executable ready: $PROJECT_ROOT/dist/FBPoster-standalone"
fi

echo "=== Linux Build Successful ==="
