from PySide6.QtCore import Qt, QThread, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from facebook.group_metadata import GroupMetadata
from gui.workers.group_metadata_worker import GroupMetadataWorker
from models.saved_group import SavedGroup
from services.group_service import GroupService
from services.facebook_account_service import FacebookAccountService
from session_manager import list_sessions


class GroupDialog(QDialog):
    def __init__(
        self,
        group_service: GroupService,
        group: SavedGroup | None = None,
        preferred_account: str | None = None,
        auto_refresh: bool = False,
        auto_save_after_refresh: bool = False,
        account_service: FacebookAccountService | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.group_service = group_service
        self.group = group
        self.saved_group: SavedGroup | None = None
        self.metadata: GroupMetadata | None = None
        self._metadata_url: str | None = None
        self._thread: QThread | None = None
        self._worker: GroupMetadataWorker | None = None
        self._save_after_fetch = auto_save_after_refresh
        self.account_service = account_service or FacebookAccountService(
            session_lister=list_sessions,
        )

        self.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled, True)
        self.setWindowTitle(
            "Chỉnh sửa nhóm" if group else "Thêm nhóm Facebook"
        )
        self.setMinimumWidth(640)
        self.resize(700, 430)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(16)
        title = QLabel(
            "Chỉnh sửa nhóm" if group else "Thêm nhóm Facebook"
        )
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            "Chọn một tài khoản đã đăng nhập để lấy tên nhóm từ Facebook."
        )
        subtitle.setProperty("muted", True)
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        form_panel = QFrame()
        form_panel.setProperty("formSection", True)
        form_panel_layout = QVBoxLayout(form_panel)
        form_panel_layout.setContentsMargins(18, 17, 18, 18)
        form_panel_layout.setSpacing(12)
        section_title = QLabel("Thông tin nhóm")
        section_title.setObjectName("SectionTitle")
        form_panel_layout.addWidget(section_title)

        form = QFormLayout()
        form.setHorizontalSpacing(20)
        form.setVerticalSpacing(13)
        self.url_input = QLineEdit(group.url if group else "")
        self.url_input.setAttribute(
            Qt.WidgetAttribute.WA_InputMethodEnabled, True
        )
        self.url_input.setPlaceholderText(
            "https://www.facebook.com/groups/…"
        )
        self.account_combo = QComboBox()
        accounts = [
            account
            for account in self.account_service.get_all()
            if self.account_service.has_session(account.id)
        ]
        for account in accounts:
            self.account_combo.addItem(account.display_name, account.id)
        if preferred_account:
            preferred_index = self.account_combo.findData(preferred_account)
            if preferred_index >= 0:
                self.account_combo.setCurrentIndex(preferred_index)
        self.name_input = QLineEdit(group.name if group else "")
        self.name_input.setAttribute(
            Qt.WidgetAttribute.WA_InputMethodEnabled, True
        )
        self.name_input.setPlaceholderText(
            "Tên nhóm sẽ tự điền sau khi lấy từ Facebook"
        )
        self.enabled_input = QCheckBox("Cho phép chọn khi lên kế hoạch đăng")
        self.enabled_input.setChecked(group.enabled if group else True)
        form.addRow("URL nhóm *", self.url_input)
        form.addRow("Tài khoản Facebook *", self.account_combo)
        form.addRow("Tên nhóm *", self.name_input)
        form.addRow("Trạng thái", self.enabled_input)
        form_panel_layout.addLayout(form)
        root.addWidget(form_panel)

        self.status_label = QLabel(
            "Chọn tài khoản, rồi bấm “Lấy tên nhóm”."
            if accounts
            else "Chưa có tài khoản Facebook nào đăng nhập."
        )
        self.status_label.setProperty("muted", True)
        self.status_label.setWordWrap(True)
        self.fetch_button = QPushButton("Lấy tên nhóm")
        self.fetch_button.setProperty("role", "primary")
        self.fetch_button.setProperty("density", "compact")
        self.fetch_button.setEnabled(bool(accounts))
        self.fetch_button.clicked.connect(self._start_fetch)
        fetch_row = QHBoxLayout()
        fetch_row.setSpacing(12)
        fetch_row.addWidget(self.status_label, 1)
        fetch_row.addWidget(self.fetch_button)
        root.addLayout(fetch_row)
        root.addStretch()

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.save_button = self.buttons.button(
            QDialogButtonBox.StandardButton.Save
        )
        self.cancel_button = self.buttons.button(
            QDialogButtonBox.StandardButton.Cancel
        )
        self.save_button.setText("Lưu nhóm")
        self.save_button.setIcon(QIcon())
        self.save_button.setProperty("role", "primary")
        self.cancel_button.setText("Hủy")
        self.cancel_button.setIcon(QIcon())
        self.buttons.accepted.connect(self._save)
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)

        if auto_refresh:
            QTimer.singleShot(0, self._start_fetch)

    @property
    def is_fetching(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def _start_fetch(self) -> None:
        if self.is_fetching:
            return
        try:
            normalized_url = self.group_service.normalize_group_url(
                self.url_input.text()
            )
        except ValueError as error:
            QMessageBox.warning(self, "URL nhóm chưa hợp lệ", str(error))
            return
        account = str(self.account_combo.currentData() or "").strip()
        if not account:
            QMessageBox.warning(
                self,
                "Chưa chọn tài khoản Facebook",
                "Hãy chọn một tài khoản đã đăng nhập.",
            )
            return

        self.url_input.setText(normalized_url)
        self.fetch_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.account_combo.setEnabled(False)
        self.status_label.setText(
            "Đang mở Facebook để lấy tên nhóm…"
        )

        thread = QThread(self)
        worker = GroupMetadataWorker(account, normalized_url)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_metadata_ready)
        worker.error.connect(self._on_metadata_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(worker.deleteLater)
        thread.finished.connect(self._on_fetch_thread_finished)
        thread.finished.connect(thread.deleteLater)
        self._thread = thread
        self._worker = worker
        thread.start()

    def _on_metadata_ready(self, metadata_object: object) -> None:
        metadata = metadata_object
        self.metadata = metadata
        self._metadata_url = self.url_input.text().strip()
        self.name_input.setText(metadata.name)
        self.status_label.setText("Đã cập nhật tên nhóm.")

    def _on_metadata_error(self, message: str) -> None:
        self._metadata_url = self.url_input.text().strip()
        self._save_after_fetch = False
        self.status_label.setText(
            "Không lấy được tên nhóm. Hãy kiểm tra đăng nhập "
            "hoặc nhập tên nhóm thủ công."
        )
        QMessageBox.warning(self, "Không thể đọc tên nhóm", message)

    def _on_fetch_thread_finished(self) -> None:
        should_save = self._save_after_fetch
        self._save_after_fetch = False
        self._thread = None
        self._worker = None
        self.fetch_button.setEnabled(self.account_combo.count() > 0)
        self.save_button.setEnabled(True)
        self.account_combo.setEnabled(True)
        if should_save:
            QTimer.singleShot(0, self._save)

    def _save(self) -> None:
        if self.is_fetching:
            return
        try:
            normalized_url = self.group_service.normalize_group_url(
                self.url_input.text()
            )
            url_changed = (
                self.group is None
                or self.group.url != normalized_url
            )
            if (
                url_changed
                and self._metadata_url != normalized_url
                and self.account_combo.count() > 0
            ):
                self._save_after_fetch = True
                self._start_fetch()
                return

            name = self.name_input.text().strip()
            if not name:
                raise ValueError(
                    "Hãy lấy tên nhóm từ Facebook hoặc nhập tên thủ công."
                )
            if self.group is None:
                self.saved_group = self.group_service.create_group(
                    url=normalized_url,
                    name=name,
                    enabled=self.enabled_input.isChecked(),
                )
            else:
                self.saved_group = self.group_service.update_group(
                    self.group.id,
                    url=normalized_url,
                    name=name,
                    enabled=self.enabled_input.isChecked(),
                )
        except Exception as error:
            QMessageBox.critical(self, "Không thể lưu nhóm", str(error))
            return

        self.accept()

    def reject(self) -> None:
        if self.is_fetching:
            QMessageBox.information(
                self,
                "Đang lấy tên nhóm",
                "Ứng dụng đang lấy tên nhóm. Chờ hoàn tất rồi đóng cửa sổ.",
            )
            return
        super().reject()
