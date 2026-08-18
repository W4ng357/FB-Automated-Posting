from dataclasses import dataclass


@dataclass
class GroupTarget:
    url: str
    target_count: int
    posted_count: int = 0
    failed: bool = False
    attempted_count: int = 0

    def __post_init__(self) -> None:
        if self.target_count <= 0:
            raise ValueError(
                "target_count must be greater than 0"
            )

        if self.posted_count < 0:
            raise ValueError(
                "posted_count cannot be negative"
            )

        if self.posted_count > self.target_count:
            raise ValueError(
                "posted_count cannot exceed target_count"
            )

        if self.attempted_count < 0:
            raise ValueError(
                "attempted_count cannot be negative"
            )

        # Keep objects created by the older API compatible: before
        # attempted_count existed, posted_count was the only progress value.
        if self.attempted_count == 0 and self.posted_count > 0:
            self.attempted_count = self.posted_count

        if self.attempted_count < self.posted_count:
            raise ValueError(
                "attempted_count cannot be less than posted_count"
            )

        if self.attempted_count > self.target_count:
            raise ValueError(
                "attempted_count cannot exceed target_count"
            )

    @property
    def remaining(self) -> int:
        return self.target_count - self.attempted_count

    @property
    def active(self) -> bool:
        return self.remaining > 0 and not self.failed

    def mark_posted(self) -> None:
        if self.remaining <= 0:
            raise ValueError(
                "Target post count already reached"
            )

        self.attempted_count += 1
        self.posted_count += 1

    def mark_attempt_failed(self) -> None:
        if self.remaining <= 0:
            raise ValueError(
                "Target attempt count already reached"
            )

        self.attempted_count += 1

    def mark_failed(self) -> None:
        self.failed = True
