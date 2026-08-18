from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from gui.widgets.design_components import RoundedThumbnail, StatusBadge
from models.listing import Listing
from services.caption_generator import (
    format_area,
    format_price,
)


class ListingCard(QFrame):
    edit_requested = Signal(str)
    delete_requested = Signal(str)
    toggle_requested = Signal(str, bool)

    def __init__(
        self,
        listing: Listing,
        images: list[Path] | int | None,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.listing = listing
        self.setProperty("card", True)

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(14, 14, 16, 14)
        root_layout.setSpacing(16)

        image_paths = images if isinstance(images, list) else []
        image_count = len(image_paths) if isinstance(images, list) else images
        thumbnail = RoundedThumbnail(
            image_paths[0] if image_paths else None,
            fallback_text=listing.title,
        )
        thumbnail.setToolTip(
            str(image_paths[0])
            if image_paths
            else "Phòng chưa có ảnh đại diện"
        )
        root_layout.addWidget(thumbnail)

        content_layout = QVBoxLayout()
        content_layout.setSpacing(5)

        title_row = QHBoxLayout()
        title = QLabel(listing.title)
        title.setObjectName("CardTitle")
        title.setWordWrap(True)

        title_row.addWidget(title)
        title_row.addStretch()

        area_text = (
            f" · {format_area(listing.area)}m²"
            if listing.area is not None
            else ""
        )
        summary = QLabel(
            f"{listing.id}  ·  {format_price(listing.price)}/tháng"
            f"{area_text}"
        )
        summary.setProperty("muted", True)
        address_text = listing.address.strip() or listing.location.strip()
        address = QLabel(address_text)
        address.setProperty("muted", True)
        address.setWordWrap(True)
        address.setToolTip(address_text)

        image_text = (
            "Không đọc được số ảnh"
            if image_count is None
            else (
                f"{image_count} ảnh đã lưu"
            )
        )
        images_label = QLabel(image_text)
        images_label.setProperty("meta", True)

        content_layout.addLayout(title_row)
        content_layout.addWidget(summary)
        content_layout.addWidget(address)
        content_layout.addWidget(images_label)

        side = QVBoxLayout()
        side.setSpacing(10)
        status = StatusBadge(
            "Đang dùng" if listing.enabled else "Đã ẩn",
            "enabled" if listing.enabled else "disabled",
        )
        side.addWidget(status, 0, Qt.AlignmentFlag.AlignRight)
        side.addStretch()

        actions = QHBoxLayout()
        actions.setSpacing(8)

        menu = QMenu(self)
        toggle_action = menu.addAction(
            "Ẩn phòng" if listing.enabled else "Bật phòng"
        )
        toggle_action.triggered.connect(
            lambda _checked=False: self.toggle_requested.emit(
                listing.id,
                not listing.enabled,
            )
        )

        edit_button = QPushButton("Chỉnh sửa")
        edit_button.setProperty("density", "compact")
        edit_button.clicked.connect(
            lambda: self.edit_requested.emit(listing.id)
        )

        menu.addSeparator()
        delete_action = menu.addAction("Xóa phòng")
        delete_action.triggered.connect(
            lambda _checked=False: self.delete_requested.emit(
                listing.id
            )
        )

        more_button = QPushButton("Tùy chọn")
        more_button.setProperty("role", "ghost")
        more_button.setProperty("density", "compact")
        more_button.setMenu(menu)

        actions.addWidget(edit_button)
        actions.addWidget(more_button)
        side.addLayout(actions)

        root_layout.addLayout(content_layout, 1)
        root_layout.addLayout(side)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
