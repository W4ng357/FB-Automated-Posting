from PySide6.QtCore import QSize, Qt, Signal
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
from models.saved_group import SavedGroup


class GroupCard(QFrame):
    edit_requested = Signal(str)
    refresh_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, group: SavedGroup, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("card", True)

        root = QHBoxLayout(self)
        root.setContentsMargins(14, 14, 16, 14)
        root.setSpacing(16)
        avatar = RoundedThumbnail(
            fallback_text=group.name,
            size=QSize(64, 64),
        )
        avatar.setToolTip("Nhóm Facebook đã lưu")
        root.addWidget(avatar)

        content = QVBoxLayout()
        content.setSpacing(5)
        heading = QHBoxLayout()
        name = QLabel(group.name)
        name.setObjectName("CardTitle")
        name.setWordWrap(True)
        heading.addWidget(name)
        heading.addStretch()
        url = QLabel(group.url)
        url.setProperty("muted", True)
        url.setWordWrap(True)
        url.setToolTip(group.url)
        url.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        identifier = QLabel(f"Mã nhóm {group.id}")
        identifier.setProperty("meta", True)
        content.addLayout(heading)
        content.addWidget(url)
        content.addWidget(identifier)
        root.addLayout(content, 1)

        side = QVBoxLayout()
        side.setSpacing(10)
        status = StatusBadge(
            "Đang bật" if group.enabled else "Đã ẩn",
            "enabled" if group.enabled else "disabled",
        )
        side.addWidget(status, 0, Qt.AlignmentFlag.AlignRight)
        side.addStretch()

        actions = QHBoxLayout()
        actions.setSpacing(8)
        edit_button = QPushButton("Chỉnh sửa")
        edit_button.setProperty("density", "compact")
        edit_button.clicked.connect(
            lambda: self.edit_requested.emit(group.id)
        )

        menu = QMenu(self)
        refresh_action = menu.addAction("Cập nhật tên nhóm")
        refresh_action.triggered.connect(
            lambda _checked=False: self.refresh_requested.emit(group.id)
        )
        menu.addSeparator()
        delete_action = menu.addAction("Xóa nhóm")
        delete_action.triggered.connect(
            lambda _checked=False: self.delete_requested.emit(group.id)
        )
        more_button = QPushButton("Tùy chọn")
        more_button.setProperty("role", "ghost")
        more_button.setProperty("density", "compact")
        more_button.setMenu(menu)

        actions.addWidget(edit_button)
        actions.addWidget(more_button)
        side.addLayout(actions)
        root.addLayout(side)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
