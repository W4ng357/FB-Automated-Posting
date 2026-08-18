import traceback

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from gui.dialogs.listing_dialog import ListingDialog
from gui.widgets.design_components import EmptyState
from gui.widgets.listing_card import ListingCard
from models.listing import Listing
from services.listing_service import ListingService


class ListingsPage(QWidget):
    listings_changed = Signal()

    def __init__(
        self,
        listing_service: ListingService,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.listing_service = listing_service
        self.listings: list[Listing] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)
        header = QHBoxLayout()
        heading = QVBoxLayout()
        heading.setSpacing(5)
        title = QLabel("Phòng")
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            "Quản lý thông tin, ảnh và trạng thái sẵn sàng đăng của từng phòng."
        )
        subtitle.setProperty("muted", True)
        heading.addWidget(title)
        heading.addWidget(subtitle)
        add_button = QPushButton("Thêm phòng")
        add_button.setProperty("role", "primary")
        add_button.setMinimumHeight(42)
        add_button.clicked.connect(self._add_listing)
        header.addLayout(heading)
        header.addStretch()
        header.addWidget(add_button)
        root.addLayout(header)

        self.search_input = QLineEdit()
        self.search_input.setProperty("search", True)
        self.search_input.setPlaceholderText(
            "Tìm theo mã, tên phòng hoặc địa chỉ..."
        )
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._render_listings)
        self.search_input.setMaximumWidth(760)
        self.count_label = QLabel()
        self.count_label.setProperty("meta", True)
        search_row = QHBoxLayout()
        search_row.addWidget(self.search_input, 1)
        search_row.addStretch()
        search_row.addWidget(self.count_label)
        root.addLayout(search_row)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 10, 0)
        self.list_layout.setSpacing(12)
        self.scroll_area.setWidget(self.list_container)
        root.addWidget(self.scroll_area, 1)
        self.refresh_listings()

    def refresh_listings(self) -> None:
        try:
            self.listings = self.listing_service.get_all()
        except Exception as error:
            self.listings = []
            self._render_message(
                "Không thể tải danh sách phòng",
                f"{error}\nKiểm tra tệp dữ liệu rồi thử lại.",
                "Thử lại",
                self.refresh_listings,
            )
            return
        self._render_listings()

    def _render_listings(self) -> None:
        self._clear()
        query = self.search_input.text().strip().lower()
        visible = [
            listing
            for listing in self.listings
            if not query
            or query in listing.id.lower()
            or query in listing.title.lower()
            or query in listing.address.lower()
            or query in listing.location.lower()
        ]
        self.count_label.setText(f"{len(visible)} phòng")
        if not visible:
            if query:
                self._render_message(
                    "Không tìm thấy phòng",
                    "Thử một tên, mã phòng hoặc địa chỉ khác.",
                )
            else:
                self._render_message(
                    "Chưa có phòng",
                    "Tạo phòng đầu tiên để chuẩn bị nội dung và ảnh đăng.",
                    "Thêm phòng",
                    self._add_listing,
                )
            return

        for listing in visible:
            try:
                images = self.listing_service.get_images(listing.id)
            except Exception:
                traceback.print_exc()
                images = None
            card = ListingCard(listing, images)
            card.edit_requested.connect(self._edit_listing)
            card.delete_requested.connect(self._delete_listing)
            card.toggle_requested.connect(self._toggle_listing)
            self.list_layout.addWidget(card)
        self.list_layout.addStretch()

    def _render_message(
        self,
        title: str,
        description: str,
        action_text: str | None = None,
        action=None,
    ) -> None:
        self._clear()
        panel = EmptyState(title, description, action_text)
        if action is not None:
            panel.action_requested.connect(action)
        self.list_layout.addWidget(panel)
        self.list_layout.addStretch()

    def _clear(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _add_listing(self) -> None:
        dialog = ListingDialog(self.listing_service, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_listings()
            self.listings_changed.emit()

    def _edit_listing(self, listing_id: str) -> None:
        try:
            listing = self.listing_service.get_by_id(listing_id)
            if listing is None:
                raise KeyError(f"Không tìm thấy phòng {listing_id}")
            dialog = ListingDialog(
                self.listing_service,
                listing=listing,
                parent=self,
            )
        except Exception as error:
            self._show_error("Không thể mở thông tin phòng", error)
            return
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_listings()
            self.listings_changed.emit()

    def _toggle_listing(self, listing_id: str, enabled: bool) -> None:
        try:
            self.listing_service.update_listing(
                listing_id,
                enabled=enabled,
            )
        except Exception as error:
            self._show_error("Không thể đổi trạng thái phòng", error)
            return
        self.refresh_listings()
        self.listings_changed.emit()

    def _delete_listing(self, listing_id: str) -> None:
        confirmation = QMessageBox(self)
        confirmation.setIcon(QMessageBox.Icon.Warning)
        confirmation.setWindowTitle("Xóa phòng")
        confirmation.setText(f"Bạn muốn xóa phòng {listing_id}?")
        confirmation.setInformativeText(
            "Có thể chỉ xóa thông tin hoặc xóa cả thư mục ảnh đã lưu."
        )
        metadata_button = confirmation.addButton(
            "Chỉ xóa thông tin",
            QMessageBox.ButtonRole.AcceptRole,
        )
        images_button = confirmation.addButton(
            "Xóa phòng và ảnh",
            QMessageBox.ButtonRole.DestructiveRole,
        )
        confirmation.addButton("Hủy", QMessageBox.ButtonRole.RejectRole)
        confirmation.exec()
        clicked = confirmation.clickedButton()
        if clicked not in {metadata_button, images_button}:
            return
        try:
            self.listing_service.delete_listing(
                listing_id,
                delete_images=(clicked is images_button),
            )
        except Exception as error:
            self._show_error("Không thể xóa phòng", error)
            return
        self.refresh_listings()
        self.listings_changed.emit()

    def _show_error(self, title: str, error: Exception) -> None:
        QMessageBox.critical(self, title, str(error))
