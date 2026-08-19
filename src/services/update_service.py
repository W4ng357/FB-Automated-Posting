"""Service for checking, downloading, and applying application updates from GitHub Releases."""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QProcess, QCoreApplication

from app_paths import (
    CURRENT_UPDATE_DIR,
    TEMP_UPDATE_DIR,
    UPDATES_DIR,
)
from version import (
    APP_VERSION,
    GITHUB_API_URL,
    is_newer_version,
)

logger = logging.getLogger(__name__)


@dataclass
class ReleaseInfo:
    version: str
    name: str
    body: str
    published_at: str
    html_url: str
    code_zip_url: str | None = None
    zipball_url: str | None = None
    file_size: int = 0


class UpdateService:
    """Handles checking, downloading and applying lightweight code updates."""

    def __init__(self, api_url: str = GITHUB_API_URL) -> None:
        self.api_url = api_url

    def get_current_installed_version(self) -> str:
        """Return version of active updated code if present, else base APP_VERSION."""
        manifest_file = CURRENT_UPDATE_DIR / "update_manifest.json"
        if manifest_file.is_file():
            try:
                data = json.loads(manifest_file.read_text(encoding="utf-8"))
                return data.get("version", APP_VERSION)
            except Exception:
                pass
        return APP_VERSION

    def check_for_updates(self, timeout: float = 8.0) -> ReleaseInfo | None:
        """Query GitHub Releases API to check if a newer version is available."""
        current_version = self.get_current_installed_version()
        req = urllib.request.Request(
            self.api_url,
            headers={
                "User-Agent": f"FBPoster-App/{current_version}",
                "Accept": "application/vnd.github.v3+json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status != 200:
                    return None
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as err:
            logger.warning("Could not check for updates: %s", err)
            return None

        tag_name = data.get("tag_name", "").strip()
        if not tag_name:
            return None

        if not is_newer_version(tag_name, current_version):
            return None

        # Find app_code.zip asset if present
        code_zip_url = None
        file_size = 0
        for asset in data.get("assets", []):
            name = asset.get("name", "")
            if name.lower() == "app_code.zip" or name.lower().endswith(".zip"):
                code_zip_url = asset.get("browser_download_url")
                file_size = asset.get("size", 0)
                if name.lower() == "app_code.zip":
                    break

        zipball_url = data.get("zipball_url")

        return ReleaseInfo(
            version=tag_name,
            name=data.get("name") or tag_name,
            body=data.get("body") or "Bản cập nhật mới.",
            published_at=data.get("published_at") or "",
            html_url=data.get("html_url") or "",
            code_zip_url=code_zip_url,
            zipball_url=zipball_url,
            file_size=file_size,
        )

    def download_and_apply_update(
        self,
        release: ReleaseInfo,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> bool:
        """Download update zip and extract into CURRENT_UPDATE_DIR atomically."""
        download_url = release.code_zip_url or release.zipball_url
        if not download_url:
            raise ValueError("Không tìm thấy đường dẫn tải bản cập nhật.")

        UPDATES_DIR.mkdir(parents=True, exist_ok=True)
        TEMP_UPDATE_DIR.mkdir(parents=True, exist_ok=True)

        download_target = TEMP_UPDATE_DIR / f"update_{release.version}.zip"
        staging_dir = TEMP_UPDATE_DIR / f"staging_{release.version}"

        try:
            # 1. Download file with progress report
            req = urllib.request.Request(
                download_url,
                headers={"User-Agent": f"FBPoster-Updater/{APP_VERSION}"},
            )
            with urllib.request.urlopen(req, timeout=30.0) as resp, open(download_target, "wb") as out_file:
                total_size = int(resp.headers.get("Content-Length", 0)) or release.file_size
                downloaded = 0
                chunk_size = 64 * 1024

                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total_size)

            # 2. Extract and validate zip
            if staging_dir.exists():
                shutil.rmtree(staging_dir, ignore_errors=True)
            staging_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(download_target, "r") as zf:
                zf.extractall(staging_dir)

            # Determine where the root source code is in the extracted folder
            final_src_dir = staging_dir
            # If zip contains a single top-level folder (like GitHub zipball `repo-v1.0.1/src`)
            items = [item for item in staging_dir.iterdir() if not item.name.startswith(".")]
            if len(items) == 1 and items[0].is_dir():
                inner_dir = items[0]
                if (inner_dir / "src").is_dir():
                    final_src_dir = inner_dir / "src"
                else:
                    final_src_dir = inner_dir
            elif (staging_dir / "src").is_dir():
                final_src_dir = staging_dir / "src"

            # 3. Write update manifest
            manifest = {
                "version": release.version,
                "installed_at": datetime.now().isoformat(),
                "release_name": release.name,
            }
            manifest_path = final_src_dir / "update_manifest.json"
            manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

            # 4. Atomic swap to CURRENT_UPDATE_DIR
            if CURRENT_UPDATE_DIR.exists():
                old_backup = UPDATES_DIR / "previous_backup"
                if old_backup.exists():
                    shutil.rmtree(old_backup, ignore_errors=True)
                CURRENT_UPDATE_DIR.rename(old_backup)

            shutil.copytree(final_src_dir, CURRENT_UPDATE_DIR)
            return True

        finally:
            # Clean up temp files
            if download_target.exists():
                try:
                    download_target.unlink()
                except Exception:
                    pass
            if staging_dir.exists():
                shutil.rmtree(staging_dir, ignore_errors=True)

    @staticmethod
    def restart_application() -> None:
        """Relaunch application process and exit current instance."""
        executable = sys.executable
        args = sys.argv
        if getattr(sys, "frozen", False):
            # In frozen app, sys.executable is the binary path
            QProcess.startDetached(executable, args[1:])
        else:
            # In dev mode, sys.executable is python, args is [app.py, ...]
            QProcess.startDetached(executable, args)

        app_instance = QCoreApplication.instance()
        if app_instance is not None:
            app_instance.quit()
        sys.exit(0)
