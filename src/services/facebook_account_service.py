import re

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from shutil import rmtree

from facebook.account_profile import FacebookProfileMetadata
from models.facebook_account import FacebookAccount, normalize_facebook_name
from services.account_session_registry import AccountSessionRegistry
from services.facebook_account_asset_manager import (
    FacebookAccountAssetManager,
)
from services.facebook_account_repository import FacebookAccountRepository
from session_manager import SESSIONS_DIR


class FacebookAccountService:
    def __init__(
        self,
        repository: FacebookAccountRepository | None = None,
        asset_manager: FacebookAccountAssetManager | None = None,
        sessions_dir: Path = SESSIONS_DIR,
        session_lister: Callable[[], list[str]] | None = None,
    ) -> None:
        self.repository = repository or FacebookAccountRepository()
        self.asset_manager = asset_manager or FacebookAccountAssetManager()
        self.sessions_dir = sessions_dir.resolve()
        self._session_lister = session_lister or self._list_session_dirs

    def get_all(self) -> list[FacebookAccount]:
        registered = {
            account.id: account for account in self.repository.get_all()
        }
        for session_id in self._session_lister():
            if session_id in registered:
                continue
            try:
                registered[session_id] = FacebookAccount(id=session_id)
            except ValueError:
                continue
        return sorted(
            registered.values(),
            key=lambda account: account.display_name.casefold(),
        )

    def get_by_id(self, account_id: str) -> FacebookAccount | None:
        account = self.repository.get_by_id(account_id)
        if account is not None:
            return account
        if self.get_session_path(account_id).is_dir():
            return FacebookAccount(id=account_id)
        return None

    def create_pending_account(self) -> FacebookAccount:
        known_ids = {account.id for account in self.get_all()}
        highest = 0
        for account_id in known_ids:
            match = re.fullmatch(r"account-(\d+)", account_id)
            if match:
                highest = max(highest, int(match.group(1)))
        account = FacebookAccount(
            id=f"account-{highest + 1:03d}",
            created_at=self._now(),
            updated_at=self._now(),
        )
        return self.repository.upsert(account)

    def update_alias(
        self,
        account_id: str,
        alias: str,
    ) -> FacebookAccount:
        account = self._require_account(account_id)
        updated = replace(
            account,
            alias=alias.strip(),
            updated_at=self._now(),
        )
        return self.repository.upsert(updated)

    def apply_metadata(
        self,
        account_id: str,
        metadata: FacebookProfileMetadata,
    ) -> FacebookAccount:
        account = self._require_account(account_id)
        clean_name = normalize_facebook_name(metadata.name)
        if not clean_name:
            raise ValueError("Không đọc được tên tài khoản Facebook")
        avatar_path = account.avatar_path
        if metadata.avatar_data:
            avatar_path = self.asset_manager.save_avatar(
                account_id,
                metadata.avatar_data,
                metadata.avatar_extension or ".jpg",
            )
        updated = replace(
            account,
            facebook_name=clean_name,
            profile_url=metadata.profile_url.strip(),
            avatar_path=avatar_path,
            session_verified=True,
            updated_at=self._now(),
        )
        return self.repository.upsert(updated)

    def get_avatar_path(self, account: FacebookAccount) -> Path | None:
        try:
            return self.asset_manager.resolve_avatar_path(account.avatar_path)
        except (OSError, ValueError):
            return None

    def get_session_path(self, account_id: str) -> Path:
        FacebookAccount(id=account_id)
        session_path = (self.sessions_dir / account_id).resolve()
        if session_path.parent != self.sessions_dir:
            raise ValueError("Session path is outside browser_sessions")
        return session_path

    def has_session(self, account_id: str) -> bool:
        if not self._raw_session_exists(account_id):
            return False
        registered = self.repository.get_by_id(account_id)
        if registered is None:
            return True
        return registered.session_verified or registered.is_synced

    def discard_if_unused(self, account_id: str) -> bool:
        account = self.repository.get_by_id(account_id)
        if account is not None and not (
            account.session_verified or account.is_synced
        ):
            return self.delete_account(account_id)
        if self._raw_session_exists(account_id):
            return False
        self.asset_manager.delete_account_assets(account_id)
        return self.repository.delete(account_id)

    def delete_account(self, account_id: str) -> bool:
        self._require_account(account_id)
        session_path = self.get_session_path(account_id)
        lock_path = session_path if session_path.is_dir() else None
        with AccountSessionRegistry.exclusive(account_id, lock_path):
            deleted = False
            if session_path.exists():
                if not session_path.is_dir():
                    raise NotADirectoryError(str(session_path))
                rmtree(session_path)
                deleted = True
            deleted = (
                self.asset_manager.delete_account_assets(account_id)
                or deleted
            )
            deleted = self.repository.delete(account_id) or deleted
        return deleted

    def _require_account(self, account_id: str) -> FacebookAccount:
        account = self.get_by_id(account_id)
        if account is None:
            raise KeyError(f"Không tìm thấy tài khoản {account_id}")
        if self.repository.get_by_id(account_id) is None:
            account = replace(
                account,
                session_verified=self._raw_session_exists(account_id),
                created_at=self._now(),
                updated_at=self._now(),
            )
            self.repository.upsert(account)
        return account

    def _list_session_dirs(self) -> list[str]:
        if not self.sessions_dir.is_dir():
            return []
        return sorted(
            path.name for path in self.sessions_dir.iterdir() if path.is_dir()
        )

    def _raw_session_exists(self, account_id: str) -> bool:
        if self.get_session_path(account_id).is_dir():
            return True
        return account_id in self._session_lister()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
