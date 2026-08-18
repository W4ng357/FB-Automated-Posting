from pathlib import Path
from shutil import copy2, rmtree

from services.content_loader import (
    SUPPORTED_IMAGE_EXTENSIONS,
)

from app_paths import LISTINGS_DIR


class ListingAssetManager:
    def __init__(
        self,
        listings_dir: Path = LISTINGS_DIR,
    ) -> None:
        self.listings_dir = listings_dir.resolve()

    def get_listing_dir(
        self,
        listing_id: str,
    ) -> Path:
        if not listing_id or Path(listing_id).name != listing_id:
            raise ValueError(
                f"Mã phòng không hợp lệ: {listing_id!r}"
            )

        listing_dir = (
            self.listings_dir
            / listing_id
        ).resolve()

        if (
            listing_dir.parent != self.listings_dir
            or listing_dir.name != listing_id
        ):
            raise ValueError(
                f"Listing directory is outside "
                f"the configured listings directory: "
                f"{listing_id!r}"
            )

        return listing_dir

    def get_images_dir(
        self,
        listing_id: str,
    ) -> Path:
        listing_dir = self.get_listing_dir(listing_id)
        images_dir = (listing_dir / "images").resolve()

        if (
            images_dir.parent != listing_dir
            or images_dir.name != "images"
        ):
            raise ValueError(
                f"Images directory is outside the "
                f"listing directory: {listing_id!r}"
            )

        return images_dir

    def create_listing_folder(
        self,
        listing_id: str,
    ) -> Path:
        images_dir = self.get_images_dir(
            listing_id
        )

        images_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        return images_dir

    def get_existing_listing_ids(self) -> set[str]:
        if not self.listings_dir.exists():
            return set()

        if not self.listings_dir.is_dir():
            raise NotADirectoryError(
                f"Listings asset path is not a directory: "
                f"{self.listings_dir}"
            )

        return {
            path.name
            for path in self.listings_dir.iterdir()
            if path.is_dir()
        }

    def get_images(
        self,
        listing_id: str,
    ) -> list[Path]:
        images_dir = self.get_images_dir(
            listing_id
        )

        if not images_dir.exists():
            return []

        if not images_dir.is_dir():
            raise NotADirectoryError(
                f"Images path is not a directory: "
                f"{images_dir}"
            )

        return sorted(
            image
            for image in images_dir.iterdir()
            if image.is_file()
            and image.suffix.lower()
            in SUPPORTED_IMAGE_EXTENSIONS
        )

    def add_images(
        self,
        listing_id: str,
        source_paths: list[Path],
    ) -> list[Path]:
        if not source_paths:
            return []

        validated_sources: list[Path] = []

        for source_path in source_paths:
            resolved_source = source_path.resolve()

            if not resolved_source.is_file():
                raise FileNotFoundError(
                    f"Không tìm thấy ảnh: {resolved_source}"
                )

            extension = resolved_source.suffix.lower()

            if extension not in SUPPORTED_IMAGE_EXTENSIONS:
                raise ValueError(
                    f"Định dạng ảnh chưa được hỗ trợ: "
                    f"{resolved_source}"
                )

            validated_sources.append(resolved_source)

        images_dir = self.create_listing_folder(
            listing_id
        )

        next_number = self._get_next_image_number(
            listing_id
        )

        copied_images: list[Path] = []

        try:
            for source_path in validated_sources:
                extension = source_path.suffix.lower()

                destination = (
                    images_dir
                    / f"{next_number:03d}{extension}"
                )

                copy2(
                    source_path,
                    destination,
                )

                copied_images.append(destination)

                next_number += 1
        except Exception:
            for copied_image in copied_images:
                copied_image.unlink(missing_ok=True)

            raise

        return copied_images

    def delete_image(
        self,
        listing_id: str,
        image_name: str,
    ) -> bool:
        images_dir = self.get_images_dir(
            listing_id
        ).resolve()

        if not image_name or Path(image_name).name != image_name:
            raise ValueError(
                f"Tên ảnh không hợp lệ: {image_name!r}"
            )

        image_path = (images_dir / image_name).resolve()

        if image_path.parent != images_dir:
            raise ValueError(
                f"Image path is outside the listing "
                f"images directory: {image_name!r}"
            )

        if not image_path.is_file():
            return False

        image_path.unlink()

        return True

    def clear_images(
        self,
        listing_id: str,
    ) -> int:
        images = self.get_images(
            listing_id
        )

        for image in images:
            image.unlink()

        return len(images)

    def delete_listing_assets(
        self,
        listing_id: str,
    ) -> bool:
        listing_dir = self.get_listing_dir(
            listing_id
        )

        if not listing_dir.exists():
            return False

        if not listing_dir.is_dir():
            raise NotADirectoryError(
                f"Listing asset path is not a directory: "
                f"{listing_dir}"
            )

        rmtree(listing_dir)

        return True

    def _get_next_image_number(
        self,
        listing_id: str,
    ) -> int:
        highest_number = 0

        for image in self.get_images(listing_id):
            try:
                number = int(image.stem)
            except ValueError:
                continue

            highest_number = max(
                highest_number,
                number,
            )

        return highest_number + 1
