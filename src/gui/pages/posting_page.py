from PySide6.QtCore import QSize, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gui.widgets.account_posting_tab import AccountPostingTab
from gui.dialogs.account_manager_dialog import AccountManagerDialog
from gui.widgets.design_components import (
    EmptyState,
    StatusBadge,
    circular_avatar_icon,
)
from services.group_service import GroupService
from services.facebook_account_service import FacebookAccountService
from services.listing_service import ListingService
from session_manager import list_sessions


class PostingPage(QWidget):
    posting_state_changed = Signal(bool)
    accounts_changed = Signal(int)

    def __init__(
        self,
        listing_service: ListingService,
        group_service: GroupService | None = None,
        account_service: FacebookAccountService | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.listing_service = listing_service
        self.group_service = group_service or GroupService()
        self.account_service = account_service or FacebookAccountService(
            session_lister=list_sessions,
        )
        self.account_tabs: dict[str, AccountPostingTab] = {}
        self.account_statuses: dict[str, str] = {}
        self.session_error: str | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(16)
        header = QHBoxLayout()
        heading = QVBoxLayout()
        title = QLabel("Đăng bài")
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            "Mỗi tài khoản có hàng chờ, tiến trình, nhật ký và kết quả riêng."
        )
        subtitle.setProperty("muted", True)
        subtitle.setWordWrap(True)
        heading.addWidget(title)
        heading.addWidget(subtitle)
        manage_button = QPushButton("Quản lý tài khoản")
        manage_button.clicked.connect(self._manage_accounts)
        refresh_button = QPushButton("Làm mới dữ liệu")
        refresh_button.clicked.connect(self.refresh_data)
        self.start_all_button = QPushButton("Bắt đầu tất cả")
        self.start_all_button.setProperty("role", "primary")
        self.start_all_button.setMinimumHeight(42)
        self.start_all_button.clicked.connect(self.start_all)
        header.addLayout(heading)
        header.addStretch()
        header.addWidget(manage_button)
        header.addWidget(refresh_button)
        header.addWidget(self.start_all_button)
        root.addLayout(header)

        self.overview = QWidget()
        self.overview.setProperty("overview", True)
        overview_layout = QHBoxLayout(self.overview)
        overview_layout.setContentsMargins(16, 12, 16, 12)
        self.accounts_summary = QLabel()
        self.queue_summary = QLabel()
        self.run_summary = StatusBadge("", "idle")
        self.accounts_summary.setProperty("overviewStrong", True)
        self.queue_summary.setProperty("muted", True)
        overview_layout.addWidget(self.accounts_summary)
        overview_layout.addSpacing(20)
        overview_layout.addWidget(self.queue_summary)
        overview_layout.addStretch()
        overview_layout.addWidget(self.run_summary)
        root.addWidget(self.overview)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("AccountTabs")
        self.tabs.setIconSize(QSize(22, 22))
        self.empty_panel = EmptyState(
            "Chưa có tài khoản Facebook",
            "Thêm tài khoản và đăng nhập ngay trong ứng dụng để bắt đầu.",
            "Thêm tài khoản",
        )
        self.empty_panel.action_requested.connect(self._manage_accounts)
        root.addWidget(self.empty_panel, 1)
        root.addWidget(self.tabs, 1)
        self.refresh_data()

    @property
    def is_running(self) -> bool:
        return any(tab.is_running for tab in self.account_tabs.values())

    def refresh_data(self) -> None:
        try:
            accounts = self.account_service.get_all()
            self.session_error = None
        except Exception as error:
            accounts = []
            self.session_error = str(error)
        account_ids = {account.id for account in accounts}
        for account in list(self.account_tabs):
            tab = self.account_tabs[account]
            if account not in account_ids and not tab.is_running:
                index = self.tabs.indexOf(tab)
                if index >= 0:
                    self.tabs.removeTab(index)
                tab.deleteLater()
                del self.account_tabs[account]
                self.account_statuses.pop(account, None)

        for account in accounts:
            avatar_path = self.account_service.get_avatar_path(account)
            session_available = self.account_service.has_session(account.id)
            if account.id in self.account_tabs:
                tab = self.account_tabs[account.id]
                previous_status = self.account_statuses.get(account.id)
                tab.update_account(
                    account,
                    avatar_path,
                    session_available,
                )
                if previous_status in {"Sẵn sàng", "Chưa đăng nhập", None}:
                    self.account_statuses[account.id] = (
                        "Sẵn sàng"
                        if session_available
                        else "Chưa đăng nhập"
                    )
                tab.refresh_available_data()
                self._update_tab_identity(account.id)
                continue
            tab = AccountPostingTab(
                account,
                self.listing_service,
                self.group_service,
                account_service=self.account_service,
                avatar_path=avatar_path,
                session_available=session_available,
            )
            tab.running_changed.connect(self._on_running_changed)
            tab.status_changed.connect(self._on_status_changed)
            tab.queue_changed.connect(lambda _account: self._update_overview())
            self.account_tabs[account.id] = tab
            initial_status = (
                "Sẵn sàng" if session_available else "Chưa đăng nhập"
            )
            self.account_statuses[account.id] = initial_status
            self.tabs.addTab(
                tab,
                self._account_icon(account),
                f"{account.display_name} · {initial_status}",
            )
            self.tabs.setTabToolTip(
                self.tabs.indexOf(tab),
                self._account_tooltip(account),
            )
        has_accounts = bool(self.account_tabs)
        self.tabs.setVisible(has_accounts)
        self.empty_panel.setVisible(not has_accounts)
        if self.session_error:
            self.empty_panel.set_content(
                "Không thể đọc phiên Facebook",
                f"{self.session_error}\nKiểm tra dữ liệu tài khoản rồi thử lại.",
            )
        else:
            self.empty_panel.set_content(
                "Chưa có tài khoản Facebook",
                "Thêm tài khoản và đăng nhập ngay trong ứng dụng để bắt đầu.",
            )
        self._update_overview()
        self.accounts_changed.emit(len(self.account_tabs))

    def refresh_listings(self) -> None:
        for tab in self.account_tabs.values():
            tab.refresh_available_data()
        self._update_overview()

    def refresh_groups(self) -> None:
        self._update_overview()

    def start_all(self) -> None:
        for tab in self.account_tabs.values():
            if tab.tasks and tab.session_available and not tab.is_running:
                tab.start()
        self._update_overview()

    def _on_running_changed(self, account: str, running: bool) -> None:
        self.posting_state_changed.emit(self.is_running)
        self.start_all_button.setEnabled(
            any(
                tab.tasks and tab.session_available and not tab.is_running
                for tab in self.account_tabs.values()
            )
        )
        self._update_overview()

    def _on_status_changed(self, account: str, status: str) -> None:
        self.account_statuses[account] = status
        tab = self.account_tabs.get(account)
        if tab is not None:
            index = self.tabs.indexOf(tab)
            if index >= 0:
                profile = self.account_service.get_by_id(account)
                display_name = profile.display_name if profile else account
                self.tabs.setTabText(
                    index,
                    f"{display_name} · {status}",
                )
        self._update_overview()

    def _update_overview(self) -> None:
        account_count = len(self.account_tabs)
        task_count = sum(
            len(tab.tasks) for tab in self.account_tabs.values()
        )
        attempt_count = sum(
            tab.total_attempts for tab in self.account_tabs.values()
        )
        running_count = sum(
            1 for tab in self.account_tabs.values() if tab.is_running
        )
        pending_count = sum(
            1
            for tab in self.account_tabs.values()
            if not tab.session_available
        )
        ready_count = account_count - running_count - pending_count
        self.accounts_summary.setText(f"{account_count} tài khoản")
        self.queue_summary.setText(
            f"{task_count} phòng trong hàng chờ · {attempt_count} lượt dự kiến"
        )
        run_parts = [f"{running_count} đang chạy"]
        if ready_count:
            run_parts.append(f"{ready_count} sẵn sàng")
        if pending_count:
            run_parts.append(f"{pending_count} cần đăng nhập")
        self.run_summary.set_state(
            " · ".join(run_parts),
            "running" if running_count else "warning" if pending_count else "idle",
        )
        self.start_all_button.setEnabled(
            any(
                tab.tasks and not tab.is_running
                and tab.session_available
                for tab in self.account_tabs.values()
            )
        )

    def _manage_accounts(self) -> None:
        dialog = AccountManagerDialog(
            self.account_service,
            parent=self,
        )
        dialog.accounts_changed.connect(self.refresh_data)
        dialog.exec()
        self.refresh_data()

    def _update_tab_identity(self, account_id: str) -> None:
        tab = self.account_tabs.get(account_id)
        account = self.account_service.get_by_id(account_id)
        if tab is None or account is None:
            return
        index = self.tabs.indexOf(tab)
        if index < 0:
            return
        status = self.account_statuses.get(account_id, "Sẵn sàng")
        self.tabs.setTabText(
            index,
            f"{account.display_name} · {status}",
        )
        self.tabs.setTabIcon(index, self._account_icon(account))
        self.tabs.setTabToolTip(index, self._account_tooltip(account))

    def _account_icon(self, account):
        avatar_path = self.account_service.get_avatar_path(account)
        return circular_avatar_icon(avatar_path, self.tabs.iconSize())

    @staticmethod
    def _account_tooltip(account) -> str:
        identity = account.facebook_name.strip() or "Chưa đồng bộ tên Facebook"
        return f"{identity}\nPhiên cục bộ: {account.id}"
