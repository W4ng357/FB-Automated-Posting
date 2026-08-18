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
            raise ValueError("Mã nhóm không được để trống.")
        if not self.url.strip():
            raise ValueError("URL nhóm không được để trống.")
        if not self.name.strip():
            raise ValueError("Tên nhóm không được để trống.")
