import traceback

from pathlib import Path
from threading import Event

from PySide6.QtCore import QThread, Signal

from models.account_posting_plan import AccountPostingPlan
from services.account_posting_service import AccountPostingService


class PostingWorker(QThread):
    """Run one posting plan without moving QObjects between threads.

    ``AccountPostingService`` is synchronous and does not need a Qt event
    loop.  Keeping the QThread wrapper owned by the GUI thread while its
    ``run`` method performs the blocking work avoids the unsafe worker
    re-parenting/deletion sequence that previously corrupted Qt state when
    several accounts stopped at nearly the same time.
    """

    progress = Signal(object)
    result = Signal(object)
    completed = Signal(object)
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

    def run(self) -> None:
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
        self.completed.emit(results)
