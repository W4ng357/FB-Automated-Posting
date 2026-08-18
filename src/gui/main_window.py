from PySide6.QtCore import QEvent, QEasingCurve, QPropertyAnimation, QTimer, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from gui.pages.groups_page import GroupsPage
from gui.pages.listings_page import ListingsPage
from gui.pages.posting_page import PostingPage
from services.group_service import GroupService
from services.facebook_account_service import FacebookAccountService
from services.listing_service import ListingService


class MainWindow(QMainWindow):
    minimized_to_tray = Signal()

    def __init__(
        self,
        listing_service: ListingService | None = None,
        group_service: GroupService | None = None,
        account_service: FacebookAccountService | None = None,
    ) -> None:
        super().__init__()
        self.listing_service = listing_service or ListingService()
        self.group_service = group_service or GroupService()
        self.account_service = account_service
        self._page_animation: QPropertyAnimation | None = None
        self._system_tray_enabled = False
        self._application_exit_requested = False
        self.setWindowTitle("W4nwy Automation · Quản lý đăng bài")
        self.setMinimumSize(1120, 720)
        self.resize(1480, 920)

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._create_sidebar())

        self.page_stack = QStackedWidget()
        self.page_stack.setObjectName("PageStack")
        self.listings_page = ListingsPage(self.listing_service)
        self.groups_page = GroupsPage(self.group_service)
        self.posting_page = PostingPage(
            self.listing_service,
            self.group_service,
            self.account_service,
        )
        self.account_service = self.posting_page.account_service
        self.page_stack.addWidget(self.listings_page)
        self.page_stack.addWidget(self.groups_page)
        self.page_stack.addWidget(self.posting_page)
        root.addWidget(self.page_stack, 1)

        self.listings_page.listings_changed.connect(
            self.posting_page.refresh_listings
        )
        self.groups_page.groups_changed.connect(
            self.posting_page.refresh_groups
        )
        self.posting_page.accounts_changed.connect(
            self._update_sidebar_footer
        )
        self._update_sidebar_footer(len(self.posting_page.account_tabs))
        self.setCentralWidget(central)
        self.page_stack.setCurrentIndex(0)
        self.listings_button.setChecked(True)

    def _create_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(228)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(20, 28, 20, 24)
        layout.setSpacing(10)
        brand = QLabel("W4nwy Automation")
        brand.setObjectName("BrandLabel")
        layout.addWidget(brand)
        layout.addSpacing(26)

        self.navigation_group = QButtonGroup(self)
        self.navigation_group.setExclusive(True)
        self.listings_button = self._create_nav_button("Phòng")
        self.groups_button = self._create_nav_button("Nhóm")
        self.posting_button = self._create_nav_button("Đăng bài")
        self.navigation_group.addButton(self.listings_button, 0)
        self.navigation_group.addButton(self.groups_button, 1)
        self.navigation_group.addButton(self.posting_button, 2)
        self.navigation_group.idClicked.connect(self._show_page)
        layout.addWidget(self.listings_button)
        layout.addWidget(self.groups_button)
        layout.addWidget(self.posting_button)
        separator = QFrame()
        separator.setObjectName("SidebarSeparator")
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFixedHeight(1)
        layout.addSpacing(14)
        layout.addWidget(separator)
        layout.addStretch()
        self.sidebar_footer = QLabel()
        self.sidebar_footer.setObjectName("SidebarFooter")
        self.sidebar_footer.setWordWrap(True)
        layout.addWidget(self.sidebar_footer)
        return sidebar

    @staticmethod
    def _create_nav_button(text: str) -> QPushButton:
        button = QPushButton(text)
        button.setCheckable(True)
        button.setProperty("nav", True)
        button.setMinimumHeight(44)
        button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        return button

    def _show_page(self, index: int) -> None:
        previous_index = self.page_stack.currentIndex()
        self.page_stack.setCurrentIndex(index)
        button = self.navigation_group.button(index)
        if button is not None:
            button.setChecked(True)
        if index == 0:
            self.listings_page.refresh_listings()
        elif index == 1:
            self.groups_page.refresh_groups()
        elif index == 2:
            self.posting_page.refresh_data()
        if previous_index != index and self.isVisible():
            self._animate_page_in(self.page_stack.currentWidget())

    def _animate_page_in(self, page: QWidget) -> None:
        if self._page_animation is not None:
            self._page_animation.stop()
            self._page_animation = None

        effect = QGraphicsOpacityEffect(page)
        effect.setOpacity(0.84)
        page.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(180)
        animation.setStartValue(0.84)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        def finish() -> None:
            if page.graphicsEffect() is effect:
                page.setGraphicsEffect(None)
            if self._page_animation is animation:
                self._page_animation = None

        animation.finished.connect(finish)
        self._page_animation = animation
        animation.start()

    def _update_sidebar_footer(self, account_count: int) -> None:
        account_text = (
            "Chưa có tài khoản"
            if account_count == 0
            else f"{account_count} tài khoản đã lưu"
        )
        self.sidebar_footer.setText(
            f"Dữ liệu lưu trên máy\n{account_text}"
        )

    def enable_system_tray(self, enabled: bool) -> None:
        self._system_tray_enabled = enabled

    def request_application_exit(self) -> bool:
        if self.posting_page.is_running:
            QMessageBox.warning(
                self,
                "Đang đăng bài",
                "Hãy dừng tất cả tài khoản và chờ bài hiện tại đăng xong "
                "trước khi thoát ứng dụng.",
            )
            return False
        self._application_exit_requested = True
        if self.close():
            return True
        self._application_exit_requested = False
        return False

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if (
            self._system_tray_enabled
            and event.type() == QEvent.Type.WindowStateChange
            and self.isMinimized()
        ):
            QTimer.singleShot(0, self._hide_in_system_tray)

    def _hide_in_system_tray(self) -> None:
        if not self._system_tray_enabled:
            return
        self.hide()
        self.minimized_to_tray.emit()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._application_exit_requested:
            event.accept()
            return
        if self._system_tray_enabled:
            event.ignore()
            self._hide_in_system_tray()
            return
        if not self.posting_page.is_running:
            event.accept()
            return
        QMessageBox.warning(
            self,
            "Đang đăng bài",
            "Hãy chờ các tài khoản đăng xong trước khi đóng ứng dụng.",
        )
        event.ignore()
