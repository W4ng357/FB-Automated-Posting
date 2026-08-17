from dataclasses import dataclass


@dataclass
class Listing:
    id: str
    title: str
    location: str
    price: int

    address: str = ""
    area: float | None = None
    description: str = ""
    contact: str = ""
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Listing id cannot be empty")

        if not self.title.strip():
            raise ValueError("Listing title cannot be empty")

        if not self.location.strip():
            raise ValueError("Listing location cannot be empty")

        if self.price < 0:
            raise ValueError("Price cannot be negative")

        if self.area is not None and self.area <= 0:
            raise ValueError("Area must be greater than 0")