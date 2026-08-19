from pathlib import Path

from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from gui.widgets.design_components import EmptyState, RoundedThumbnail, StatusBadge
from models.posting_result_entry import PostingResultEntry
from services.caption_generator import format_area, format_price
from services.listing_service import ListingService


class PostingResultRow(QFrame):
    GROUP_OPTICAL_OFFSET = 24

    def __init__(
        self,
        entry: PostingResultEntry,
        listing_service: ListingService,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.entry = entry
        self.setProperty("resultCard", True)
        result = entry.result
        listing = listing_service.get_by_id(entry.listing_id)
        image_path = self._first_image(listing_service, entry.listing_id)

        root = QHBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(12)

        room_panel_layout = QHBoxLayout()
        room_panel_layout.setContentsMargins(0, 0, 0, 0)
        room_panel_layout.setSpacing(12)
        self.thumbnail = RoundedThumbnail(
            image_path,
            entry.listing_title,
            QSize(80, 68),
        )
        room_panel_layout.addWidget(
            self.thumbnail,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )

        room_info = QVBoxLayout()
        room_info.setSpacing(2)
        self.room_title = QLabel(entry.listing_title)
        self.room_title.setObjectName("CardTitle")
        self.room_title.setWordWrap(True)
        if listing is None:
            metadata_text = entry.listing_id
            address_text = "Phòng này không còn trong danh sách"
        else:
            unit = getattr(listing, "price_unit", "TR") or "TR"
            metadata = [listing.id, format_price(listing.price, unit)]
            if listing.area is not None:
                metadata.append(f"{format_area(listing.area)}m²")
            metadata_text = " · ".join(metadata)
            address_text = listing.address.strip() or listing.location.strip()
        metadata = QLabel(metadata_text)
        metadata.setProperty("muted", True)
        address = QLabel(address_text)
        address.setProperty("meta", True)
        address.setWordWrap(True)
        detail = QLabel(self._detail_text(entry))
        detail.setProperty("resultDetail", True)
        detail.setWordWrap(True)
        room_info.addWidget(self.room_title)
        room_info.addWidget(metadata)
        room_info.addWidget(address)
        room_info.addWidget(detail)
        room_panel_layout.addLayout(room_info, 1)
        root.addLayout(room_panel_layout, 1)

        fetched_group_name = (result.group_name or "").strip()
        display_group_name = (
            result.group_url
            if fetched_group_name.casefold() in {"", "unknown", "unknown group"}
            else fetched_group_name
        )
        self.group_label = QLabel(display_group_name)
        self.group_label.setProperty("resultGroup", True)
        self.group_label.setWordWrap(True)
        self.group_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.group_label.setAccessibleName(
            f"Nhóm đăng: {self.group_label.text()}"
        )
        group_slot = QHBoxLayout()
        group_slot.setContentsMargins(
            self.GROUP_OPTICAL_OFFSET * 2,
            0,
            0,
            0,
        )
        group_slot.setSpacing(0)
        group_slot.addWidget(
            self.group_label,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )
        root.addLayout(group_slot)

        event_info = QVBoxLayout()
        event_info.setSpacing(3)
        event_info.setContentsMargins(8, 0, 0, 0)
        self.time_label = QLabel(
            entry.posted_at.astimezone().strftime("%d/%m/%Y · %H:%M:%S")
        )
        self.time_label.setProperty("meta", True)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        status_text, status_state = self.status_for(entry)
        self.status_badge = StatusBadge(status_text, status_state)
        destination_url = result.post_url or result.group_url
        self.open_button = QPushButton(
            "Mở bài viết" if result.post_url else "Mở nhóm"
        )
        self.open_button.setProperty("role", "link")
        self.open_button.setProperty("density", "compact")
        self.open_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(destination_url))
        )
        event_info.addWidget(self.time_label)
        event_info.addWidget(
            self.status_badge,
            0,
            Qt.AlignmentFlag.AlignRight,
        )
        event_info.addWidget(
            self.open_button,
            0,
            Qt.AlignmentFlag.AlignRight,
        )
        event_info.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(event_info, 1)
        self._update_group_width(self.width())

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_group_width(event.size().width())

    def _update_group_width(self, row_width: int) -> None:
        available_width = max(0, row_width - 28)
        group_width = max(200, min(440, round(available_width * 0.28)))
        self.group_label.setFixedWidth(group_width)

    @staticmethod
    def status_for(entry: PostingResultEntry) -> tuple[str, str]:
        result = entry.result
        if result.success and result.post_url:
            return "Thành công", "success"
        if result.success:
            return "Thiếu liên kết", "warning"
        return "Thất bại", "error"

    @staticmethod
    def _detail_text(entry: PostingResultEntry) -> str:
        result = entry.result
        if result.success and result.post_url:
            return "Đã đăng và lấy được liên kết bài viết."
        if result.success:
            return "Đã đăng nhưng chưa lấy được liên kết bài viết."
        return result.error or "Đăng không thành công và không có thông tin lỗi."

    @staticmethod
    def _first_image(
        listing_service: ListingService,
        listing_id: str,
    ) -> Path | None:
        try:
            images = listing_service.get_images(listing_id)
        except (KeyError, OSError):
            return None
        return images[0] if images else None


class PostingResultsDialog(QDialog):
    def __init__(
        self,
        account_display_name: str,
        listing_service: ListingService,
        entries: list[PostingResultEntry] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.account_display_name = account_display_name
        self.listing_service = listing_service
        self.entries: list[PostingResultEntry] = []
        self.rows: list[PostingResultRow] = []
        self.setWindowTitle(f"Kết quả đăng · {account_display_name}")
        self.setMinimumSize(860, 520)
        self.resize(1040, 660)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(14)
        heading = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel(f"Kết quả đăng · {account_display_name}")
        title.setObjectName("PageTitle")
        self.summary_label = QLabel()
        self.summary_label.setProperty("muted", True)
        title_box.addWidget(title)
        title_box.addWidget(self.summary_label)
        close_button = QPushButton("Đóng")
        close_button.clicked.connect(self.close)
        heading.addLayout(title_box, 1)
        heading.addWidget(close_button, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(heading)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.container = QWidget()
        self.rows_layout = QVBoxLayout(self.container)
        self.rows_layout.setContentsMargins(0, 0, 7, 0)
        self.rows_layout.setSpacing(8)
        self.scroll.setWidget(self.container)
        root.addWidget(self.scroll, 1)
        self.set_entries(entries or [])

    def set_entries(self, entries: list[PostingResultEntry]) -> None:
        self.entries = list(entries)
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self.rows.clear()
        success_count = sum(
            1
            for entry in self.entries
            if entry.result.success and entry.result.post_url
        )
        interrupted_count = sum(
            1
            for entry in self.entries
            if entry.result.success and not entry.result.post_url
        )
        failed_count = len(self.entries) - success_count - interrupted_count
        parts = [f"{len(self.entries)} kết quả", f"{success_count} thành công"]
        if interrupted_count:
            parts.append(f"{interrupted_count} thiếu liên kết")
        if failed_count:
            parts.append(f"{failed_count} thất bại")
        self.summary_label.setText(" · ".join(parts))

        if not self.entries:
            self.rows_layout.addWidget(
                EmptyState(
                    "Chưa có kết quả",
                    "Mỗi bài đăng xong sẽ xuất hiện tại đây.",
                )
            )
        else:
            for entry in sorted(
                self.entries,
                key=lambda item: item.posted_at,
                reverse=True,
            ):
                row = PostingResultRow(entry, self.listing_service)
                self.rows.append(row)
                self.rows_layout.addWidget(row)
        self.rows_layout.addStretch()
