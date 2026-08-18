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

from gui.dialogs.group_dialog import GroupDialog
from gui.widgets.design_components import EmptyState
from gui.widgets.group_card import GroupCard
from models.saved_group import SavedGroup
from services.group_service import GroupService


class GroupsPage(QWidget):
    groups_changed = Signal()

    def __init__(
        self,
        group_service: GroupService,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.group_service = group_service
        self.groups: list[SavedGroup] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)
        header = QHBoxLayout()
        heading = QVBoxLayout()
        title = QLabel("Nhóm")
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            "Lưu nhóm Facebook một lần để tái sử dụng cho mọi phòng."
        )
        subtitle.setProperty("muted", True)
        heading.addWidget(title)
        heading.addWidget(subtitle)
        add_button = QPushButton("Thêm nhóm")
        add_button.setProperty("role", "primary")
        add_button.setMinimumHeight(42)
        add_button.clicked.connect(self._add_group)
        header.addLayout(heading)
        header.addStretch()
        header.addWidget(add_button)
        root.addLayout(header)

        self.search_input = QLineEdit()
        self.search_input.setProperty("search", True)
        self.search_input.setPlaceholderText(
            "Tìm theo tên, mã hoặc URL nhóm..."
        )
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._render_groups)
        self.search_input.setMaximumWidth(760)
        self.count_label = QLabel()
        self.count_label.setProperty("meta", True)
        search_row = QHBoxLayout()
        search_row.addWidget(self.search_input, 1)
        search_row.addStretch()
        search_row.addWidget(self.count_label)
        root.addLayout(search_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.container = QWidget()
        self.groups_layout = QVBoxLayout(self.container)
        self.groups_layout.setContentsMargins(0, 0, 10, 0)
        self.groups_layout.setSpacing(12)
        scroll.setWidget(self.container)
        root.addWidget(scroll, 1)
        self.refresh_groups()

    def refresh_groups(self) -> None:
        try:
            self.groups = self.group_service.get_all()
        except Exception as error:
            self.groups = []
            self._render_message(
                "Không thể tải thư viện nhóm",
                f"{error}\nKiểm tra tệp dữ liệu rồi thử lại.",
                "Thử lại",
                self.refresh_groups,
            )
            return
        self._render_groups()

    def _render_groups(self) -> None:
        self._clear()
        query = self.search_input.text().strip().lower()
        visible = [
            group
            for group in self.groups
            if not query
            or query in group.id.lower()
            or query in group.name.lower()
            or query in group.url.lower()
        ]
        self.count_label.setText(f"{len(visible)} nhóm")
        if not visible:
            if query:
                self._render_message(
                    "Không tìm thấy nhóm",
                    "Thử một tên, mã hoặc URL nhóm khác.",
                )
            else:
                self._render_message(
                    "Chưa có nhóm đã lưu",
                    "Lưu nhóm Facebook để chọn nhanh khi tạo hàng chờ đăng.",
                    "Thêm nhóm",
                    self._add_group,
                )
            return
        for group in visible:
            card = GroupCard(group)
            card.edit_requested.connect(self._edit_group)
            card.refresh_requested.connect(self._refresh_group)
            card.delete_requested.connect(self._delete_group)
            self.groups_layout.addWidget(card)
        self.groups_layout.addStretch()

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
        self.groups_layout.addWidget(panel)
        self.groups_layout.addStretch()

    def _clear(self) -> None:
        while self.groups_layout.count():
            item = self.groups_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _add_group(self) -> None:
        dialog = GroupDialog(self.group_service, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_groups()
            self.groups_changed.emit()

    def _edit_group(self, group_id: str) -> None:
        group = self.group_service.get_by_id(group_id)
        if group is None:
            QMessageBox.warning(
                self, "Không tìm thấy nhóm", f"Nhóm {group_id} không còn tồn tại."
            )
            self.refresh_groups()
            return
        dialog = GroupDialog(self.group_service, group=group, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_groups()
            self.groups_changed.emit()

    def _refresh_group(self, group_id: str) -> None:
        group = self.group_service.get_by_id(group_id)
        if group is None:
            self.refresh_groups()
            return
        dialog = GroupDialog(
            self.group_service,
            group=group,
            auto_refresh=True,
            auto_save_after_refresh=True,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_groups()
            self.groups_changed.emit()

    def _delete_group(self, group_id: str) -> None:
        answer = QMessageBox.question(
            self,
            "Xóa nhóm",
            f"Xóa nhóm {group_id} khỏi thư viện?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.group_service.delete_group(group_id)
        except Exception as error:
            QMessageBox.critical(self, "Không thể xóa nhóm", str(error))
            return
        self.refresh_groups()
        self.groups_changed.emit()
