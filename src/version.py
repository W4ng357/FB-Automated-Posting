"""Application version and GitHub release metadata."""

from __future__ import annotations

import re

APP_VERSION = "1.0.0"
APP_NAME = "FBPoster"
GITHUB_REPO = "W4ng357/FB-Automated-Posting"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_RELEASES_PAGE = f"https://github.com/{GITHUB_REPO}/releases"


def parse_version(version_str: str) -> tuple[int, ...]:
    """Extract numeric components from version string (e.g. 'v1.2.3' -> (1, 2, 3))."""
    cleaned = version_str.strip().lstrip("vV")
    match = re.match(r"^(\d+(?:\.\d+)*)", cleaned)
    if not match:
        return (0,)
    return tuple(int(part) for part in match.group(1).split("."))


def is_newer_version(remote_version: str, local_version: str = APP_VERSION) -> bool:
    """Return True if remote_version is strictly newer than local_version."""
    remote_tuple = parse_version(remote_version)
    local_tuple = parse_version(local_version)

    max_len = max(len(remote_tuple), len(local_tuple))
    remote_padded = remote_tuple + (0,) * (max_len - len(remote_tuple))
    local_padded = local_tuple + (0,) * (max_len - len(local_tuple))

    return remote_padded > local_padded
