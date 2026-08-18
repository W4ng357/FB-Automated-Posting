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
        root.setContentsMargins(14, 13, 14, 13)
        root.setSpacing(14)
        thumbnail = RoundedThumbnail(
            image_path,
            entry.listing_title,
            QSize(92, 78),
        )
        root.addWidget(thumbnail, 0, Qt.AlignmentFlag.AlignTop)

        room_info = QVBoxLayout()
        room_info.setSpacing(4)
        title = QLabel(entry.listing_title)
        title.setObjectName("CardTitle")
        title.setWordWrap(True)
        if listing is None:
            metadata_text = entry.listing_id
            address_text = "Thông tin phòng không còn trong dữ liệu cục bộ"
        else:
            metadata = [listing.id, format_price(listing.price)]
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
        room_info.addWidget(title)
        room_info.addWidget(metadata)
        room_info.addWidget(address)
        room_info.addWidget(detail)
        root.addLayout(room_info, 1)

        event_info = QVBoxLayout()
        event_info.setSpacing(5)
        event_info.setContentsMargins(6, 0, 0, 0)
        time_label = QLabel(
            entry.posted_at.astimezone().strftime("%d/%m/%Y · %H:%M:%S")
        )
        time_label.setProperty("meta", True)
        time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        group = QLabel(result.group_name or result.group_url)
        group.setProperty("resultGroup", True)
        group.setWordWrap(True)
        group.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop
        )
        status_text, status_state = self.status_for(entry)
        badge = StatusBadge(status_text, status_state)
        destination_url = result.post_url or result.group_url
        open_button = QPushButton(
            "Mở bài viết" if result.post_url else "Mở nhóm"
        )
        open_button.setProperty("role", "link")
        open_button.setProperty("density", "compact")
        open_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(destination_url))
        )
        event_info.addWidget(time_label)
        event_info.addWidget(group)
        event_info.addStretch()
        event_info.addWidget(badge, 0, Qt.AlignmentFlag.AlignRight)
        event_info.addWidget(open_button, 0, Qt.AlignmentFlag.AlignRight)
        root.addLayout(event_info, 0)

    @staticmethod
    def status_for(entry: PostingResultEntry) -> tuple[str, str]:
        result = entry.result
        if result.success and result.post_url:
            return "Thành công", "success"
        if result.success:
            return "Bị gián đoạn", "warning"
        return "Thất bại", "error"

    @staticmethod
    def _detail_text(entry: PostingResultEntry) -> str:
        result = entry.result
        if result.success and result.post_url:
            return "Đã đăng bài và lấy được liên kết."
        if result.success:
            return "Đã đăng bài nhưng không lấy được liên kết để kiểm tra."
        return result.error or "Đăng bài thất bại nhưng không có mô tả lỗi."

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
        self.rows_layout.setSpacing(9)
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
            parts.append(f"{interrupted_count} bị gián đoạn")
        if failed_count:
            parts.append(f"{failed_count} thất bại")
        self.summary_label.setText(" · ".join(parts))

        if not self.entries:
            self.rows_layout.addWidget(
                EmptyState(
                    "Chưa có kết quả",
                    "Kết quả mới sẽ xuất hiện ngay khi tài khoản đăng xong từng bài.",
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
