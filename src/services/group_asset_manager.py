from pathlib import Path
from shutil import rmtree


ROOT_DIR = Path(__file__).resolve().parents[2]
GROUPS_DIR = ROOT_DIR / "data" / "groups"
SUPPORTED_GROUP_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
}
MAX_GROUP_IMAGE_BYTES = 10 * 1024 * 1024


class GroupAssetManager:
    def __init__(self, groups_dir: Path = GROUPS_DIR) -> None:
        self.groups_dir = groups_dir.resolve()

    def get_group_dir(self, group_id: str) -> Path:
        if not group_id or Path(group_id).name != group_id:
            raise ValueError(f"Invalid group ID: {group_id!r}")
        group_dir = (self.groups_dir / group_id).resolve()
        if group_dir.parent != self.groups_dir:
            raise ValueError("Group directory is outside configured root")
        return group_dir

    def save_avatar(
        self,
        group_id: str,
        image_data: bytes,
        extension: str,
    ) -> str:
        suffix = extension.lower()
        if not suffix.startswith("."):
            suffix = f".{suffix}"
        if suffix not in SUPPORTED_GROUP_IMAGE_EXTENSIONS:
            raise ValueError(f"Unsupported group image type: {suffix}")
        if not image_data:
            raise ValueError("Group image is empty")
        if len(image_data) > MAX_GROUP_IMAGE_BYTES:
            raise ValueError("Group image exceeds 10 MB")

        group_dir = self.get_group_dir(group_id)
        group_dir.mkdir(parents=True, exist_ok=True)
        destination = (group_dir / f"avatar{suffix}").resolve()
        if destination.parent != group_dir:
            raise ValueError("Avatar path is outside group directory")
        temp_file = (group_dir / f".avatar{suffix}.tmp").resolve()
        if temp_file.parent != group_dir:
            raise ValueError("Temporary avatar path is outside group directory")
        temp_file.write_bytes(image_data)
        try:
            self.clear_avatar(group_id)
            temp_file.replace(destination)
        except Exception:
            temp_file.unlink(missing_ok=True)
            raise
        return f"{group_id}/{destination.name}"

    def resolve_image_path(
        self,
        relative_path: str | None,
    ) -> Path | None:
        if not relative_path:
            return None
        resolved = (self.groups_dir / relative_path).resolve()
        if self.groups_dir not in resolved.parents:
            raise ValueError("Saved group image path is outside data/groups")
        return resolved if resolved.is_file() else None

    def clear_avatar(self, group_id: str) -> None:
        group_dir = self.get_group_dir(group_id)
        if not group_dir.is_dir():
            return
        for item in group_dir.iterdir():
            if (
                item.is_file()
                and item.stem == "avatar"
                and item.suffix.lower()
                in SUPPORTED_GROUP_IMAGE_EXTENSIONS
            ):
                item.unlink()

    def delete_group_assets(self, group_id: str) -> bool:
        group_dir = self.get_group_dir(group_id)
        if not group_dir.exists():
            return False
        if not group_dir.is_dir():
            raise NotADirectoryError(str(group_dir))
        rmtree(group_dir)
        return True
