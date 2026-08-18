from pathlib import Path
from urllib.parse import urlsplit

from models.saved_group import SavedGroup
from services.group_asset_manager import GroupAssetManager
from services.group_repository import GroupRepository


class GroupService:
    def __init__(
        self,
        repository: GroupRepository | None = None,
        asset_manager: GroupAssetManager | None = None,
    ) -> None:
        self.repository = repository or GroupRepository()
        self.asset_manager = asset_manager or GroupAssetManager()
        self.last_image_error: str | None = None

    def get_all(self) -> list[SavedGroup]:
        return self.repository.get_all()

    def get_by_id(self, group_id: str) -> SavedGroup | None:
        return self.repository.get_by_id(group_id)

    def create_group(
        self,
        url: str,
        name: str,
        image_data: bytes | None = None,
        image_extension: str | None = None,
        enabled: bool = True,
    ) -> SavedGroup:
        normalized_url = self.normalize_group_url(url)
        clean_name = name.strip()
        group = self.repository.create(
            url=normalized_url,
            name=clean_name,
            enabled=enabled,
        )
        return self._cache_optional_image(
            group,
            image_data,
            image_extension,
        )

    def update_group(
        self,
        group_id: str,
        *,
        url: str,
        name: str,
        enabled: bool,
        image_data: bytes | None = None,
        image_extension: str | None = None,
    ) -> SavedGroup:
        group = self.repository.update(
            group_id,
            url=self.normalize_group_url(url),
            name=name.strip(),
            enabled=enabled,
        )
        return self._cache_optional_image(
            group,
            image_data,
            image_extension,
        )

    def delete_group(
        self,
        group_id: str,
        delete_image: bool = True,
    ) -> bool:
        if self.repository.get_by_id(group_id) is None:
            raise KeyError(f"Group not found: {group_id}")
        deleted = self.repository.delete(group_id)
        if delete_image:
            self.asset_manager.delete_group_assets(group_id)
        return deleted

    def get_image_path(self, group: SavedGroup) -> Path | None:
        return self.asset_manager.resolve_image_path(group.image_path)

    @staticmethod
    def normalize_group_url(url: str) -> str:
        candidate = url.strip()
        if not candidate:
            raise ValueError("Group URL cannot be empty")
        if "://" not in candidate:
            candidate = f"https://{candidate}"

        parsed = urlsplit(candidate)
        host = (parsed.hostname or "").lower()
        if host != "facebook.com" and not host.endswith(".facebook.com"):
            raise ValueError("URL must belong to facebook.com")

        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 2 or parts[0].lower() != "groups":
            raise ValueError("URL must point to a Facebook group")

        return f"https://www.facebook.com/groups/{parts[1]}"

    def _cache_optional_image(
        self,
        group: SavedGroup,
        image_data: bytes | None,
        image_extension: str | None,
    ) -> SavedGroup:
        self.last_image_error = None
        if image_data is None or image_extension is None:
            return group

        try:
            image_path = self.asset_manager.save_avatar(
                group.id,
                image_data,
                image_extension,
            )
            return self.repository.update(
                group.id,
                image_path=image_path,
            )
        except Exception as error:
            # Metadata remains useful even if the optional image cache fails.
            self.last_image_error = str(error)
            return group
