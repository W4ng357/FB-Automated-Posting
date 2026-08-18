#!/usr/bin/env python3
"""Development Data Migration Utility for FB Poster.

Safely copies local development data (data/, browser_sessions/) from the
project root into the persistent user application data directory (APP_DATA_DIR).
"""

from __future__ import annotations

import argparse
import shutil
import sys

from pathlib import Path

# Ensure src is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from app_paths import (
    ACCOUNTS_DIR,
    ACCOUNTS_FILE,
    APP_DATA_DIR,
    BROWSER_SESSIONS_DIR,
    DATA_DIR,
    DRAFTS_DIR,
    GROUPS_DIR,
    GROUPS_FILE,
    LISTINGS_DIR,
    LISTINGS_FILE,
    ensure_app_paths,
)


def migrate_dev_data(force: bool = False) -> None:
    """Migrate local development data into APP_DATA_DIR."""
    ensure_app_paths()

    dev_data_dir = PROJECT_ROOT / "data"
    dev_sessions_dir = PROJECT_ROOT / "browser_sessions"

    print("=== FB Poster Data Migration ===")
    print(f"Source dev directory: {PROJECT_ROOT}")
    print(f"Target app data dir: {APP_DATA_DIR}\n")

    items_to_migrate: list[tuple[Path, Path]] = []

    # JSON files
    for dev_file, target_file in [
        (dev_data_dir / "listings.json", LISTINGS_FILE),
        (dev_data_dir / "groups.json", GROUPS_FILE),
        (dev_data_dir / "accounts.json", ACCOUNTS_FILE),
    ]:
        if dev_file.is_file():
            items_to_migrate.append((dev_file, target_file))

    # Asset directories
    for dev_dir, target_dir in [
        (dev_data_dir / "listings", LISTINGS_DIR),
        (dev_data_dir / "groups", GROUPS_DIR),
        (dev_data_dir / "accounts", ACCOUNTS_DIR),
        (dev_data_dir / "drafts", DRAFTS_DIR),
        (dev_sessions_dir, BROWSER_SESSIONS_DIR),
    ]:
        if dev_dir.is_dir():
            items_to_migrate.append((dev_dir, target_dir))

    if not items_to_migrate:
        print("No local development data found in project root to migrate.")
        return

    print("Found the following development items to migrate:")
    for src, dst in items_to_migrate:
        print(f"  - {src.relative_to(PROJECT_ROOT)} -> {dst}")

    if not force:
        print("\nWARNING: This will copy development data into your app data directory.")
        answer = input("Proceed with migration? [y/N]: ").strip().lower()
        if answer not in ("y", "yes"):
            print("Migration cancelled.")
            return

    print("\nCopying data...")
    for src, dst in items_to_migrate:
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"  ✓ Copied file: {src.name}")
        elif src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            for item in src.iterdir():
                target_item = dst / item.name
                if item.is_file():
                    shutil.copy2(item, target_item)
                elif item.is_dir():
                    if target_item.exists():
                        shutil.rmtree(target_item)
                    shutil.copytree(item, target_item)
            print(f"  ✓ Copied directory: {src.name}")

    print(f"\n✓ Migration completed successfully! Data is ready in: {APP_DATA_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate local development data into FB Poster user data directory."
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Overwrite existing data without confirmation prompt.",
    )
    args = parser.parse_args()
    migrate_dev_data(force=args.force)


if __name__ == "__main__":
    main()
