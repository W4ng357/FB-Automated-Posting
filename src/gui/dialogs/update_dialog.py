"""Update Dialog for checking and applying application updates from GitHub Releases."""

from __future__ import annotations

import html

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from services.update_service import ReleaseInfo, UpdateService
from version import APP_VERSION


class CheckUpdateWorker(QThread):
    finished_signal = Signal(object, str)  # (ReleaseInfo | None, error_str)

    def __init__(self, update_service: UpdateService) -> None:
        super().__init__()
        self.update_service = update_service

    def run(self) -> None:
        try:
            release = self.update_service.check_for_updates()
            self.finished_signal.emit(release, "")
        except Exception as error:
            self.finished_signal.emit(None, str(error))


class DownloadUpdateWorker(QThread):
    progress_signal = Signal(int, int)  # (downloaded, total)
    finished_signal = Signal(bool, str)  # (success, error_str)

    def __init__(
        self,
        update_service: UpdateService,
        release: ReleaseInfo,
    ) -> None:
        super().__init__()
        self.update_service = update_service
        self.release = release

    def run(self) -> None:
        try:
            def on_progress(downloaded: int, total: int) -> None:
                self.progress_signal.emit(downloaded, total)

            success = self.update_service.download_and_apply_update(
                self.release,
                progress_callback=on_progress,
            )
            self.finished_signal.emit(success, "")
        except Exception as error:
            self.finished_signal.emit(False, str(error))


class UpdateDialog(QDialog):
    def __init__(
        self,
        update_service: UpdateService | None = None,
        parent=None,
        auto_check: bool = True,
    ) -> None:
        super().__init__(parent)
        self.update_service = update_service or UpdateService()
        self.current_version = self.update_service.get_current_installed_version()
        self.latest_release: ReleaseInfo | None = None

        self.setWindowTitle("Cập nhật ứng dụng")
        self.setFixedSize(520, 420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 20)
        root.setSpacing(16)

        # Header
        header = QHBoxLayout()
        header_text = QVBoxLayout()
        header_text.setSpacing(4)
        self.title_label = QLabel("Kiểm tra cập nhật")
        self.title_label.setObjectName("DialogTitle")
        self.version_info = QLabel(f"Phiên bản hiện tại: v{self.current_version.lstrip('v')}")
        self.version_info.setProperty("muted", True)
        header_text.addWidget(self.title_label)
        header_text.addWidget(self.version_info)
        header.addLayout(header_text)
        header.addStretch()
        root.addLayout(header)

        # Content card / container
        self.content_card = QFrame()
        self.content_card.setProperty("card", True)
        card_layout = QVBoxLayout(self.content_card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        self.status_label = QLabel("Đang kết nối GitHub để kiểm tra phiên bản mới...")
        self.status_label.setWordWrap(True)
        card_layout.addWidget(self.status_label)

        # Changelog browser
        self.changelog_browser = QTextBrowser()
        self.changelog_browser.setOpenExternalLinks(True)
        self.changelog_browser.setMinimumHeight(140)
        self.changelog_browser.hide()
        card_layout.addWidget(self.changelog_browser)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        card_layout.addWidget(self.progress_bar)

        root.addWidget(self.content_card, 1)

        # Action Buttons
        self.button_box = QHBoxLayout()
        self.button_box.setSpacing(10)

        self.check_again_button = QPushButton("Kiểm tra lại")
        self.check_again_button.clicked.connect(self.start_check)
        self.check_again_button.hide()

        self.action_button = QPushButton("Cập nhật ngay")
        self.action_button.setProperty("role", "primary")
        self.action_button.setMinimumHeight(38)
        self.action_button.clicked.connect(self._on_action_clicked)
        self.action_button.hide()

        self.close_button = QPushButton("Đóng")
        self.close_button.setMinimumHeight(38)
        self.close_button.clicked.connect(self.close)

        self.button_box.addWidget(self.check_again_button)
        self.button_box.addStretch()
        self.button_box.addWidget(self.close_button)
        self.button_box.addWidget(self.action_button)
        root.addLayout(self.button_box)

        self.check_worker: CheckUpdateWorker | None = None
        self.download_worker: DownloadUpdateWorker | None = None

        if auto_check:
            self.start_check()

    def start_check(self) -> None:
        self.title_label.setText("Kiểm tra cập nhật")
        self.status_label.setText("Đang kết nối GitHub để kiểm tra phiên bản mới...")
        self.changelog_browser.hide()
        self.progress_bar.hide()
        self.action_button.hide()
        self.check_again_button.hide()
        self.close_button.setEnabled(True)

        self.check_worker = CheckUpdateWorker(self.update_service)
        self.check_worker.finished_signal.connect(self._on_check_finished)
        self.check_worker.start()

    @Slot(object, str)
    def _on_check_finished(self, release: ReleaseInfo | None, error: str) -> None:
        if error:
            self.status_label.setText(
                f"Không thể kết nối đến máy chủ cập nhật.\nChi tiết: {error}"
            )
            self.check_again_button.show()
            return

        if release is None:
            self.status_label.setText(
                f"🎉 Bạn đang sử dụng phiên bản mới nhất (v{self.current_version.lstrip('v')}).\n"
                "Không có bản cập nhật nào mới hơn."
            )
            self.check_again_button.show()
            return

        self.latest_release = release
        new_v = release.version.lstrip("v")
        size_mb = (
            f" (~{release.file_size / (1024*1024):.1f} MB)"
            if release.file_size > 0
            else " (~1-2 MB)"
        )

        self.title_label.setText("Có phiên bản mới!")
        self.status_label.setText(
            f"<b>Đã có bản cập nhật v{new_v}</b>{size_mb}<br>"
            "Nội dung thay đổi:"
        )

        # Format changelog markdown/text to HTML
        escaped_body = html.escape(release.body).replace("\n", "<br>")
        self.changelog_browser.setHtml(
            f"<div style='font-family: sans-serif; line-height: 1.5; color: #E2E8F0;'>"
            f"{escaped_body}"
            f"</div>"
        )
        self.changelog_browser.show()

        self.action_button.setText("Cập nhật ngay")
        self.action_button.show()
        self.check_again_button.hide()

    def _on_action_clicked(self) -> None:
        if self.action_button.text() == "Khởi động lại ngay":
            self.update_service.restart_application()
            return

        if self.latest_release is None:
            return

        # Start downloading
        self.status_label.setText("Đang tải gói cập nhật mã nguồn từ GitHub...")
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.action_button.setEnabled(False)
        self.close_button.setEnabled(False)
        self.check_again_button.hide()

        self.download_worker = DownloadUpdateWorker(
            self.update_service, self.latest_release
        )
        self.download_worker.progress_signal.connect(self._on_download_progress)
        self.download_worker.finished_signal.connect(self._on_download_finished)
        self.download_worker.start()

    @Slot(int, int)
    def _on_download_progress(self, downloaded: int, total: int) -> None:
        if total > 0:
            percent = int((downloaded / total) * 100)
            self.progress_bar.setValue(percent)
            dl_mb = downloaded / (1024 * 1024)
            tot_mb = total / (1024 * 1024)
            self.status_label.setText(
                f"Đang tải bản cập nhật: {dl_mb:.1f} MB / {tot_mb:.1f} MB ({percent}%)"
            )
        else:
            dl_mb = downloaded / (1024 * 1024)
            self.status_label.setText(f"Đang tải bản cập nhật: {dl_mb:.1f} MB...")

    @Slot(bool, str)
    def _on_download_finished(self, success: bool, error: str) -> None:
        self.close_button.setEnabled(True)
        if success:
            self.progress_bar.setValue(100)
            self.status_label.setText(
                "✨ <b>Cập nhật thành công!</b><br>"
                "Nhấn 'Khởi động lại ngay' để bắt đầu sử dụng phiên bản mới."
            )
            self.action_button.setText("Khởi động lại ngay")
            self.action_button.setEnabled(True)
            self.action_button.show()
        else:
            self.status_label.setText(
                f"❌ Quá trình cập nhật gặp sự cố: {error}\n"
                "Vui lòng thử lại sau."
            )
            self.action_button.setText("Thử lại")
            self.action_button.setEnabled(True)
            self.action_button.show()
