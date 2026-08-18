# PowerShell Build Script for FB Poster Windows Standalone Executable
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Host "=== FB Poster Windows Build ===" -ForegroundColor Cyan

# 1. Locate Python executable
$PythonCmd = "$ProjectRoot\.venv\Scripts\python.exe"
if (-not (Test-Path $PythonCmd)) {
    $PythonCmd = "python"
}

Write-Host "Using Python: $PythonCmd"

# 2. Ensure PyInstaller is installed
& $PythonCmd -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing PyInstaller..."
    & $PythonCmd -m pip install pyinstaller
}

# 3. Set Playwright bundled browsers path and install Chromium
Write-Host "Ensuring Playwright Chromium is installed in package directory..."
$env:PLAYWRIGHT_BROWSERS_PATH = "0"
& $PythonCmd -m playwright install chromium

# 4. Clean previous build artifacts
Write-Host "Cleaning previous build artifacts..."
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }

# Parse arguments
$BuildOnedir = $true
$BuildOnefile = $true

if ($args -contains "-Onedir") {
    $BuildOnefile = $false
} elseif ($args -contains "-Onefile") {
    $BuildOnedir = $false
}

# 5. Build ONEDIR package
if ($BuildOnedir) {
    Write-Host "Building ONEDIR distribution (dist\FBPoster\)..." -ForegroundColor Yellow
    & $PythonCmd -m PyInstaller --noconfirm FBPoster.spec
    Write-Host "✓ ONEDIR build completed: $ProjectRoot\dist\FBPoster\FBPoster.exe" -ForegroundColor Green
}

# 6. Build ONEFILE executable
if ($BuildOnefile) {
    Write-Host "Building ONEFILE standalone executable (dist\FBPoster.exe)..." -ForegroundColor Yellow
    & $PythonCmd -m PyInstaller --noconfirm --onefile --windowed `
        --name FBPoster `
        --paths src `
        --add-data "src/gui/styles/dark.qss;src/gui/styles" `
        src/gui/app.py

    Write-Host "✓ ONEFILE build completed: $ProjectRoot\dist\FBPoster.exe" -ForegroundColor Green
}

Write-Host "=== Windows Build Successful ===" -ForegroundColor Cyan
