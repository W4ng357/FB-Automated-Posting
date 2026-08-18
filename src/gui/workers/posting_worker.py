import traceback

from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, Signal, Slot

from models.account_posting_plan import AccountPostingPlan
from services.account_posting_service import AccountPostingService


class PostingWorker(QObject):
    started = Signal()
    progress = Signal(object)
    result = Signal(object)
    finished = Signal(object)
    error = Signal(str)

    def __init__(
        self,
        session_path: Path,
        plan: AccountPostingPlan,
        posting_service: AccountPostingService | None = None,
    ) -> None:
        super().__init__()
        self.session_path = session_path
        self.plan = plan
        self.posting_service = (
            posting_service or AccountPostingService()
        )
        self._stop_requested = Event()

    def request_stop(self) -> None:
        self._stop_requested.set()

    @Slot()
    def run(self) -> None:
        self.started.emit()
        try:
            results = self.posting_service.run_plan(
                session_path=self.session_path,
                plan=self.plan,
                progress_callback=self.progress.emit,
                result_callback=self.result.emit,
                stop_requested=self._stop_requested.is_set,
            )
        except Exception as error:
            traceback.print_exc()
            self.error.emit(str(error))
            return
        self.finished.emit(results)
