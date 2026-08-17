from pathlib import Path

from models.listing import Listing
from services.caption_generator import (
    generate_caption as generate_listing_caption,
)
from services.listing_asset_manager import ListingAssetManager
from services.listing_repository import ListingRepository


class ListingService:
    def __init__(
        self,
        repository: ListingRepository | None = None,
        asset_manager: ListingAssetManager | None = None,
    ) -> None:
        self.repository = repository or ListingRepository()
        self.asset_manager = (
            asset_manager or ListingAssetManager()
        )

    def get_all(self) -> list[Listing]:
        return self.repository.get_all()

    def get_by_id(
        self,
        listing_id: str,
    ) -> Listing | None:
        return self.repository.get_by_id(listing_id)

    def create_listing(
        self,
        title: str,
        location: str,
        price: int,
        address: str = "",
        area: float | None = None,
        description: str = "",
        contact: str = "",
        enabled: bool = True,
        image_paths: list[Path] | None = None,
    ) -> Listing:
        listing = self.repository.create(
            title=title,
            location=location,
            price=price,
            address=address,
            area=area,
            description=description,
            contact=contact,
            enabled=enabled,
            reserved_ids=(
                self.asset_manager
                .get_existing_listing_ids()
            ),
        )

        listing_dir = self.asset_manager.get_listing_dir(
            listing.id
        )
        assets_already_existed = listing_dir.exists()

        try:
            self.asset_manager.create_listing_folder(
                listing.id
            )

            if image_paths:
                self.asset_manager.add_images(
                    listing.id,
                    image_paths,
                )
        except Exception as error:
            cleanup_errors: list[str] = []

            try:
                self.repository.delete(listing.id)
            except Exception as cleanup_error:
                cleanup_errors.append(
                    f"metadata cleanup failed: "
                    f"{cleanup_error}"
                )

            if not assets_already_existed:
                try:
                    self.asset_manager.delete_listing_assets(
                        listing.id
                    )
                except Exception as cleanup_error:
                    cleanup_errors.append(
                        f"asset cleanup failed: "
                        f"{cleanup_error}"
                    )

            if cleanup_errors:
                error.add_note("; ".join(cleanup_errors))

            raise

        return listing

    def update_listing(
        self,
        listing_id: str,
        **changes: object,
    ) -> Listing:
        listing = self._require_listing(listing_id)

        if "id" in changes:
            raise ValueError(
                "Listing ID cannot be changed"
            )

        if not changes:
            return listing

        return self.repository.update(
            listing_id,
            **changes,
        )

    def delete_listing(
        self,
        listing_id: str,
        delete_images: bool = False,
    ) -> bool:
        self._require_listing(listing_id)

        if delete_images:
            self.asset_manager.get_listing_dir(listing_id)

        deleted = self.repository.delete(listing_id)

        if not deleted:
            raise KeyError(
                f"Listing not found: {listing_id}"
            )

        if delete_images:
            self.asset_manager.delete_listing_assets(
                listing_id
            )

        return True

    def add_images(
        self,
        listing_id: str,
        image_paths: list[Path],
    ) -> list[Path]:
        self._require_listing(listing_id)

        return self.asset_manager.add_images(
            listing_id,
            image_paths,
        )

    def remove_image(
        self,
        listing_id: str,
        image_name: str,
    ) -> bool:
        self._require_listing(listing_id)

        return self.asset_manager.delete_image(
            listing_id,
            image_name,
        )

    def get_images(
        self,
        listing_id: str,
    ) -> list[Path]:
        self._require_listing(listing_id)

        return self.asset_manager.get_images(
            listing_id
        )

    def generate_caption(
        self,
        listing_id: str,
    ) -> str:
        listing = self._require_listing(listing_id)
        caption = generate_listing_caption(listing)

        if not caption:
            raise ValueError(
                f"Generated caption is empty: "
                f"{listing_id}"
            )

        return caption

    def prepare_for_posting(
        self,
        listing_id: str,
    ) -> tuple[str, list[Path]]:
        listing = self._require_listing(listing_id)

        if not listing.enabled:
            raise ValueError(
                f"Listing is disabled: {listing_id}"
            )

        images = self.asset_manager.get_images(
            listing_id
        )

        if not images:
            raise ValueError(
                f"Listing has no images: {listing_id}"
            )

        caption = generate_listing_caption(listing)

        if not caption:
            raise ValueError(
                f"Generated caption is empty: "
                f"{listing_id}"
            )

        return caption, images

    def _require_listing(
        self,
        listing_id: str,
    ) -> Listing:
        listing = self.repository.get_by_id(listing_id)

        if listing is None:
            raise KeyError(
                f"Listing not found: {listing_id}"
            )

        return listing
