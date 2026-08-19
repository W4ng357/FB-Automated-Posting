#!/usr/bin/env python3
"""One-command release script to bump version, tag, and push to GitHub."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT_DIR / "src" / "version.py"


def update_version_file(new_version: str) -> None:
    content = VERSION_FILE.read_text(encoding="utf-8")
    clean_v = new_version.lstrip("vV")
    updated = re.sub(
        r'APP_VERSION = "[^"]+"',
        f'APP_VERSION = "{clean_v}"',
        content,
    )
    VERSION_FILE.write_text(updated, encoding="utf-8")
    print(f"✓ Đã cập nhật APP_VERSION = \"{clean_v}\" trong {VERSION_FILE.relative_to(ROOT_DIR)}")


def run_command(cmd: list[str]) -> bool:
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT_DIR)
    return result.returncode == 0


def main() -> int:
    if len(sys.argv) < 2:
        print("Sử dụng: python scripts/release.py <version> [ghi_chú]")
        print("Ví dụ:   python scripts/release.py 1.0.1 \"Cập nhật tìm kiếm và giá\"")
        return 1

    raw_version = sys.argv[1].strip()
    tag_name = f"v{raw_version.lstrip('vV')}"
    message = sys.argv[2].strip() if len(sys.argv) > 2 else f"Release {tag_name}"

    print(f"=== Chuẩn bị phát hành {tag_name} ===")
    update_version_file(raw_version)

    # 1. Git Add & Commit
    run_command(["git", "add", "-A"])
    commit_ok = run_command(["git", "commit", "-m", f"Release {tag_name}: {message}"])
    if not commit_ok:
        print("⚠️ Không có thay đổi mới để commit, tiếp tục gắn tag...")

    # 2. Git Tag
    tag_ok = run_command(["git", "tag", "-a", tag_name, "-m", message])
    if not tag_ok:
        print(f"❌ Không thể tạo tag {tag_name}. Có thể tag đã tồn tại.")
        return 1

    # 3. Git Push
    print(f"\n🚀 Đang đẩy commit và tag {tag_name} lên GitHub...")
    push_ok = run_command(["git", "push", "origin", "HEAD", "--tags"])
    if not push_ok:
        print("❌ Push thất bại. Kiểm tra kết nối mạng và quyền push git.")
        return 1

    print(f"\n✨ THÀNH CÔNG! Tag {tag_name} đã được đẩy lên GitHub.")
    print("GitHub Actions sẽ tự động đóng gói 'app_code.zip' và tạo GitHub Release sau vài giây.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
