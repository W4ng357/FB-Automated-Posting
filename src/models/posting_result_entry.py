from dataclasses import dataclass, field
from datetime import datetime

from models.post_result import PostResult


@dataclass(frozen=True)
class PostingResultEntry:
    account_name: str
    listing_id: str
    listing_title: str
    result: PostResult
    posted_at: datetime = field(
        default_factory=lambda: datetime.now().astimezone()
    )
