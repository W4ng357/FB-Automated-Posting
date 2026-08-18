import re

from dataclasses import dataclass
from pathlib import Path


_FACEBOOK_TITLE_SUFFIX = re.compile(
    r"\s*(?:\||-|–|—)\s*Facebook\s*$",
    re.IGNORECASE,
)
_NOTIFICATION_PREFIX = re.compile(r"^\(\d+\)\s*")
_INVALID_FACEBOOK_NAMES = {
    "facebook",
    "đăng nhập facebook",
    "log into facebook",
    "profile",
    "trang cá nhân",
    "trang cá nhân của bạn",
    "your profile",
    "meta ai",
    "notifications",
    "thông báo",
    "posts",
    "bài viết",
}


def normalize_facebook_name(value: str) -> str:
    candidate = _NOTIFICATION_PREFIX.sub("", value.strip())
    candidate = _FACEBOOK_TITLE_SUFFIX.sub("", candidate).strip()
    if candidate.casefold() in _INVALID_FACEBOOK_NAMES:
        return ""
    return candidate


@dataclass(frozen=True)
class FacebookAccount:
    id: str
    facebook_name: str = ""
    alias: str = ""
    profile_url: str = ""
    avatar_path: str | None = None
    session_verified: bool = False
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        account_id = self.id.strip()
        if (
            not account_id
            or account_id in {".", ".."}
            or Path(account_id).name != account_id
        ):
            raise ValueError(f"Invalid Facebook account ID: {self.id!r}")
        clean_facebook_name = normalize_facebook_name(self.facebook_name)
        if clean_facebook_name != self.facebook_name:
            object.__setattr__(
                self,
                "facebook_name",
                clean_facebook_name,
            )

    @property
    def display_name(self) -> str:
        return (
            self.alias.strip()
            or normalize_facebook_name(self.facebook_name)
            or self.id
        )

    @property
    def is_synced(self) -> bool:
        return bool(normalize_facebook_name(self.facebook_name))

    @property
    def identity_detail(self) -> str:
        facebook_name = normalize_facebook_name(self.facebook_name)
        if self.alias.strip() and facebook_name:
            return facebook_name
        if self.is_synced:
            return "Đã lấy tên và ảnh đại diện từ Facebook"
        return "Chưa lấy thông tin từ Facebook"
