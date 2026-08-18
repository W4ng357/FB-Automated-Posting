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
            raise ValueError("Mã phòng không được để trống.")

        if not self.title.strip():
            raise ValueError("Tên phòng không được để trống.")

        if not self.location.strip():
            raise ValueError("Địa chỉ phòng không được để trống.")

        if self.price < 0:
            raise ValueError("Giá thuê không được là số âm.")

        if self.area is not None and self.area <= 0:
            raise ValueError("Diện tích phải lớn hơn 0.")
