import threading

from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows uses the in-process guard.
    fcntl = None


class AccountSessionBusyError(RuntimeError):
    pass


class AccountSessionRegistry:
    _lock = threading.Lock()
    _running_accounts: set[str] = set()

    @classmethod
    def is_busy(cls, account_name: str) -> bool:
        with cls._lock:
            return account_name in cls._running_accounts

    @classmethod
    @contextmanager
    def exclusive(
        cls,
        account_name: str,
        session_path: Path | None = None,
    ) -> Iterator[None]:
        lock_handle = None
        with cls._lock:
            if account_name in cls._running_accounts:
                raise AccountSessionBusyError(
                    f"Tài khoản “{account_name}” đang chạy"
                )
            cls._running_accounts.add(account_name)

        try:
            if session_path is not None and fcntl is not None:
                lock_path = session_path / ".fb_poster.lock"
                lock_handle = lock_path.open("a+", encoding="utf-8")
                try:
                    fcntl.flock(
                        lock_handle.fileno(),
                        fcntl.LOCK_EX | fcntl.LOCK_NB,
                    )
                except BlockingIOError as error:
                    raise AccountSessionBusyError(
                        f"Tài khoản “{account_name}” đang được một cửa sổ "
                        "khác sử dụng"
                    ) from error
            yield
        finally:
            if lock_handle is not None:
                if fcntl is not None:
                    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
                lock_handle.close()
            with cls._lock:
                cls._running_accounts.discard(account_name)
