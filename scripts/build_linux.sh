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

# Parse build target argument (default: both onedir and onefile)
BUILD_ONEDIR=true
BUILD_ONEFILE=true

if [ "$1" == "--onedir" ]; then
    BUILD_ONEFILE=false
elif [ "$1" == "--onefile" ]; then
    BUILD_ONEDIR=false
fi

# 5. Build ONEDIR directory package
if [ "$BUILD_ONEDIR" = true ]; then
    echo "Building ONEDIR distribution (dist/FBPoster/)..."
    $PYTHON_CMD -m PyInstaller --noconfirm FBPoster.spec
    chmod +x dist/FBPoster/FBPoster
    echo "✓ ONEDIR build completed: $PROJECT_ROOT/dist/FBPoster/FBPoster"
fi

# 6. Build ONEFILE standalone executable
if [ "$BUILD_ONEFILE" = true ]; then
    echo "Building ONEFILE standalone executable (dist/FBPoster)..."
    $PYTHON_CMD -m PyInstaller --noconfirm --onefile --windowed \
        --name FBPoster \
        --paths src \
        --add-data "src/gui/styles/dark.qss:src/gui/styles" \
        src/gui/app.py

    # Rename if necessary or ensure executable permissions
    chmod +x dist/FBPoster
    echo "✓ ONEFILE build completed: $PROJECT_ROOT/dist/FBPoster"
fi

echo "=== Linux Build Successful ==="
