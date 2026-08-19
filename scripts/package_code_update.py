#!/usr/bin/env python3
"""Package the lightweight source code bundle into dist/app_code.zip."""

from __future__ import annotations

import os
import sys
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
DIST_DIR = ROOT_DIR / "dist"
OUTPUT_ZIP = DIST_DIR / "app_code.zip"

EXCLUDE_PATTERNS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".DS_Store",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".log",
}


def should_include_file(file_path: Path) -> bool:
    for part in file_path.parts:
        if part in EXCLUDE_PATTERNS or part.startswith("."):
            return False
    if file_path.suffix in EXCLUDE_EXTENSIONS:
        return False
    # Exclude unit tests from production update zip to keep it minimal
    if file_path.name.endswith("_test.py"):
        return False
    return True


def package_code() -> Path:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    if OUTPUT_ZIP.exists():
        OUTPUT_ZIP.unlink()

    count = 0
    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(SRC_DIR):
            root_path = Path(root)
            dirs[:] = [d for d in dirs if d not in EXCLUDE_PATTERNS and not d.startswith(".")]

            for file_name in files:
                file_path = root_path / file_name
                if should_include_file(file_path):
                    # Store relative to src/
                    arcname = file_path.relative_to(SRC_DIR)
                    zf.write(file_path, arcname)
                    count += 1

    size_kb = OUTPUT_ZIP.stat().st_size / 1024
    print(f"✓ Đã đóng gói thành công {count} tệp vào: {OUTPUT_ZIP} ({size_kb:.1f} KB)")
    return OUTPUT_ZIP


if __name__ == "__main__":
    package_code()
