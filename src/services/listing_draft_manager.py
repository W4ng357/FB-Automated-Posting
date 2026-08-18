from pathlib import Path
from uuid import uuid4

from services.listing_asset_manager import ListingAssetManager


from app_paths import DRAFTS_DIR


class ListingDraftManager:
    def __init__(self, drafts_dir: Path = DRAFTS_DIR) -> None:
        self.asset_manager = ListingAssetManager(drafts_dir)

    def create_draft(self) -> str:
        draft_id = uuid4().hex
        self.asset_manager.create_listing_folder(draft_id)
        return draft_id

    def get_images_dir(self, draft_id: str) -> Path:
        return self.asset_manager.get_images_dir(draft_id)

    def get_images(self, draft_id: str) -> list[Path]:
        return self.asset_manager.get_images(draft_id)

    def add_images(
        self,
        draft_id: str,
        image_paths: list[Path],
    ) -> list[Path]:
        return self.asset_manager.add_images(draft_id, image_paths)

    def remove_image(self, draft_id: str, image_name: str) -> bool:
        return self.asset_manager.delete_image(draft_id, image_name)

    def cleanup(self, draft_id: str) -> bool:
        return self.asset_manager.delete_listing_assets(draft_id)

