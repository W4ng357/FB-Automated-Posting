from dataclasses import dataclass

from models.listing_posting_task import ListingPostingTask


@dataclass
class AccountPostingPlan:
    account_name: str
    tasks: list[ListingPostingTask]

    def __post_init__(self) -> None:
        if not self.account_name.strip():
            raise ValueError("Account name cannot be empty")
        if not self.tasks:
            raise ValueError("An account plan needs at least one task")

    @property
    def total_attempts(self) -> int:
        return sum(task.total_attempts for task in self.tasks)

    def fresh_copy(self) -> "AccountPostingPlan":
        return AccountPostingPlan(
            account_name=self.account_name,
            tasks=[task.fresh_copy() for task in self.tasks],
        )

