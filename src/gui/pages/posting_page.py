from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from gui.dialogs.account_manager_dialog import AccountManagerDialog
from gui.dialogs.posting_plan_dialog import PostingPlanDialog
from gui.widgets.account_posting_tab import AccountPostingTab
from gui.widgets.design_components import (
    EmptyState,
    StatusBadge,
    circular_avatar_icon,
)
from services.facebook_account_service import FacebookAccountService
from services.group_service import GroupService
from services.listing_service import ListingService
from session_manager import list_sessions


class AccountRailButton(QPushButton):
    def __init__(self, account_id: str, parent=None) -> None:
        super().__init__(parent)
        self.account_id = account_id
        self.setCheckable(True)
        self.setProperty("accountRail", True)
        self.setIconSize(QSize(38, 38))
        self.setMinimumHeight(64)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

    def update_identity(self, display_name: str, status: str, icon) -> None:
        self.setText(f"{display_name}\n{status}")
        self.setIcon(icon)
        self.setAccessibleName(f"{display_name}, {status}")


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
        self.account_buttons: dict[str, AccountRailButton] = {}
        self.account_statuses: dict[str, str] = {}
        self.session_error: str | None = None
        self._starting_all = False

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)
        header = QHBoxLayout()
        heading = QVBoxLayout()
        heading.setSpacing(3)
        title = QLabel("Đăng bài")
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            "Chọn tài khoản, thiết lập kế hoạch và theo dõi từng lượt đăng."
        )
        subtitle.setProperty("muted", True)
        subtitle.setWordWrap(True)
        heading.addWidget(title)
        heading.addWidget(subtitle)
        manage_button = QPushButton("Quản lý tài khoản")
        manage_button.setProperty("density", "compact")
        manage_button.clicked.connect(self._manage_accounts)
        self.configure_all_button = QPushButton("Cấu hình tất cả")
        self.configure_all_button.setProperty("density", "compact")
        self.configure_all_button.clicked.connect(self._configure_all_plans)
        refresh_button = QPushButton("Làm mới")
        refresh_button.setProperty("density", "compact")
        refresh_button.clicked.connect(self.refresh_data)
        self.start_all_button = QPushButton("Bắt đầu tất cả")
        self.start_all_button.setProperty("role", "primary")
        self.start_all_button.setProperty("density", "compact")
        self.start_all_button.clicked.connect(self.start_all)
        header.addLayout(heading, 1)
        header.addWidget(manage_button, 0, Qt.AlignmentFlag.AlignTop)
        header.addWidget(
            self.configure_all_button,
            0,
            Qt.AlignmentFlag.AlignTop,
        )
        header.addWidget(refresh_button, 0, Qt.AlignmentFlag.AlignTop)
        header.addWidget(self.start_all_button, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(header)

        self.overview = QWidget()
        self.overview.setProperty("overview", True)
        overview_layout = QHBoxLayout(self.overview)
        overview_layout.setContentsMargins(14, 9, 14, 9)
        overview_layout.setSpacing(12)
        self.accounts_summary = QLabel()
        self.queue_summary = QLabel()
        self.run_summary = StatusBadge("", "idle")
        self.accounts_summary.setProperty("overviewStrong", True)
        self.queue_summary.setProperty("muted", True)
        overview_layout.addWidget(self.accounts_summary)
        overview_layout.addWidget(self.queue_summary)
        overview_layout.addStretch()
        overview_layout.addWidget(self.run_summary)
        root.addWidget(self.overview)

        self.workspace = QWidget()
        workspace_layout = QHBoxLayout(self.workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(12)
        workspace_layout.addWidget(self._create_account_rail())
        self.workspace_stack = QStackedWidget()
        self.workspace_stack.setObjectName("AccountWorkspace")
        workspace_layout.addWidget(self.workspace_stack, 1)

        self.empty_panel = EmptyState(
            "Chưa có tài khoản Facebook",
            "Thêm tài khoản và đăng nhập ngay trong ứng dụng để bắt đầu.",
            "Thêm tài khoản",
        )
        self.empty_panel.action_requested.connect(self._manage_accounts)
        root.addWidget(self.empty_panel, 1)
        root.addWidget(self.workspace, 1)
        self.refresh_data()

    def _create_account_rail(self) -> QFrame:
        rail = QFrame()
        rail.setObjectName("AccountRail")
        rail.setFixedWidth(214)
        layout = QVBoxLayout(rail)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setSpacing(8)
        heading = QHBoxLayout()
        title = QLabel("Tài khoản")
        title.setObjectName("SectionTitle")
        self.rail_count = QLabel()
        self.rail_count.setProperty("meta", True)
        heading.addWidget(title)
        heading.addStretch()
        heading.addWidget(self.rail_count)
        layout.addLayout(heading)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.rail_container = QWidget()
        self.rail_layout = QVBoxLayout(self.rail_container)
        self.rail_layout.setContentsMargins(0, 0, 4, 0)
        self.rail_layout.setSpacing(7)
        self.rail_layout.addStretch()
        scroll.setWidget(self.rail_container)
        layout.addWidget(scroll, 1)
        self.account_button_group = QButtonGroup(self)
        self.account_button_group.setExclusive(True)
        return rail

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
        for account_id in list(self.account_tabs):
            tab = self.account_tabs[account_id]
            if account_id in account_ids or tab.is_running:
                continue
            self.workspace_stack.removeWidget(tab)
            tab.deleteLater()
            del self.account_tabs[account_id]
            button = self.account_buttons.pop(account_id, None)
            if button is not None:
                self.account_button_group.removeButton(button)
                button.setParent(None)
                button.deleteLater()
            self.account_statuses.pop(account_id, None)

        for account in accounts:
            avatar_path = self.account_service.get_avatar_path(account)
            session_available = self.account_service.has_session(account.id)
            initial_status = (
                "Sẵn sàng" if session_available else "Chưa đăng nhập"
            )
            if account.id in self.account_tabs:
                tab = self.account_tabs[account.id]
                previous_status = self.account_statuses.get(account.id)
                tab.update_account(account, avatar_path, session_available)
                if previous_status in {"Sẵn sàng", "Chưa đăng nhập", None}:
                    self.account_statuses[account.id] = initial_status
                tab.refresh_available_data()
                self._update_account_identity(account.id)
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
            tab.plan_requested.connect(self._configure_account_plan)
            self.account_tabs[account.id] = tab
            self.account_statuses[account.id] = initial_status
            self.workspace_stack.addWidget(tab)

            button = AccountRailButton(account.id)
            button.clicked.connect(
                lambda _checked=False, account_id=account.id: self._select_account(
                    account_id
                )
            )
            self.account_buttons[account.id] = button
            self.account_button_group.addButton(button)
            self.rail_layout.insertWidget(self.rail_layout.count() - 1, button)
            self._update_account_identity(account.id)

        has_accounts = bool(self.account_tabs)
        self.workspace.setVisible(has_accounts)
        self.empty_panel.setVisible(not has_accounts)
        if has_accounts and not any(
            button.isChecked() for button in self.account_buttons.values()
        ):
            self._select_account(next(iter(self.account_tabs)))
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

    def start_all(self, _checked: bool = False) -> int:
        candidates = [
            tab
            for tab in self.account_tabs.values()
            if tab.tasks and tab.session_available and not tab.is_running
        ]
        if not candidates:
            QMessageBox.information(
                self,
                "Không có tài khoản để bắt đầu",
                "Hãy kiểm tra tài khoản đã đăng nhập và đã có kế hoạch đăng.",
            )
            self._update_overview()
            return 0

        self._starting_all = True
        self.start_all_button.setText("Đang khởi động…")
        self.start_all_button.setEnabled(False)
        started = 0
        try:
            for tab in candidates:
                if tab.start():
                    started += 1
        finally:
            self._starting_all = False
            self.start_all_button.setText("Bắt đầu tất cả")
            self._update_overview()
        return started

    def _configure_account_plan(self, account_id: str) -> None:
        tab = self.account_tabs.get(account_id)
        if tab is None or tab.is_running:
            return
        dialog = PostingPlanDialog(
            self.listing_service,
            self.group_service,
            tasks=tab.tasks,
            scope_title=f"Cấu hình riêng · {tab.account.display_name}",
            scope_description=(
                "Kế hoạch này chỉ áp dụng cho tài khoản đang mở; các tài "
                "khoản khác giữ nguyên."
            ),
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        tab.apply_plan(dialog.selected_tasks())
        self._update_overview()

    def _configure_all_plans(self, _checked: bool = False) -> None:
        tabs = list(self.account_tabs.values())
        if not tabs:
            QMessageBox.information(
                self,
                "Chưa có tài khoản",
                "Hãy thêm ít nhất một tài khoản trước khi cấu hình chung.",
            )
            return
        if any(tab.is_running for tab in tabs):
            QMessageBox.information(
                self,
                "Tài khoản đang chạy",
                "Hãy chờ hoặc dừng an toàn toàn bộ tài khoản trước khi cấu "
                "hình một kế hoạch chung.",
            )
            return
        current = self.workspace_stack.currentWidget()
        template_tab = (
            current if isinstance(current, AccountPostingTab) else tabs[0]
        )
        dialog = PostingPlanDialog(
            self.listing_service,
            self.group_service,
            tasks=template_tab.tasks,
            scope_title="Cấu hình tất cả tài khoản",
            scope_description=(
                f"Dùng kế hoạch của {template_tab.account.display_name} làm "
                f"mẫu và thay thế kế hoạch hiện tại của {len(tabs)} tài khoản."
            ),
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        tasks = dialog.selected_tasks()
        for tab in tabs:
            tab.apply_plan(tasks)
        self._update_overview()

    def _select_account(self, account_id: str) -> None:
        tab = self.account_tabs.get(account_id)
        button = self.account_buttons.get(account_id)
        if tab is None or button is None:
            return
        self.workspace_stack.setCurrentWidget(tab)
        button.setChecked(True)

    def _on_running_changed(self, account: str, _running: bool) -> None:
        self.posting_state_changed.emit(self.is_running)
        self._update_account_identity(account)
        self._update_overview()

    def _on_status_changed(self, account: str, status: str) -> None:
        self.account_statuses[account] = status
        self._update_account_identity(account)
        self._update_overview()

    def _update_overview(self) -> None:
        account_count = len(self.account_tabs)
        task_count = sum(len(tab.tasks) for tab in self.account_tabs.values())
        attempt_count = sum(
            tab.total_attempts for tab in self.account_tabs.values()
        )
        running_count = sum(
            1 for tab in self.account_tabs.values() if tab.is_running
        )
        pending_count = sum(
            1 for tab in self.account_tabs.values() if not tab.session_available
        )
        ready_count = account_count - running_count - pending_count
        self.accounts_summary.setText(f"{account_count} tài khoản")
        self.rail_count.setText(str(account_count))
        self.queue_summary.setText(
            f"{task_count} phòng · {attempt_count} lượt dự kiến"
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
        can_start_any = any(
            tab.tasks and not tab.is_running and tab.session_available
            for tab in self.account_tabs.values()
        )
        self.start_all_button.setEnabled(
            can_start_any and not self._starting_all
        )
        self.start_all_button.setToolTip(
            "Bắt đầu các tài khoản đã có kế hoạch và chưa chạy."
            if can_start_any
            else "Không còn tài khoản đủ điều kiện để bắt đầu."
        )
        has_listings = any(
            tab.has_available_listings
            for tab in self.account_tabs.values()
        )
        can_configure_all = (
            account_count > 0
            and not self.is_running
            and has_listings
        )
        self.configure_all_button.setEnabled(can_configure_all)
        self.configure_all_button.setToolTip(
            "Dùng kế hoạch của tab đang mở cho toàn bộ tài khoản."
            if can_configure_all
            else (
                "Hãy chờ tất cả tài khoản dừng trước khi cấu hình chung."
                if self.is_running
                else "Hãy thêm tài khoản và ít nhất một phòng đang dùng."
            )
        )

    def _manage_accounts(self) -> None:
        dialog = AccountManagerDialog(self.account_service, parent=self)
        dialog.accounts_changed.connect(self.refresh_data)
        dialog.exec()
        self.refresh_data()

    def _update_account_identity(self, account_id: str) -> None:
        account = self.account_service.get_by_id(account_id)
        button = self.account_buttons.get(account_id)
        if account is None or button is None:
            return
        status = self.account_statuses.get(account_id, "Sẵn sàng")
        button.update_identity(
            account.display_name,
            status,
            self._account_icon(account),
        )
        button.setToolTip(self._account_tooltip(account, status))

    def _account_icon(self, account):
        avatar_path = self.account_service.get_avatar_path(account)
        return circular_avatar_icon(avatar_path, QSize(38, 38))

    @staticmethod
    def _account_tooltip(account, status: str) -> str:
        identity = account.facebook_name.strip() or "Chưa đồng bộ tên Facebook"
        return f"{identity}\n{status}\nPhiên cục bộ: {account.id}"
