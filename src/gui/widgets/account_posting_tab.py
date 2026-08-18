from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QSize, QThread, QTime, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.dialogs.posting_results_dialog import PostingResultsDialog
from gui.widgets.design_components import (
    RoundedThumbnail,
    SmoothProgressBar,
    StatusBadge,
)
from gui.workers.posting_worker import PostingWorker
from models.account_posting_plan import AccountPostingPlan
from models.facebook_account import FacebookAccount
from models.listing_posting_task import ListingPostingTask
from models.posting_progress import PostingProgress
from models.posting_result_entry import PostingResultEntry
from services.facebook_account_service import FacebookAccountService
from services.group_service import GroupService
from services.listing_service import ListingService
from session_manager import get_session


class AccountPostingTab(QWidget):
    running_changed = Signal(str, bool)
    status_changed = Signal(str, str)
    queue_changed = Signal(str)
    plan_requested = Signal(str)

    def __init__(
        self,
        account_name: str | FacebookAccount,
        listing_service: ListingService,
        group_service: GroupService,
        worker_factory: Callable = PostingWorker,
        account_service: FacebookAccountService | None = None,
        avatar_path: Path | None = None,
        session_available: bool = True,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.account = (
            account_name
            if isinstance(account_name, FacebookAccount)
            else FacebookAccount(id=account_name)
        )
        self.account_name = self.account.id
        self.listing_service = listing_service
        self.group_service = group_service
        self.account_service = account_service
        self.avatar_path = avatar_path
        self.session_available = session_available
        self.worker_factory = worker_factory
        self.tasks: list[ListingPostingTask] = []
        self._thread: QThread | None = None
        # Finished QThread wrappers stay owned by the tab. Deleting them while
        # PySide is still dispatching cross-thread signals can corrupt Qt state.
        self._retired_threads: list[QThread] = []
        self._worker: PostingWorker | None = None
        self._run_active = False
        self._stop_pending = False
        self._run_total_attempts = 0
        self._completion_status = (
            "Sẵn sàng" if self.session_available else "Chưa đăng nhập"
        )
        self.last_progress: PostingProgress | None = None
        self.result_entries: list[PostingResultEntry] = []
        self._run_result_start_index = 0
        self._run_number = 0
        self._run_log_closed = True
        self._results_dialog: PostingResultsDialog | None = None
        self._available_listing_count = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)
        root.addWidget(self._create_account_header())
        summary = QHBoxLayout()
        summary.setSpacing(10)
        summary.addWidget(self._create_progress_panel(), 3)
        summary.addWidget(self._create_plan_panel(), 2)
        root.addLayout(summary)
        root.addWidget(self._create_activity_panel(), 1)
        self.refresh_available_data()
        self._render_queue()
        self._render_results([])

    @property
    def is_running(self) -> bool:
        return self._run_active

    @property
    def total_attempts(self) -> int:
        return sum(task.total_attempts for task in self.tasks)

    @property
    def stop_pending(self) -> bool:
        return self._stop_pending

    @property
    def has_available_listings(self) -> bool:
        return self._available_listing_count > 0

    def _create_account_header(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("workspaceHeader", True)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        identity_row = QHBoxLayout()
        identity_row.setSpacing(10)
        self.account_avatar = RoundedThumbnail(
            self.avatar_path,
            self.account.display_name,
            QSize(46, 46),
            circular=True,
        )
        heading = QVBoxLayout()
        heading.setSpacing(2)
        self.account_title = QLabel(self.account.display_name)
        self.account_title.setObjectName("SectionTitle")
        self.account_hint = QLabel(self._account_hint_text())
        self.account_hint.setProperty("muted", True)
        self.account_hint.setWordWrap(True)
        heading.addWidget(self.account_title)
        heading.addWidget(self.account_hint)
        self.status_label = StatusBadge(
            self._completion_status,
            "ready" if self.session_available else "warning",
        )
        identity_row.addWidget(self.account_avatar)
        identity_row.addLayout(heading, 1)
        identity_row.addWidget(self.status_label, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(identity_row)
        divider = QFrame()
        divider.setObjectName("HeaderActionsDivider")
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.plan_button = QPushButton("Chỉnh kế hoạch")
        self.plan_button.setProperty("density", "compact")
        self.plan_button.clicked.connect(self._configure_plan)
        self.results_button = QPushButton("Kết quả")
        self.results_button.setProperty("role", "ghost")
        self.results_button.setProperty("density", "compact")
        self.results_button.clicked.connect(self._open_results)
        self.stop_button = QPushButton("Dừng đăng bài")
        self.stop_button.setProperty("role", "danger")
        self.stop_button.setProperty("density", "compact")
        self.stop_button.setEnabled(False)
        self.stop_button.setToolTip(
            "Đăng xong bài hiện tại, rồi dừng ở khoảng nghỉ tiếp theo."
        )
        self.stop_button.clicked.connect(self.stop)
        self.start_button = QPushButton("Bắt đầu")
        self.start_button.setProperty("role", "primary")
        self.start_button.setProperty("density", "compact")
        self.start_button.clicked.connect(self.start)
        actions.addWidget(self.plan_button)
        actions.addWidget(self.results_button)
        actions.addStretch()
        actions.addWidget(self.stop_button)
        actions.addWidget(self.start_button)
        layout.addLayout(actions)
        return panel

    def _create_progress_panel(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("progressCard", True)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(7)
        row = QHBoxLayout()
        title = QLabel("Tiến trình")
        title.setObjectName("SectionTitle")
        self.progress_numbers = QLabel("0/0 lượt thành công")
        self.progress_numbers.setObjectName("ProgressValue")
        row.addWidget(title)
        row.addStretch()
        row.addWidget(self.progress_numbers)
        self.progress_bar = SmoothProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.current_label = QLabel("Hiện tại: Chưa bắt đầu")
        self.current_label.setProperty("progressDetail", True)
        self.current_label.setWordWrap(True)
        self.next_label = QLabel("Tiếp theo: Chưa có")
        self.next_label.setProperty("meta", True)
        self.next_label.setWordWrap(True)
        layout.addLayout(row)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.current_label)
        layout.addWidget(self.next_label)
        return panel

    def _create_plan_panel(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("planSummary", True)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)
        row = QHBoxLayout()
        title = QLabel("Kế hoạch")
        title.setObjectName("SectionTitle")
        self.queue_summary = QLabel()
        self.queue_summary.setProperty("overviewStrong", True)
        row.addWidget(title)
        row.addStretch()
        row.addWidget(self.queue_summary)
        self.plan_detail_label = QLabel()
        self.plan_detail_label.setProperty("muted", True)
        self.plan_detail_label.setWordWrap(True)
        self.plan_detail_label.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        layout.addLayout(row)
        layout.addWidget(self.plan_detail_label, 1)
        return panel

    def _create_activity_panel(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("section", True)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)
        heading = QHBoxLayout()
        title = QLabel("Nhật ký hoạt động")
        title.setObjectName("SectionTitle")
        helper = QLabel("Cập nhật theo thời gian thực · chia theo từng lần chạy")
        helper.setProperty("meta", True)
        heading.addWidget(title)
        heading.addStretch()
        heading.addWidget(helper)
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setProperty("terminal", True)
        self.log_output.setPlaceholderText(
            "Nhật ký đăng bài của tài khoản này sẽ xuất hiện tại đây."
        )
        self.log_output.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        layout.addLayout(heading)
        layout.addWidget(self.log_output, 1)
        return panel

    def update_account(
        self,
        account: FacebookAccount,
        avatar_path: Path | None,
        session_available: bool,
    ) -> None:
        self.account = account
        self.account_name = account.id
        self.avatar_path = avatar_path
        self.session_available = session_available
        self.account_avatar.set_source(avatar_path, account.display_name)
        self.account_title.setText(account.display_name)
        self.account_hint.setText(self._account_hint_text())
        if self._results_dialog is not None:
            self._results_dialog.account_display_name = account.display_name
        if not self.is_running and self._completion_status in {
            "Sẵn sàng",
            "Chưa đăng nhập",
        }:
            self._completion_status = (
                "Sẵn sàng" if session_available else "Chưa đăng nhập"
            )
            self.status_label.set_state(
                self._completion_status,
                "ready" if session_available else "warning",
            )
        self._update_action_availability()

    def _account_hint_text(self) -> str:
        if self.account.alias.strip() and self.account.facebook_name.strip():
            identity = f"Facebook: {self.account.facebook_name.strip()}"
        elif self.account.is_synced:
            identity = f"Phiên đăng nhập: {self.account.id}"
        else:
            identity = (
                f"Phiên đăng nhập: {self.account.id} · "
                "chưa lấy thông tin Facebook"
            )
        return f"{identity} · mỗi tài khoản chạy một kế hoạch tại một thời điểm"

    def refresh_available_data(self) -> None:
        try:
            self._available_listing_count = sum(
                1
                for listing in self.listing_service.get_all()
                if listing.enabled
            )
        except Exception as error:
            self._available_listing_count = 0
            self._append_log(f"Không tải được danh sách phòng: {error}")
        self._update_action_availability()

    def _configure_plan(self) -> None:
        if self.is_running:
            return
        if not self._available_listing_count:
            QMessageBox.information(
                self,
                "Chưa có phòng sẵn sàng",
                "Hãy tạo phòng, thêm ảnh và bật phòng trước.",
            )
            return
        self.plan_requested.emit(self.account_name)

    def apply_plan(self, tasks: list[ListingPostingTask]) -> None:
        if self.is_running:
            raise RuntimeError(
                f"{self.account.display_name} đang chạy, không thể đổi kế hoạch."
            )
        self.tasks = [task.fresh_copy() for task in tasks]
        self._render_queue()
        self.queue_changed.emit(self.account_name)

    def _add_task(self) -> None:
        self._configure_plan()

    def _edit_task(self, _listing_id: str) -> None:
        self._configure_plan()

    def _remove_task(self, listing_id: str) -> None:
        self.tasks = [
            task for task in self.tasks if task.listing_id != listing_id
        ]
        self._render_queue()
        self.queue_changed.emit(self.account_name)

    def _render_queue(self) -> None:
        self.queue_summary.setText(
            f"{len(self.tasks)} phòng · {self.total_attempts} lượt"
        )
        if not self.tasks:
            self.plan_detail_label.setText(
                "Chưa có phòng trong kế hoạch. Bấm “Chỉnh kế hoạch” để thêm."
            )
        else:
            lines = [
                f"{task.listing_title} · {len(task.group_targets)} nhóm"
                f" · {task.total_attempts} lượt"
                for task in self.tasks[:3]
            ]
            if len(self.tasks) > 3:
                lines.append(f"Còn {len(self.tasks) - 3} phòng khác")
            self.plan_detail_label.setText("\n".join(lines))
        self._update_action_availability()

    def start(self) -> bool:
        if self.is_running:
            return False
        if not self.session_available:
            QMessageBox.warning(
                self,
                "Tài khoản chưa đăng nhập",
                "Đăng nhập tài khoản Facebook này trước khi bắt đầu.",
            )
            return False
        if not self.tasks:
            QMessageBox.warning(
                self,
                "Chưa có kế hoạch đăng",
                f"Chọn ít nhất một phòng cho {self.account.display_name}.",
            )
            return False
        try:
            session_path = (
                self.account_service.get_session_path(self.account_name)
                if self.account_service is not None
                else get_session(self.account_name)
            )
            if not session_path.is_dir():
                raise FileNotFoundError(
                    f"Không tìm thấy phiên đăng nhập của {self.account.display_name}"
                )
            for task in self.tasks:
                self.listing_service.prepare_for_posting(task.listing_id)
            plan = AccountPostingPlan(
                account_name=self.account_name,
                tasks=[task.fresh_copy() for task in self.tasks],
            )
        except Exception as error:
            QMessageBox.warning(self, "Chưa thể bắt đầu", str(error))
            return False

        try:
            worker = self.worker_factory(session_path, plan)
        except Exception as error:
            QMessageBox.warning(self, "Chưa thể bắt đầu", str(error))
            return False
        worker.started.connect(
            lambda: self._append_log("Đã bắt đầu tiến trình đăng bài.")
        )
        worker.progress.connect(self._on_progress)
        worker.result.connect(self._on_result)
        worker.completed.connect(self._on_worker_finished)
        worker.error.connect(self._on_worker_error)
        worker.finished.connect(self._on_thread_finished)
        self._thread = worker
        self._worker = worker
        self._run_active = True
        self._run_result_start_index = len(self.result_entries)
        self._stop_pending = False
        self._run_total_attempts = plan.total_attempts
        self.last_progress = None
        self._append_run_header(plan)
        self._set_running(True)
        worker.start()
        return True

    def stop(self) -> bool:
        if not self.is_running or self._worker is None:
            return False
        if self._stop_pending:
            return False
        self._stop_pending = True
        self._worker.request_stop()
        self.stop_button.setEnabled(False)
        self.stop_button.setText("Đang chờ dừng…")
        self.status_label.set_state("Đang chờ dừng", "warning")
        self._append_log(
            "Đã nhận yêu cầu dừng. Ứng dụng sẽ đăng xong bài hiện tại rồi dừng."
        )
        self.status_changed.emit(self.account_name, "Đang chờ dừng")
        return True

    def _on_progress(self, progress_object: object) -> None:
        progress = progress_object
        self.last_progress = progress
        self.progress_bar.setRange(0, max(progress.total, 1))
        self.progress_bar.set_animated_value(progress.attempted)
        details = (
            f"{progress.completed}/{progress.total} thành công · "
            f"{progress.failed} thất bại"
        )
        if progress.skipped:
            details += f" · {progress.skipped} bỏ qua"
        elif progress.remaining:
            details += f" · còn {progress.remaining}"
        self.progress_numbers.setText(details)
        self.current_label.setText(
            "Hiện tại: "
            f"{progress.current_listing_title or 'Chưa có phòng'} · "
            f"{progress.current_group_name or 'Chưa có nhóm'}"
        )
        next_text = progress.next_listing_title or "Không còn bài nào"
        if progress.next_group_name:
            next_text += f" · {progress.next_group_name}"
        self.next_label.setText(f"Tiếp theo: {next_text}")
        self._append_log(progress.message)

    def _on_result(self, result_object: object) -> None:
        entry = result_object
        if not isinstance(entry, PostingResultEntry):
            return
        self.result_entries.append(entry)
        self._update_results_button()
        if self._results_dialog is not None:
            self._results_dialog.set_entries(self.result_entries)

    def _on_worker_finished(self, results_object: object) -> None:
        entries = list(results_object)
        current_run_entries = self.result_entries[
            self._run_result_start_index:
        ]
        if entries != current_run_entries:
            self._render_results(
                self.result_entries[:self._run_result_start_index] + entries
            )
        was_stopped = bool(
            self.last_progress is not None and self.last_progress.stopped
        )
        self._completion_status = "Đã dừng" if was_stopped else "Hoàn tất"
        successful = sum(1 for entry in entries if entry.result.success)
        run_total = (
            self.last_progress.total
            if self.last_progress is not None
            else self._run_total_attempts
        )
        if was_stopped:
            self._append_log(
                f"Đã dừng: {len(entries)}/{run_total} lượt đã xử lý · "
                f"{successful} lượt thành công."
            )
        else:
            self._append_log(
                f"Đã hoàn tất: {successful}/{run_total} lượt thành công."
            )
        self._append_run_footer(
            "ĐÃ DỪNG" if was_stopped else "HOÀN TẤT",
            entries,
            run_total,
        )

    def _on_worker_error(self, message: str) -> None:
        self._completion_status = "Lỗi"
        log_message = f"Đã dừng vì lỗi: {message}"
        if self.last_progress is None or self.last_progress.message != log_message:
            self._append_log(log_message)
        self._append_run_footer(
            "LỖI",
            self.result_entries[self._run_result_start_index:],
            self._run_total_attempts,
        )
        QMessageBox.critical(
            self,
            f"{self.account.display_name} đã dừng vì có lỗi",
            message,
        )

    def _on_thread_finished(self) -> None:
        self._run_active = False
        if self._thread is not None:
            self._retired_threads.append(self._thread)
        self._thread = None
        self._worker = None
        self._stop_pending = False
        self._set_running(False)

    def _set_running(self, running: bool) -> None:
        self.stop_button.setEnabled(running and not self._stop_pending)
        self.stop_button.setText(
            "Đang chờ dừng…" if self._stop_pending else "Dừng đăng bài"
        )
        self.plan_button.setEnabled(not running and self._available_listing_count > 0)
        status_text = (
            "Đang chờ dừng"
            if running and self._stop_pending
            else "Đang chạy"
            if running
            else self._completion_status
        )
        self.status_label.set_state(
            status_text,
            "warning"
            if running and self._stop_pending
            else "running"
            if running
            else (
                "done"
                if self._completion_status == "Hoàn tất"
                else "error"
                if self._completion_status == "Lỗi"
                else "warning"
                if self._completion_status in {"Chưa đăng nhập", "Đã dừng"}
                else "ready"
            ),
        )
        self._update_action_availability(running)
        self.running_changed.emit(self.account_name, running)
        self.status_changed.emit(self.account_name, status_text)

    def _update_action_availability(self, running: bool | None = None) -> None:
        running = self.is_running if running is None else running
        self.plan_button.setEnabled(
            not running and self._available_listing_count > 0
        )
        self.start_button.setEnabled(
            not running and self.session_available and bool(self.tasks)
        )
        if not self.session_available:
            self.start_button.setToolTip(
                "Đăng nhập tài khoản trước khi bắt đầu đăng bài."
            )
        elif not self.tasks:
            self.start_button.setToolTip(
                "Chọn phòng và nhóm trước khi bắt đầu."
            )
        else:
            self.start_button.setToolTip("")

    def _open_results(self) -> None:
        if self._results_dialog is None:
            self._results_dialog = PostingResultsDialog(
                self.account.display_name,
                self.listing_service,
                self.result_entries,
                parent=self,
            )
            self._results_dialog.finished.connect(self._release_results_dialog)
        else:
            self._results_dialog.set_entries(self.result_entries)
        self._results_dialog.show()
        self._results_dialog.raise_()
        self._results_dialog.activateWindow()

    def _release_results_dialog(self, _result: int) -> None:
        if self._results_dialog is not None:
            self._results_dialog.deleteLater()
            self._results_dialog = None
        self.results_button.setFocus()

    def _append_log(self, message: str) -> None:
        timestamp = QTime.currentTime().toString("HH:mm:ss")
        self.log_output.appendPlainText(f"[{timestamp}] {message}")

    def _append_run_header(self, plan: AccountPostingPlan) -> None:
        self._run_number += 1
        self._run_log_closed = False
        if self.log_output.toPlainText().strip():
            self.log_output.appendPlainText("")
        self._append_run_separator(f"LẦN CHẠY {self._run_number:02d}")
        self._append_log(
            f"Tài khoản: {self.account.display_name} · "
            f"phiên đăng nhập {self.account_name}"
        )
        group_count = sum(len(task.group_targets) for task in plan.tasks)
        self._append_log(
            f"Kế hoạch: {len(plan.tasks)} phòng · "
            f"{group_count} nhóm · {plan.total_attempts} lượt"
        )
        for index, task in enumerate(plan.tasks, start=1):
            self._append_log(
                f"Phòng {index}/{len(plan.tasks)}: {task.listing_title} · "
                f"{len(task.group_targets)} nhóm · "
                f"{task.total_attempts} lượt"
            )
            groups = "; ".join(
                f"{task.group_name_for(target.url)} ×{target.target_count}"
                for target in task.group_targets
            )
            self._append_log(f"Nhóm: {groups}")
        self._append_log("Bắt đầu đăng theo kế hoạch.")

    def _append_run_footer(
        self,
        status: str,
        entries: list[PostingResultEntry],
        run_total: int,
    ) -> None:
        if self._run_log_closed:
            return
        linked_success = sum(
            1
            for entry in entries
            if entry.result.success and entry.result.post_url
        )
        interrupted = sum(
            1
            for entry in entries
            if entry.result.success and not entry.result.post_url
        )
        failed = sum(1 for entry in entries if not entry.result.success)
        remaining = max(run_total - len(entries), 0)
        self._append_log(
            f"Kết quả: {len(entries)}/{run_total} lượt đã xử lý · "
            f"{linked_success} thành công · {interrupted} thiếu liên kết · "
            f"{failed} thất bại · {remaining} chưa đăng"
        )
        self._append_run_separator(
            f"KẾT THÚC {self._run_number:02d} · {status}"
        )
        self._run_log_closed = True

    def _append_run_separator(self, label: str) -> None:
        self.log_output.appendPlainText(f"============ {label} ============")

    def _render_results(self, entries: list[PostingResultEntry]) -> None:
        self.result_entries = list(entries)
        self._update_results_button()
        if self._results_dialog is not None:
            self._results_dialog.set_entries(self.result_entries)

    def _update_results_button(self) -> None:
        count = len(self.result_entries)
        self.results_button.setText(
            f"Kết quả ({count})" if count else "Kết quả"
        )
