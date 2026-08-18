from dataclasses import dataclass


@dataclass(frozen=True)
class PostingProgress:
    completed: int
    total: int
    current_group_name: str | None
    next_group_name: str | None
    current_listing_title: str | None
    message: str
    next_listing_title: str | None = None
    attempted: int = 0
    failed: int = 0
    skipped: int = 0
    remaining: int = 0
    finished: bool = False
    stopped: bool = False
