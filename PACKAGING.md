# FB Poster — Documentation for Packaging & Distribution

This guide covers building, packaging, migrating development data, and running **FB Poster** as standalone executables for Linux and Windows.

---

## Packaging Architecture Overview

FB Poster separates **Static/Read-Only Application Resources** from **Persistent User Data**:

### 1. Static Application Resources (Bundled into Executable)
- `src/gui/styles/dark.qss`
- Qt UI components & icons
- Playwright Chromium binaries (`playwright/driver/package/.local-browsers`)

### 2. Persistent User Data (Stored in User Home Directory)
- **Linux Location:** `~/.local/share/FBPoster`
- **Windows Location:** `%LOCALAPPDATA%\FBPoster`

Directory Structure:
```text
<APP_DATA_DIR>/
├── data/
│   ├── listings.json
│   ├── groups.json
│   ├── accounts.json
│   ├── listings/          (listing photo assets)
│   ├── groups/            (group avatar assets)
│   ├── accounts/          (account avatar assets)
│   └── drafts/            (temporary form drafts)
├── browser_sessions/      (Chromium session profiles)
├── logs/                  (app.log, native-crash.log)
└── temp/
```

**Key Benefit:** Replacing or updating the executable **never deletes** your saved listings, groups, account sessions, or logs.

---

## BUILD ON LINUX

### Prerequisites
- Operating System: Linux (x86_64)
- Python 3.10+
- Virtual environment (`.venv`) with dependencies installed from `requirements.txt`

### 1. Prepare Environment & Install Chromium
Open a terminal in the project root:
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Install build dependencies
pip install pyinstaller

# Download Playwright Chromium directly into Python package directory
export PLAYWRIGHT_BROWSERS_PATH=0
python -m playwright install chromium
```

### 2. Run Linux Build Script
Run the automated build script:
```bash
./scripts/build_linux.sh
```

Flags available:
- `./scripts/build_linux.sh --onedir` : Builds `dist/FBPoster/` directory bundle
- `./scripts/build_linux.sh --onefile`: Builds `dist/FBPoster` single executable file

### 3. Output Executable Locations
- **Directory Mode:** `dist/FBPoster/FBPoster`
- **Single Executable:** `dist/FBPoster`

### 4. Test Linux Build
Launch the single standalone executable:
```bash
./dist/FBPoster
```

---

## BUILD ON WINDOWS

### Prerequisites
- Operating System: Windows 10 / 11 (x64)
- Python 3.10+
- PowerShell

### 1. Prepare Environment & Install Chromium
Open PowerShell as a normal user in the project root:
```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install PyInstaller
pip install pyinstaller

# Download Playwright Chromium in package directory
$env:PLAYWRIGHT_BROWSERS_PATH = "0"
python -m playwright install chromium
```

### 2. Run Windows Build Script
Run the automated PowerShell build script:
```powershell
.\scripts\build_windows.ps1
```

Flags available:
- `.\scripts\build_windows.ps1 -Onedir`  : Builds `dist\FBPoster\` directory bundle
- `.\scripts\build_windows.ps1 -Onefile` : Builds `dist\FBPoster.exe` single executable

### 3. Output Executable Locations
- **Directory Mode:** `dist\FBPoster\FBPoster.exe`
- **Single Executable:** `dist\FBPoster.exe`

---

## MIGRATING EXISTING DEVELOPMENT DATA

If you already have listings, groups, or browser sessions created during local development (`data/`, `browser_sessions/`), you can migrate them into your persistent application data directory:

### Run Migration Utility
```bash
# Linux
python scripts/migrate_dev_data.py

# Windows
python scripts\migrate_dev_data.py
```

Use `-f` or `--force` to skip confirmation prompts.

---

## USING THE BUILT APPLICATION (FOR END USERS)

End users do **NOT** need to install Python, PySide6, Playwright, or Chromium.

### Linux:
1. Copy or download `FBPoster`.
2. Ensure executable permissions: `chmod +x FBPoster`
3. Double click or run `./FBPoster` in terminal.

### Windows:
1. Copy or download `FBPoster.exe`.
2. Double-click `FBPoster.exe` to launch directly. No console window will appear.

---

## COMMON TROUBLESHOOTING

- **Logs Location:** If an unexpected crash occurs, check `app.log` or `native-crash.log` in `<APP_DATA_DIR>/logs/`.
- **Open Data Directory from App:** Go to **Tài khoản Facebook** -> Click **Mở thư mục dữ liệu** in the bottom left corner.
