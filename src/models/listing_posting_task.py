from dataclasses import dataclass, field

from models.group_target import GroupTarget


@dataclass
class ListingPostingTask:
    listing_id: str
    listing_title: str
    group_targets: list[GroupTarget]
    group_names: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.listing_id.strip():
            raise ValueError("Listing id cannot be empty")
        if not self.listing_title.strip():
            raise ValueError("Listing title cannot be empty")
        if not self.group_targets:
            raise ValueError("A posting task needs at least one group")

    @property
    def total_attempts(self) -> int:
        return sum(
            target.target_count
            for target in self.group_targets
        )

    def group_name_for(self, url: str) -> str:
        return self.group_names.get(url, url)

    def fresh_copy(self) -> "ListingPostingTask":
        return ListingPostingTask(
            listing_id=self.listing_id,
            listing_title=self.listing_title,
            group_targets=[
                GroupTarget(
                    url=target.url,
                    target_count=target.target_count,
                )
                for target in self.group_targets
            ],
            group_names=dict(self.group_names),
        )

