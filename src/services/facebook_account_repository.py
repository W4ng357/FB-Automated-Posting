import json
import threading

from dataclasses import asdict
from pathlib import Path

from models.facebook_account import FacebookAccount


from app_paths import ACCOUNTS_FILE

DEFAULT_ACCOUNTS_FILE = ACCOUNTS_FILE
_ACCOUNTS_LOCK = threading.RLock()


class FacebookAccountRepository:
    def __init__(
        self,
        file_path: Path = DEFAULT_ACCOUNTS_FILE,
    ) -> None:
        self.file_path = file_path

    def get_all(self) -> list[FacebookAccount]:
        with _ACCOUNTS_LOCK:
            return self._get_all_unlocked()

    def _get_all_unlocked(self) -> list[FacebookAccount]:
        if not self.file_path.is_file():
            return []
        raw_data = self.file_path.read_text(encoding="utf-8").strip()
        if not raw_data:
            return []
        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Invalid JSON in accounts file: {self.file_path}"
            ) from error
        if not isinstance(data, list) or not all(
            isinstance(item, dict) for item in data
        ):
            raise ValueError(
                "Accounts file must contain a JSON list of objects: "
                f"{self.file_path}"
            )
        return [FacebookAccount(**item) for item in data]

    def get_by_id(self, account_id: str) -> FacebookAccount | None:
        return next(
            (
                account
                for account in self.get_all()
                if account.id == account_id
            ),
            None,
        )

    def upsert(self, account: FacebookAccount) -> FacebookAccount:
        with _ACCOUNTS_LOCK:
            accounts = self._get_all_unlocked()
            for index, existing in enumerate(accounts):
                if existing.id == account.id:
                    accounts[index] = account
                    self._save(accounts)
                    return account
            accounts.append(account)
            self._save(accounts)
            return account

    def delete(self, account_id: str) -> bool:
        with _ACCOUNTS_LOCK:
            accounts = self._get_all_unlocked()
            remaining = [
                account for account in accounts if account.id != account_id
            ]
            if len(remaining) == len(accounts):
                return False
            self._save(remaining)
            return True

    def _save(self, accounts: list[FacebookAccount]) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(
            [asdict(account) for account in accounts],
            ensure_ascii=False,
            indent=2,
        )
        temporary = self.file_path.with_suffix(".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(self.file_path)
