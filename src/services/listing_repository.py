import json
import re

from dataclasses import asdict
from pathlib import Path

from models.listing import Listing


ROOT_DIR = Path(__file__).resolve().parents[2]

DEFAULT_LISTINGS_FILE = (
    ROOT_DIR
    / "data"
    / "listings.json"
)


class ListingRepository:
    def __init__(
        self,
        file_path: Path = DEFAULT_LISTINGS_FILE,
    ) -> None:
        self.file_path = file_path

    def get_all(self) -> list[Listing]:
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
                f"Invalid JSON in listings file: "
                f"{self.file_path}"
            ) from error

        if not isinstance(data, list):
            raise ValueError(
                f"Listings file must contain a JSON list: "
                f"{self.file_path}"
            )

        if not all(isinstance(item, dict) for item in data):
            raise ValueError(
                f"Every listing must be a JSON object: "
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
        title: str,
        location: str,
        price: int,
        address: str = "",
        area: float | None = None,
        description: str = "",
        contact: str = "",
        enabled: bool = True,
        reserved_ids: set[str] | None = None,
    ) -> Listing:
        listings = self.get_all()

        listing = Listing(
            id=self._generate_next_id(
                listings,
                reserved_ids or set(),
            ),
            title=title,
            location=location,
            price=price,
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
        listings = self.get_all()

        for index, listing in enumerate(listings):
            if listing.id != listing_id:
                continue

            data = asdict(listing)

            if "id" in changes:
                raise ValueError(
                    "Listing ID cannot be changed"
                )

            invalid_fields = (
                set(changes)
                - set(data)
            )

            if invalid_fields:
                raise ValueError(
                    f"Invalid fields: {invalid_fields}"
                )

            data.update(changes)

            updated_listing = Listing(**data)

            listings[index] = updated_listing

            self._save(listings)

            return updated_listing

        raise KeyError(
            f"Listing not found: {listing_id}"
        )

    def delete(
        self,
        listing_id: str,
    ) -> bool:
        listings = self.get_all()

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
