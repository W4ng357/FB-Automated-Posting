from dataclasses import dataclass


@dataclass
class GroupTarget:
    url: str
    target_count: int
    posted_count: int = 0

    def __post_init__(self) -> None:
        if self.target_count <= 0:
            raise ValueError(
                "target_count must be greater than 0"
            )

    @property
    def remaining(self) -> int:
        return self.target_count - self.posted_count

    def mark_posted(self) -> None:
        if self.remaining <= 0:
            raise ValueError(
                "Target post count already reached"
            )

        self.posted_count += 1