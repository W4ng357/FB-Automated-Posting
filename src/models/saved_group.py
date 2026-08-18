from dataclasses import dataclass


@dataclass(frozen=True)
class SavedGroup:
    id: str
    url: str
    name: str
    image_path: str | None = None
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Group id cannot be empty")
        if not self.url.strip():
            raise ValueError("Group URL cannot be empty")
        if not self.name.strip():
            raise ValueError("Group name cannot be empty")

