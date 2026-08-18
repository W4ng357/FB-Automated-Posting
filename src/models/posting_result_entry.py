from dataclasses import dataclass

from models.post_result import PostResult


@dataclass(frozen=True)
class PostingResultEntry:
    account_name: str
    listing_id: str
    listing_title: str
    result: PostResult

