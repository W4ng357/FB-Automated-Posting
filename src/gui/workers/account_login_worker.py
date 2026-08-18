import traceback

from collections.abc import Callable
from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, Signal, Slot

from facebook.account_profile import (
    FacebookProfileMetadata,
    run_account_login_session,
)


class AccountLoginWorker(QObject):
    started = Signal()
    status_changed = Signal(str)
    profile_ready = Signal(object)
    error = Signal(str)
    finished = Signal()

    def __init__(
        self,
        account_id: str,
        session_path: Path,
        session_runner: Callable = run_account_login_session,
    ) -> None:
        super().__init__()
        self.account_id = account_id
        self.session_path = session_path
        self.session_runner = session_runner
        self._capture_requested = Event()
        self._cancel_requested = Event()

    def request_profile(self) -> None:
        self._capture_requested.set()

    def cancel(self) -> None:
        self._cancel_requested.set()
        self._capture_requested.set()

    @Slot()
    def run(self) -> None:
        self.started.emit()
        try:
            metadata: FacebookProfileMetadata | None = self.session_runner(
                self.account_id,
                self.session_path,
                self._capture_requested,
                self._cancel_requested,
                self.status_changed.emit,
            )
            if metadata is not None:
                self.profile_ready.emit(metadata)
        except Exception as error:
            traceback.print_exc()
            self.error.emit(str(error))
        finally:
            self.finished.emit()
