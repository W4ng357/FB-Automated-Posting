from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from gui.widgets.design_components import RoundedThumbnail, StatusBadge
from gui.workers.account_login_worker import AccountLoginWorker
from models.facebook_account import FacebookAccount
from services.facebook_account_service import FacebookAccountService


class AccountLoginDialog(QDialog):
    account_updated = Signal(object)

    def __init__(
        self,
        account_service: FacebookAccountService,
        account: FacebookAccount,
        worker_factory=AccountLoginWorker,
        auto_start: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.account_service = account_service
        self.account = account
        self.worker_factory = worker_factory
        self.updated_account: FacebookAccount | None = None
        self._thread: QThread | None = None
        self._worker: AccountLoginWorker | None = None
        self._pending_reject = False
        self._profile_saved = False
        self.browser_was_started = False

        self.setWindowTitle("Đăng nhập tài khoản Facebook")
        self.setMinimumSize(700, 520)
        self.resize(760, 570)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(16)

        title = QLabel(
            "Đồng bộ lại tài khoản"
            if account.is_synced
            else "Thêm tài khoản Facebook"
        )
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            "Ứng dụng mở Chromium với một hồ sơ riêng và chỉ lưu session trên máy này."
        )
        subtitle.setProperty("muted", True)
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        identity = QFrame()
        identity.setProperty("workspaceHeader", True)
        identity_layout = QHBoxLayout(identity)
        identity_layout.setContentsMargins(16, 14, 16, 14)
        identity_layout.setSpacing(14)
        self.avatar = RoundedThumbnail(
            account_service.get_avatar_path(account),
            account.display_name,
            circular=True,
        )
        identity_text = QVBoxLayout()
        identity_text.setSpacing(4)
        identity_name = QLabel(account.display_name)
        identity_name.setObjectName("SectionTitle")
        identity_id = QLabel(f"Phiên trình duyệt: {account.id}")
        identity_id.setProperty("meta", True)
        identity_text.addWidget(identity_name)
        identity_text.addWidget(identity_id)
        identity_layout.addWidget(self.avatar)
        identity_layout.addLayout(identity_text, 1)
        root.addWidget(identity)

        guide = QFrame()
        guide.setProperty("formSection", True)
        guide_layout = QVBoxLayout(guide)
        guide_layout.setContentsMargins(18, 17, 18, 18)
        guide_layout.setSpacing(9)
        guide_title = QLabel("Cách hoàn tất đăng nhập")
        guide_title.setObjectName("SectionTitle")
        guide_layout.addWidget(guide_title)
        for text in (
            "Đăng nhập Facebook trong cửa sổ Chromium được mở riêng.",
            "Hoàn tất mã xác minh hoặc checkpoint nếu Facebook yêu cầu.",
            "Quay lại đây và chọn “Đã đăng nhập, lấy thông tin” để lưu tên và avatar.",
        ):
            line = QLabel(text)
            line.setProperty("muted", True)
            line.setWordWrap(True)
            guide_layout.addWidget(line)
        root.addWidget(guide)

        status_row = QHBoxLayout()
        status_row.setSpacing(12)
        self.status_badge = StatusBadge("Chưa mở Chromium", "idle")
        self.status_text = QLabel(
            "Mở cửa sổ đăng nhập khi bạn đã sẵn sàng."
        )
        self.status_text.setProperty("muted", True)
        self.status_text.setWordWrap(True)
        status_row.addWidget(self.status_badge)
        status_row.addWidget(self.status_text, 1)
        root.addLayout(status_row)
        root.addStretch()

        footer = QHBoxLayout()
        footer.setSpacing(10)
        footer.addStretch()
        self.cancel_button = QPushButton("Hủy")
        self.cancel_button.clicked.connect(self.reject)
        self.launch_button = QPushButton("Mở Facebook")
        self.launch_button.clicked.connect(self._start_browser)
        self.capture_button = QPushButton("Đã đăng nhập, lấy thông tin")
        self.capture_button.setProperty("role", "primary")
        self.capture_button.setEnabled(False)
        self.capture_button.clicked.connect(self._request_profile)
        footer.addWidget(self.cancel_button)
        footer.addWidget(self.launch_button)
        footer.addWidget(self.capture_button)
        root.addLayout(footer)

        if auto_start:
            QTimer.singleShot(0, self._start_browser)

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def _start_browser(self) -> None:
        if self.is_running:
            return
        self.browser_was_started = True
        self.launch_button.setEnabled(False)
        self.capture_button.setEnabled(False)
        self.cancel_button.setText("Dừng")
        self.status_badge.set_state("Đang mở", "running")
        self.status_text.setText("Đang khởi tạo hồ sơ Chromium...")

        thread = QThread(self)
        worker = self.worker_factory(
            self.account.id,
            self.account_service.get_session_path(self.account.id),
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.started.connect(self._on_worker_started)
        worker.status_changed.connect(self._on_status_changed)
        worker.profile_ready.connect(self._on_profile_ready)
        worker.error.connect(self._on_error)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(self._on_thread_finished)
        thread.finished.connect(thread.deleteLater)
        self._thread = thread
        self._worker = worker
        thread.start()

    def _on_worker_started(self) -> None:
        self.capture_button.setEnabled(True)
        self.status_badge.set_state("Chờ đăng nhập", "running")

    def _on_status_changed(self, message: str) -> None:
        self.status_text.setText(message)
        self.status_badge.set_state("Chờ xác nhận", "warning")
        self.capture_button.setEnabled(True)

    def _request_profile(self) -> None:
        if self._worker is None:
            return
        self.capture_button.setEnabled(False)
        self.status_badge.set_state("Đang đọc hồ sơ", "running")
        self.status_text.setText("Đang mở trang cá nhân và lấy tên, avatar...")
        self._worker.request_profile()

    def _on_profile_ready(self, metadata_object: object) -> None:
        try:
            self.updated_account = self.account_service.apply_metadata(
                self.account.id,
                metadata_object,
            )
        except Exception as error:
            self._on_error(str(error))
            return
        self._profile_saved = True
        self.status_badge.set_state("Đã đồng bộ", "success")
        self.status_text.setText(
            f"Đã lưu hồ sơ Facebook của {self.updated_account.facebook_name}."
        )
        self.account_updated.emit(self.updated_account)

    def _on_error(self, message: str) -> None:
        self.status_badge.set_state("Có lỗi", "error")
        self.status_text.setText(
            f"{message}\nKiểm tra cửa sổ Facebook rồi thử lại."
        )

    def _on_thread_finished(self) -> None:
        self._thread = None
        self._worker = None
        self.launch_button.setEnabled(True)
        self.capture_button.setEnabled(False)
        self.cancel_button.setText("Hủy")
        if self._profile_saved:
            self.accept()
        elif self._pending_reject:
            super().reject()
        else:
            self.status_badge.set_state("Đã đóng Chromium", "idle")

    def reject(self) -> None:
        if self.is_running and self._worker is not None:
            self._pending_reject = True
            self.cancel_button.setEnabled(False)
            self.capture_button.setEnabled(False)
            self.status_text.setText("Đang đóng Chromium an toàn...")
            self._worker.cancel()
            return
        super().reject()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.is_running:
            event.ignore()
            self.reject()
            return
        super().closeEvent(event)
