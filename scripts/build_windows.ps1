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

# 5. Build distributions using FBPoster.spec
Write-Host "Building distributions from FBPoster.spec..." -ForegroundColor Yellow
& $PythonCmd -m PyInstaller --noconfirm FBPoster.spec

if (Test-Path "dist\FBPoster\FBPoster.exe") {
    Write-Host "✓ ONEDIR package ready: $ProjectRoot\dist\FBPoster\FBPoster.exe" -ForegroundColor Green
}

if (Test-Path "dist\FBPoster-standalone.exe") {
    Write-Host "✓ ONEFILE executable ready: $ProjectRoot\dist\FBPoster-standalone.exe" -ForegroundColor Green
}

Write-Host "=== Windows Build Successful ===" -ForegroundColor Cyan
