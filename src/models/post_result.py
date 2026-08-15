from dataclasses import dataclass


@dataclass
class PostResult:
    group_url: str
    group_name: str | None
    success: bool
    post_url: str | None = None
    error: str | None = None