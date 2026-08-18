from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from gui.widgets.design_components import StatusBadge
from models.posting_result_entry import PostingResultEntry


class ResultCard(QFrame):
    def __init__(
        self,
        entry: PostingResultEntry,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("resultCard", True)
        result = entry.result
        root = QHBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(14)
        state = StatusBadge(
            "Thành công" if result.success else "Thất bại",
            "success" if result.success else "error",
        )
        root.addWidget(state)
        content = QVBoxLayout()
        content.setSpacing(4)
        group_name = QLabel(result.group_name or result.group_url)
        group_name.setObjectName("CardTitle")
        listing = QLabel(entry.listing_title)
        listing.setProperty("muted", True)
        if result.success and result.post_url:
            detail_text = "Đăng thành công · Đã lấy được liên kết bài viết"
        elif result.success:
            detail_text = "Đăng thành công · Chưa lấy được liên kết bài viết"
        else:
            detail_text = f"Đăng thất bại · {result.error or 'Không rõ lỗi'}"
        detail = QLabel(detail_text)
        detail.setWordWrap(True)
        detail.setProperty("muted", True)
        destination_url = result.post_url or result.group_url
        url = QLabel(destination_url)
        url.setProperty("meta", True)
        url.setWordWrap(True)
        url.setToolTip(destination_url)
        url.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        content.addWidget(group_name)
        content.addWidget(listing)
        content.addWidget(detail)
        content.addWidget(url)
        root.addLayout(content, 1)
        open_button = QPushButton(
            "Mở bài viết" if result.post_url else "Mở nhóm"
        )
        open_button.setProperty("role", "link")
        open_button.setProperty("density", "compact")
        open_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(destination_url))
        )
        root.addWidget(open_button)
