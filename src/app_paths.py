"""Centralized path management for FB Poster.

Handles persistent user data directory (QStandardPaths) and static resource
resolution for both dev environment and PyInstaller frozen executable.
"""

from __future__ import annotations

import os
import sys

from pathlib import Path

from PySide6.QtCore import QCoreApplication, QStandardPaths

APP_NAME = "FBPoster"
ORG_NAME = "FBPoster"


def get_app_data_dir() -> Path:
    """Return the persistent, user-writable application data directory.

    Uses QStandardPaths.AppLocalDataLocation.
    - Linux: ~/.local/share/FBPoster
    - Windows: %LOCALAPPDATA%\\FBPoster
    """
    if QCoreApplication.instance() is None:
        QCoreApplication.setOrganizationName(ORG_NAME)
        QCoreApplication.setApplicationName(APP_NAME)

    path_str = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppLocalDataLocation
    )
    if path_str:
        res = Path(path_str)
        # Simplify double FBPoster folder if present (e.g. FBPoster/FBPoster -> FBPoster)
        if res.name == APP_NAME and res.parent.name == ORG_NAME:
            res = res.parent
        return res

    if sys.platform == "win32":
        base = Path(
            os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
        )
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(
            os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
        )
    return base / APP_NAME


def get_resource_path(relative_path: str | Path) -> Path:
    """Get absolute path to static application resources.

    Supports normal source execution and PyInstaller frozen execution (_MEIPASS).
    """
    rel = Path(relative_path)
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        # Root of project directory
        base = Path(__file__).resolve().parents[1]

    return (base / rel).resolve()


APP_DATA_DIR = get_app_data_dir()
DATA_DIR = APP_DATA_DIR / "data"

LISTINGS_FILE = DATA_DIR / "listings.json"
LISTINGS_DIR = DATA_DIR / "listings"

GROUPS_FILE = DATA_DIR / "groups.json"
GROUPS_DIR = DATA_DIR / "groups"

ACCOUNTS_FILE = DATA_DIR / "accounts.json"
ACCOUNTS_DIR = DATA_DIR / "accounts"

DRAFTS_DIR = DATA_DIR / "drafts"

BROWSER_SESSIONS_DIR = APP_DATA_DIR / "browser_sessions"
LOGS_DIR = APP_DATA_DIR / "logs"
TEMP_DIR = APP_DATA_DIR / "temp"

UPDATES_DIR = APP_DATA_DIR / "updates"
CURRENT_UPDATE_DIR = UPDATES_DIR / "current"
TEMP_UPDATE_DIR = UPDATES_DIR / "temp"


def ensure_app_paths() -> None:
    """Create all persistent directories and initial empty JSON files if missing."""
    for directory in (
        APP_DATA_DIR,
        DATA_DIR,
        LISTINGS_DIR,
        GROUPS_DIR,
        ACCOUNTS_DIR,
        DRAFTS_DIR,
        BROWSER_SESSIONS_DIR,
        LOGS_DIR,
        TEMP_DIR,
        UPDATES_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    for json_file in (LISTINGS_FILE, GROUPS_FILE, ACCOUNTS_FILE):
        if not json_file.exists():
            json_file.write_text("[]\n", encoding="utf-8")


def setup_playwright_env() -> None:
    """Configure Playwright environment variables for bundled browsers when frozen."""
    if getattr(sys, "frozen", False):
        bundled_browsers = (
            get_resource_path("playwright")
            / "driver"
            / "package"
            / ".local-browsers"
        )
        if bundled_browsers.is_dir():
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(bundled_browsers)
