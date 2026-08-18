from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QSize, QThread, QTime, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gui.dialogs.group_selector_dialog import GroupSelectorDialog
from gui.widgets.design_components import (
    EmptyState,
    RoundedThumbnail,
    SmoothProgressBar,
    StatusBadge,
)
from gui.widgets.posting_task_card import PostingTaskCard
from gui.widgets.result_card import ResultCard
from gui.workers.posting_worker import PostingWorker
from models.account_posting_plan import AccountPostingPlan
from models.facebook_account import FacebookAccount
from models.listing_posting_task import ListingPostingTask
from models.posting_progress import PostingProgress
from models.posting_result_entry import PostingResultEntry
from services.group_service import GroupService
from services.facebook_account_service import FacebookAccountService
from services.listing_service import ListingService
from session_manager import get_session


class AccountPostingTab(QWidget):
    running_changed = Signal(str, bool)
    status_changed = Signal(str, str)
    queue_changed = Signal(str)

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
        self._worker: PostingWorker | None = None
        self._stop_pending = False
        self._run_total_attempts = 0
        self._completion_status = (
            "Sẵn sàng" if self.session_available else "Chưa đăng nhập"
        )
        self.last_progress: PostingProgress | None = None
        self.result_entries: list[PostingResultEntry] = []
        self.queue_empty_state: EmptyState | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        account_scroll = QScrollArea()
        account_scroll.setWidgetResizable(True)
        account_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 18, 10, 20)
        content_layout.setSpacing(16)
        content_layout.addWidget(self._create_account_header())
        content_layout.addWidget(self._create_progress_panel())
        content_layout.addWidget(self._create_queue_panel())
        content_layout.addWidget(self._create_activity_panel())
        content_layout.addStretch()
        account_scroll.setWidget(content)
        root.addWidget(account_scroll)
        self.refresh_available_data()
        self._render_queue()
        self._render_results([])

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    @property
    def total_attempts(self) -> int:
        return sum(task.total_attempts for task in self.tasks)

    def _create_account_header(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("workspaceHeader", True)
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)
        self.account_avatar = RoundedThumbnail(
            self.avatar_path,
            self.account.display_name,
            QSize(54, 54),
            circular=True,
        )
        heading = QVBoxLayout()
        heading.setSpacing(4)
        self.account_title = QLabel(self.account.display_name)
        self.account_title.setObjectName("SectionTitle")
        self.account_hint = QLabel(self._account_hint_text())
        self.account_hint.setProperty("muted", True)
        self.account_hint.setWordWrap(True)
        heading.addWidget(self.account_title)
        heading.addWidget(self.account_hint)
        self.status_label = StatusBadge(
            self._completion_status,
            "idle" if self.session_available else "warning",
        )
        self.start_button = QPushButton("Bắt đầu tài khoản")
        self.start_button.setProperty("role", "primary")
        self.start_button.setMinimumHeight(42)
        self.start_button.setEnabled(self.session_available)
        if not self.session_available:
            self.start_button.setToolTip(
                "Hãy đăng nhập tài khoản trước khi bắt đầu đăng bài."
            )
        self.start_button.clicked.connect(self.start)
        self.stop_button = QPushButton("Dừng đăng bài")
        self.stop_button.setProperty("role", "danger")
        self.stop_button.setMinimumHeight(42)
        self.stop_button.setEnabled(False)
        self.stop_button.setToolTip(
            "Dừng tại khoảng chờ an toàn sau khi bài hiện tại hoàn tất."
        )
        self.stop_button.clicked.connect(self.stop)
        layout.addWidget(self.account_avatar)
        layout.addLayout(heading, 1)
        layout.addWidget(self.status_label)
        layout.addWidget(self.stop_button)
        layout.addWidget(self.start_button)
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
        self.account_avatar.set_source(
            avatar_path,
            account.display_name,
        )
        self.account_title.setText(account.display_name)
        self.account_hint.setText(self._account_hint_text())
        self.start_button.setEnabled(
            session_available and not self.is_running
        )
        self.start_button.setToolTip(
            ""
            if session_available
            else "Hãy đăng nhập tài khoản trước khi bắt đầu đăng bài."
        )
        if not self.is_running and self._completion_status in {
            "Sẵn sàng",
            "Chưa đăng nhập",
        }:
            self._completion_status = (
                "Sẵn sàng" if session_available else "Chưa đăng nhập"
            )
            self.status_label.set_state(
                self._completion_status,
                "idle" if session_available else "warning",
            )

    def _account_hint_text(self) -> str:
        if self.account.alias.strip() and self.account.facebook_name.strip():
            identity = f"Facebook: {self.account.facebook_name.strip()}"
        elif self.account.is_synced:
            identity = f"Phiên {self.account.id}"
        else:
            identity = f"Phiên {self.account.id} · chưa đồng bộ hồ sơ"
        return f"{identity} · một kế hoạch chạy tại một thời điểm"

    def _create_queue_panel(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("section", True)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        heading = QHBoxLayout()
        title = QLabel("Hàng chờ đăng")
        title.setObjectName("SectionTitle")
        self.queue_summary = QLabel()
        self.queue_summary.setProperty("muted", True)
        heading.addWidget(title)
        heading.addStretch()
        heading.addWidget(self.queue_summary)
        layout.addLayout(heading)

        selector = QHBoxLayout()
        self.listing_combo = QComboBox()
        self.listing_combo.setMinimumWidth(280)
        add_button = QPushButton("Thêm vào hàng chờ")
        add_button.setProperty("density", "compact")
        add_button.clicked.connect(self._add_task)
        self.add_task_button = add_button
        selector.addWidget(self.listing_combo, 1)
        selector.addWidget(add_button)
        layout.addLayout(selector)

        self.queue_container = QWidget()
        self.queue_layout = QVBoxLayout(self.queue_container)
        self.queue_layout.setContentsMargins(0, 0, 0, 0)
        self.queue_layout.setSpacing(9)
        layout.addWidget(self.queue_container)
        return panel

    def _create_progress_panel(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("progressCard", True)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 17, 18, 17)
        layout.setSpacing(10)
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
        current_caption = QLabel("Đang xử lý")
        current_caption.setProperty("meta", True)
        self.current_label = QLabel("Chưa bắt đầu")
        self.current_label.setProperty("progressDetail", True)
        self.current_label.setWordWrap(True)
        next_caption = QLabel("Tiếp theo")
        next_caption.setProperty("meta", True)
        self.next_label = QLabel("Chưa có lượt tiếp theo")
        self.next_label.setProperty("progressDetail", True)
        self.next_label.setWordWrap(True)
        details = QHBoxLayout()
        details.setSpacing(28)
        current = QVBoxLayout()
        current.setSpacing(3)
        current.addWidget(current_caption)
        current.addWidget(self.current_label)
        upcoming = QVBoxLayout()
        upcoming.setSpacing(3)
        upcoming.addWidget(next_caption)
        upcoming.addWidget(self.next_label)
        details.addLayout(current, 1)
        details.addLayout(upcoming, 1)
        layout.addLayout(row)
        layout.addWidget(self.progress_bar)
        layout.addLayout(details)
        return panel

    def _create_activity_panel(self) -> QTabWidget:
        tabs = QTabWidget()
        tabs.setObjectName("ActivityTabs")
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setProperty("terminal", True)
        self.log_output.setPlaceholderText(
            "Nhật ký của tài khoản sẽ xuất hiện tại đây."
        )
        self.log_output.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.results_scroll = QScrollArea()
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(10, 10, 10, 10)
        self.results_layout.setSpacing(9)
        self.results_scroll.setWidget(self.results_container)
        tabs.addTab(self.log_output, "Nhật ký hoạt động")
        self.results_tab_index = tabs.addTab(
            self.results_scroll,
            "Kết quả",
        )
        self.activity_tabs = tabs
        tabs.setMinimumHeight(250)
        return tabs

    def refresh_available_data(self) -> None:
        current_id = self.listing_combo.currentData()
        queued_ids = {task.listing_id for task in self.tasks}
        try:
            listings = [
                listing
                for listing in self.listing_service.get_all()
                if listing.enabled and listing.id not in queued_ids
            ]
        except Exception as error:
            listings = []
            self._append_log(f"Không tải được danh sách phòng: {error}")
        self.listing_combo.clear()
        for listing in listings:
            self.listing_combo.addItem(
                f"{listing.id} · {listing.title}", listing.id
            )
        if not listings:
            self.listing_combo.addItem(
                "Không còn phòng khả dụng", None
            )
        if current_id is not None:
            index = self.listing_combo.findData(current_id)
            if index >= 0:
                self.listing_combo.setCurrentIndex(index)
        self.add_task_button.setEnabled(bool(listings) and not self.is_running)
        if self.queue_empty_state is not None:
            self.queue_empty_state.action_button.setEnabled(
                bool(listings) and not self.is_running
            )

    def _add_task(self) -> None:
        listing_id = self.listing_combo.currentData()
        if not listing_id:
            QMessageBox.information(
                self,
                "Không có phòng khả dụng",
                "Hãy tạo và bật ít nhất một phòng trước.",
            )
            return
        listing = self.listing_service.get_by_id(listing_id)
        if listing is None:
            self.refresh_available_data()
            return
        selector = GroupSelectorDialog(
            self.group_service,
            preferred_account=self.account_name,
            account_service=self.account_service,
            parent=self,
        )
        if selector.exec() != QDialog.DialogCode.Accepted:
            return
        targets, names = selector.selected_targets()
        self.tasks.append(
            ListingPostingTask(
                listing_id=listing.id,
                listing_title=listing.title,
                group_targets=targets,
                group_names=names,
            )
        )
        self._render_queue()
        self.refresh_available_data()
        self.queue_changed.emit(self.account_name)

    def _edit_task(self, listing_id: str) -> None:
        task = next(
            (task for task in self.tasks if task.listing_id == listing_id),
            None,
        )
        if task is None:
            return
        counts = {
            target.url: target.target_count
            for target in task.group_targets
        }
        selector = GroupSelectorDialog(
            self.group_service,
            selected_counts=counts,
            preferred_account=self.account_name,
            account_service=self.account_service,
            parent=self,
        )
        if selector.exec() != QDialog.DialogCode.Accepted:
            return
        targets, names = selector.selected_targets()
        task.group_targets = targets
        task.group_names = names
        self._render_queue()
        self.queue_changed.emit(self.account_name)

    def _remove_task(self, listing_id: str) -> None:
        self.tasks = [
            task for task in self.tasks if task.listing_id != listing_id
        ]
        self._render_queue()
        self.refresh_available_data()
        self.queue_changed.emit(self.account_name)

    def _render_queue(self) -> None:
        while self.queue_layout.count():
            item = self.queue_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self.queue_empty_state = None
        if not self.tasks:
            self.queue_empty_state = EmptyState(
                "Hàng chờ đang trống",
                "Thêm một phòng, chọn nhóm và số lượt đăng để bắt đầu.",
                "Thêm phòng vào hàng chờ",
            )
            self.queue_empty_state.action_requested.connect(self._add_task)
            self.queue_empty_state.action_button.setEnabled(
                self.listing_combo.currentData() is not None
                and not self.is_running
            )
            self.queue_layout.addWidget(self.queue_empty_state)
        else:
            for task in self.tasks:
                card = PostingTaskCard(task)
                card.edit_requested.connect(self._edit_task)
                card.remove_requested.connect(self._remove_task)
                card.setEnabled(not self.is_running)
                self.queue_layout.addWidget(card)
        self.queue_layout.addStretch()
        self.queue_summary.setText(
            f"{len(self.tasks)} phòng · {self.total_attempts} lượt"
        )

    def start(self) -> bool:
        if self.is_running:
            return False
        if not self.session_available:
            QMessageBox.warning(
                self,
                "Tài khoản chưa đăng nhập",
                "Hãy đăng nhập tài khoản Facebook này trước khi bắt đầu.",
            )
            return False
        if not self.tasks:
            QMessageBox.warning(
                self,
                "Hàng chờ đang trống",
                f"Hãy thêm ít nhất một phòng cho tài khoản {self.account_name}.",
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

        self._render_results([])
        self._stop_pending = False
        self._run_total_attempts = plan.total_attempts
        self.last_progress = None
        self._append_log(
            f"Bắt đầu kế hoạch gồm {len(self.tasks)} phòng "
            f"và {plan.total_attempts} lượt."
        )
        self._set_running(True)
        thread = QThread(self)
        worker = self.worker_factory(session_path, plan)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.started.connect(
            lambda: self._append_log("Đã khởi động bộ máy đăng bài.")
        )
        worker.progress.connect(self._on_progress)
        worker.result.connect(self._on_result)
        worker.finished.connect(self._on_worker_finished)
        worker.error.connect(self._on_worker_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(worker.deleteLater)
        thread.finished.connect(self._on_thread_finished)
        thread.finished.connect(thread.deleteLater)
        self._thread = thread
        self._worker = worker
        thread.start()
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
            "Đã nhận yêu cầu dừng. Bài đang đăng sẽ hoàn tất trước khi dừng."
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
            f"{progress.current_listing_title or 'Chưa có phòng'} · "
            f"{progress.current_group_name or 'Chưa có nhóm'}"
        )
        self.next_label.setText(
            f"{progress.next_listing_title or 'Không còn lượt chờ'}"
            + (
                f" · {progress.next_group_name}"
                if progress.next_group_name
                else ""
            )
        )
        self._append_log(progress.message)

    def _on_result(self, result_object: object) -> None:
        entry = result_object
        if not isinstance(entry, PostingResultEntry):
            return
        if not self.result_entries:
            self._clear_results()
            self.results_layout.addStretch()
        self.result_entries.append(entry)
        insert_at = max(self.results_layout.count() - 1, 0)
        self.results_layout.insertWidget(insert_at, ResultCard(entry))
        self._update_results_tab_label()

    def _on_worker_finished(self, results_object: object) -> None:
        entries = list(results_object)
        if entries != self.result_entries:
            self._render_results(entries)
        was_stopped = bool(
            self.last_progress is not None
            and self.last_progress.stopped
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
                f"Đã dừng an toàn: {len(entries)}/{run_total} "
                f"lượt đã xử lý, {successful} lượt thành công."
            )
        else:
            self._append_log(
                f"Kết thúc: {successful}/{run_total} "
                "lượt thành công."
            )

    def _on_worker_error(self, message: str) -> None:
        self._completion_status = "Lỗi"
        log_message = f"Đã dừng vì lỗi: {message}"
        if (
            self.last_progress is None
            or self.last_progress.message != log_message
        ):
            self._append_log(log_message)
        QMessageBox.critical(
            self,
            f"Tài khoản {self.account_name} gặp lỗi",
            message,
        )

    def _on_thread_finished(self) -> None:
        self._thread = None
        self._worker = None
        self._stop_pending = False
        self._set_running(False)

    def _set_running(self, running: bool) -> None:
        self.start_button.setEnabled(
            not running and self.session_available
        )
        self.stop_button.setEnabled(running and not self._stop_pending)
        self.stop_button.setText(
            "Đang chờ dừng…" if self._stop_pending else "Dừng đăng bài"
        )
        self.listing_combo.setEnabled(not running)
        self.add_task_button.setEnabled(
            not running and self.listing_combo.count() > 0
        )
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
                if self._completion_status in {
                    "Chưa đăng nhập",
                    "Đã dừng",
                }
                else "idle"
            ),
        )
        self._render_queue()
        self.running_changed.emit(self.account_name, running)
        self.status_changed.emit(
            self.account_name,
            status_text,
        )

    def _append_log(self, message: str) -> None:
        timestamp = QTime.currentTime().toString("HH:mm:ss")
        self.log_output.appendPlainText(f"[{timestamp}] {message}")

    def _clear_results(self) -> None:
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _render_results(self, entries: list) -> None:
        self.result_entries = list(entries)
        self._clear_results()
        if not entries:
            empty = EmptyState(
                "Chưa có kết quả",
                "Kết quả của lần chạy sẽ xuất hiện tại đây.",
            )
            self.results_layout.addWidget(empty)
        else:
            for entry in entries:
                self.results_layout.addWidget(ResultCard(entry))
        self.results_layout.addStretch()
        self._update_results_tab_label()

    def _update_results_tab_label(self) -> None:
        count = len(self.result_entries)
        self.activity_tabs.setTabText(
            self.results_tab_index,
            f"Kết quả ({count})" if count else "Kết quả",
        )
