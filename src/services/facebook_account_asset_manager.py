from pathlib import Path
from shutil import rmtree


from app_paths import ACCOUNTS_DIR
SUPPORTED_AVATAR_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_AVATAR_BYTES = 5 * 1024 * 1024


class FacebookAccountAssetManager:
    def __init__(self, accounts_dir: Path = ACCOUNTS_DIR) -> None:
        self.accounts_dir = accounts_dir.resolve()

    def get_account_dir(self, account_id: str) -> Path:
        if not account_id or Path(account_id).name != account_id:
            raise ValueError(f"Invalid account ID: {account_id!r}")
        account_dir = (self.accounts_dir / account_id).resolve()
        if account_dir.parent != self.accounts_dir:
            raise ValueError("Account asset directory is outside configured root")
        return account_dir

    def save_avatar(
        self,
        account_id: str,
        image_data: bytes,
        extension: str,
    ) -> str:
        suffix = extension.lower()
        if not suffix.startswith("."):
            suffix = f".{suffix}"
        if suffix not in SUPPORTED_AVATAR_EXTENSIONS:
            suffix = ".jpg"
        if not image_data:
            raise ValueError("Avatar image is empty")
        if len(image_data) > MAX_AVATAR_BYTES:
            raise ValueError("Avatar image exceeds 5 MB")

        account_dir = self.get_account_dir(account_id)
        account_dir.mkdir(parents=True, exist_ok=True)
        destination = (account_dir / f"avatar{suffix}").resolve()
        temporary = (account_dir / f".avatar{suffix}.tmp").resolve()
        if destination.parent != account_dir or temporary.parent != account_dir:
            raise ValueError("Avatar path is outside account asset directory")
        temporary.write_bytes(image_data)
        try:
            self.clear_avatar(account_id)
            temporary.replace(destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        return f"{account_id}/{destination.name}"

    def resolve_avatar_path(self, relative_path: str | None) -> Path | None:
        if not relative_path:
            return None
        resolved = (self.accounts_dir / relative_path).resolve()
        if self.accounts_dir not in resolved.parents:
            raise ValueError("Saved avatar path is outside data/accounts")
        return resolved if resolved.is_file() else None

    def clear_avatar(self, account_id: str) -> None:
        account_dir = self.get_account_dir(account_id)
        if not account_dir.is_dir():
            return
        for item in account_dir.iterdir():
            if (
                item.is_file()
                and item.stem == "avatar"
                and item.suffix.lower() in SUPPORTED_AVATAR_EXTENSIONS
            ):
                item.unlink()

    def delete_account_assets(self, account_id: str) -> bool:
        account_dir = self.get_account_dir(account_id)
        if not account_dir.exists():
            return False
        if not account_dir.is_dir():
            raise NotADirectoryError(str(account_dir))
        rmtree(account_dir)
        return True
