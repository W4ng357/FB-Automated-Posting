import json
import re
import threading

from dataclasses import asdict
from pathlib import Path

from models.listing import Listing


from app_paths import LISTINGS_FILE

DEFAULT_LISTINGS_FILE = LISTINGS_FILE


_LISTINGS_LOCK = threading.RLock()


class ListingRepository:
    def __init__(
        self,
        file_path: Path = DEFAULT_LISTINGS_FILE,
    ) -> None:
        self.file_path = file_path

    def get_all(self) -> list[Listing]:
        with _LISTINGS_LOCK:
            return self._get_all_unlocked()

    def _get_all_unlocked(self) -> list[Listing]:
        if not self.file_path.is_file():
            return []

        raw_data = self.file_path.read_text(
            encoding="utf-8"
        ).strip()

        if not raw_data:
            return []

        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Tệp danh sách phòng có JSON không hợp lệ: "
                f"{self.file_path}"
            ) from error

        if not isinstance(data, list):
            raise ValueError(
                f"Dữ liệu phòng phải là một danh sách JSON: "
                f"{self.file_path}"
            )

        if not all(isinstance(item, dict) for item in data):
            raise ValueError(
                f"Mỗi phòng phải là một đối tượng JSON: "
                f"{self.file_path}"
            )

        return [
            Listing(**item)
            for item in data
        ]

    def get_by_id(
        self,
        listing_id: str,
    ) -> Listing | None:
        listings = self.get_all()

        for listing in listings:
            if listing.id == listing_id:
                return listing

        return None

    def create(
        self,
        location: str,
        price: int,
        title: str = "",
        price_unit: str = "TR",
        address: str = "",
        area: float | None = None,
        description: str = "",
        contact: str = "",
        enabled: bool = True,
        reserved_ids: set[str] | None = None,
    ) -> Listing:
        with _LISTINGS_LOCK:
            listings = self._get_all_unlocked()

            listing = Listing(
                id=self._generate_next_id(
                    listings,
                    reserved_ids or set(),
                ),
                title=title,
                location=location,
                price=price,
                price_unit=price_unit,
                address=address,
                area=area,
                description=description,
                contact=contact,
                enabled=enabled,
            )

            listings.append(listing)

            self._save(listings)

            return listing

    def update(
        self,
        listing_id: str,
        **changes,
    ) -> Listing:
        with _LISTINGS_LOCK:
            listings = self._get_all_unlocked()

            for index, listing in enumerate(listings):
                if listing.id != listing_id:
                    continue

                data = asdict(listing)

                if "id" in changes:
                    raise ValueError(
                        "Không thể thay đổi mã phòng."
                    )

                invalid_fields = (
                    set(changes)
                    - set(data)
                )

                if invalid_fields:
                    raise ValueError(
                        f"Trường dữ liệu không hợp lệ: {invalid_fields}"
                    )

                data.update(changes)

                updated_listing = Listing(**data)

                listings[index] = updated_listing

                self._save(listings)

                return updated_listing

            raise KeyError(
                f"Không tìm thấy phòng {listing_id}."
            )

    def delete(
        self,
        listing_id: str,
    ) -> bool:
        with _LISTINGS_LOCK:
            listings = self._get_all_unlocked()

            updated_listings = [
                listing
                for listing in listings
                if listing.id != listing_id
            ]

            if len(updated_listings) == len(listings):
                return False

            self._save(updated_listings)

            return True

    def _save(
        self,
        listings: list[Listing],
    ) -> None:
        self.file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = [
            asdict(listing)
            for listing in listings
        ]

        json_content = json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )

        # Ghi file tạm trước để giảm nguy cơ
        # làm hỏng listings.json khi đang save.
        temp_file = self.file_path.with_suffix(
            ".tmp"
        )

        temp_file.write_text(
            json_content,
            encoding="utf-8",
        )

        temp_file.replace(self.file_path)

    @staticmethod
    def _generate_next_id(
        listings: list[Listing],
        reserved_ids: set[str] | None = None,
    ) -> str:
        highest_id = 0

        listing_ids = [
            listing.id
            for listing in listings
        ]
        listing_ids.extend(reserved_ids or set())

        for listing_id in listing_ids:
            match = re.fullmatch(
                r"R(\d+)",
                listing_id,
            )

            if not match:
                continue

            number = int(match.group(1))

            highest_id = max(
                highest_id,
                number,
            )

        return f"R{highest_id + 1:03d}"
