from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from gui.dialogs.account_login_dialog import AccountLoginDialog
from gui.widgets.design_components import (
    EmptyState,
    RoundedThumbnail,
    StatusBadge,
)
from models.facebook_account import FacebookAccount
from services.facebook_account_service import FacebookAccountService


class AccountCard(QFrame):
    edit_requested = Signal(str)
    sync_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(
        self,
        account_service: FacebookAccountService,
        account: FacebookAccount,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("accountCard", True)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        session_available = account_service.has_session(account.id)

        root = QHBoxLayout(self)
        root.setContentsMargins(14, 14, 16, 14)
        root.setSpacing(14)
        avatar = RoundedThumbnail(
            account_service.get_avatar_path(account),
            account.display_name,
            QSize(64, 64),
            circular=True,
        )
        root.addWidget(avatar)

        content = QVBoxLayout()
        content.setSpacing(4)
        name = QLabel(account.display_name)
        name.setObjectName("CardTitle")
        name.setWordWrap(True)
        identity = QLabel(account.identity_detail)
        identity.setProperty("muted", True)
        session = QLabel(
            f"Phiên {account.id}"
            + (
                f" · cập nhật {account.updated_at[:10]}"
                if account.updated_at
                else ""
            )
        )
        session.setProperty("meta", True)
        content.addWidget(name)
        content.addWidget(identity)
        content.addWidget(session)
        root.addLayout(content, 1)

        side = QVBoxLayout()
        side.setSpacing(9)
        if account.is_synced and session_available:
            badge = StatusBadge("Đã đồng bộ", "success")
        elif session_available:
            badge = StatusBadge("Chưa đồng bộ", "warning")
        else:
            badge = StatusBadge("Chưa đăng nhập", "warning")
        side.addWidget(badge, 0, Qt.AlignmentFlag.AlignRight)
        side.addStretch()

        actions = QHBoxLayout()
        actions.setSpacing(8)
        sync_button = QPushButton(
            "Đồng bộ lại" if session_available else "Đăng nhập"
        )
        sync_button.setProperty("density", "compact")
        sync_button.clicked.connect(
            lambda: self.sync_requested.emit(account.id)
        )
        edit_button = QPushButton("Chỉnh sửa")
        edit_button.setProperty("density", "compact")
        edit_button.clicked.connect(
            lambda: self.edit_requested.emit(account.id)
        )
        menu = QMenu(self)
        delete_action = menu.addAction("Xóa tài khoản và session")
        delete_action.triggered.connect(
            lambda _checked=False: self.delete_requested.emit(account.id)
        )
        more_button = QPushButton("Tùy chọn")
        more_button.setProperty("role", "ghost")
        more_button.setProperty("density", "compact")
        more_button.setMenu(menu)
        actions.addWidget(sync_button)
        actions.addWidget(edit_button)
        actions.addWidget(more_button)
        side.addLayout(actions)
        root.addLayout(side)


class AccountEditDialog(QDialog):
    def __init__(
        self,
        account_service: FacebookAccountService,
        account: FacebookAccount,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.account_service = account_service
        self.account = account
        self.updated_account: FacebookAccount | None = None
        self.setWindowTitle("Chỉnh sửa tài khoản")
        self.setMinimumWidth(600)
        self.resize(660, 360)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(14)
        title = QLabel("Chỉnh sửa tài khoản")
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            "Nhãn chỉ thay đổi cách hiển thị trong ứng dụng; "
            "session Chromium vẫn giữ nguyên."
        )
        subtitle.setProperty("muted", True)
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        panel = QFrame()
        panel.setProperty("formSection", True)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(18, 17, 18, 18)
        panel_layout.setSpacing(8)
        facebook_label = QLabel("Tên Facebook")
        self.facebook_name = QLineEdit(account.facebook_name)
        self.facebook_name.setReadOnly(True)
        self.facebook_name.setPlaceholderText("Chưa đồng bộ hồ sơ Facebook")
        alias_label = QLabel("Nhãn trong ứng dụng")
        self.alias_input = QLineEdit(account.alias)
        self.alias_input.setPlaceholderText(
            "Để trống để dùng tên Facebook"
        )
        panel_layout.addWidget(facebook_label)
        panel_layout.addWidget(self.facebook_name)
        panel_layout.addWidget(alias_label)
        panel_layout.addWidget(self.alias_input)
        root.addWidget(panel)
        root.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        save = buttons.button(QDialogButtonBox.StandardButton.Save)
        cancel = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        save.setText("Lưu thay đổi")
        save.setProperty("role", "primary")
        cancel.setText("Hủy")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _save(self) -> None:
        try:
            self.updated_account = self.account_service.update_alias(
                self.account.id,
                self.alias_input.text(),
            )
        except Exception as error:
            QMessageBox.critical(
                self,
                "Không thể lưu tài khoản",
                str(error),
            )
            return
        self.accept()


class AccountManagerDialog(QDialog):
    accounts_changed = Signal()

    def __init__(
        self,
        account_service: FacebookAccountService,
        login_dialog_factory=AccountLoginDialog,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.account_service = account_service
        self.login_dialog_factory = login_dialog_factory
        self.accounts: list[FacebookAccount] = []
        self.setWindowTitle("Quản lý tài khoản Facebook")
        self.setMinimumSize(780, 580)
        self.resize(900, 680)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(16)
        header = QHBoxLayout()
        heading = QVBoxLayout()
        heading.setSpacing(4)
        title = QLabel("Tài khoản Facebook")
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            "Mỗi tài khoản dùng một Chromium profile riêng được lưu cục bộ."
        )
        subtitle.setProperty("muted", True)
        subtitle.setWordWrap(True)
        heading.addWidget(title)
        heading.addWidget(subtitle)
        add_button = QPushButton("Thêm tài khoản")
        add_button.setProperty("role", "primary")
        add_button.setMinimumHeight(42)
        add_button.clicked.connect(self._add_account)
        header.addLayout(heading, 1)
        header.addWidget(add_button)
        root.addLayout(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.container = QWidget()
        self.accounts_layout = QVBoxLayout(self.container)
        self.accounts_layout.setContentsMargins(0, 0, 10, 0)
        self.accounts_layout.setSpacing(10)
        self.scroll.setWidget(self.container)
        root.addWidget(self.scroll, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close = buttons.button(QDialogButtonBox.StandardButton.Close)
        close.setText("Đóng")
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self._render_accounts()

    def _render_accounts(self) -> None:
        while self.accounts_layout.count():
            item = self.accounts_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        try:
            self.accounts = self.account_service.get_all()
        except Exception as error:
            empty = EmptyState(
                "Không thể tải tài khoản",
                f"{error}\nKiểm tra tệp dữ liệu rồi mở lại.",
            )
            self.accounts_layout.addWidget(empty)
            self.accounts_layout.addStretch()
            return
        if not self.accounts:
            empty = EmptyState(
                "Chưa có tài khoản Facebook",
                "Thêm tài khoản và đăng nhập để bắt đầu tạo hàng chờ đăng.",
                "Thêm tài khoản",
            )
            empty.action_requested.connect(self._add_account)
            self.accounts_layout.addWidget(empty)
        else:
            for account in self.accounts:
                card = AccountCard(self.account_service, account)
                card.sync_requested.connect(self._sync_account)
                card.edit_requested.connect(self._edit_account)
                card.delete_requested.connect(self._delete_account)
                self.accounts_layout.addWidget(card)
        self.accounts_layout.addStretch()

    def _add_account(self) -> None:
        try:
            account = self.account_service.create_pending_account()
        except Exception as error:
            QMessageBox.critical(
                self,
                "Không thể tạo tài khoản",
                str(error),
            )
            return
        dialog = self.login_dialog_factory(
            self.account_service,
            account,
            parent=self,
        )
        result = dialog.exec()
        if result != QDialog.DialogCode.Accepted:
            self.account_service.discard_if_unused(account.id)
        self._render_accounts()
        self.accounts_changed.emit()

    def _sync_account(self, account_id: str) -> None:
        account = self.account_service.get_by_id(account_id)
        if account is None:
            self._render_accounts()
            return
        dialog = self.login_dialog_factory(
            self.account_service,
            account,
            parent=self,
        )
        dialog.exec()
        self._render_accounts()
        self.accounts_changed.emit()

    def _edit_account(self, account_id: str) -> None:
        account = self.account_service.get_by_id(account_id)
        if account is None:
            self._render_accounts()
            return
        dialog = AccountEditDialog(
            self.account_service,
            account,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._render_accounts()
            self.accounts_changed.emit()

    def _delete_account(self, account_id: str) -> None:
        account = self.account_service.get_by_id(account_id)
        if account is None:
            self._render_accounts()
            return
        answer = QMessageBox.warning(
            self,
            "Xóa tài khoản Facebook",
            f"Xóa {account.display_name} khỏi ứng dụng?\n\n"
            "Thao tác này xóa cả Chromium session và avatar đã lưu trên máy.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.account_service.delete_account(account_id)
        except Exception as error:
            QMessageBox.critical(
                self,
                "Không thể xóa tài khoản",
                f"{error}\nHãy dừng tiến trình đang dùng tài khoản rồi thử lại.",
            )
            return
        self._render_accounts()
        self.accounts_changed.emit()
