from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from gui.dialogs.group_dialog import GroupDialog
from gui.widgets.design_components import EmptyState
from models.group_target import GroupTarget
from services.group_service import GroupService
from services.facebook_account_service import FacebookAccountService


class GroupSelectionRow(QFrame):
    def __init__(
        self,
        group,
        selected_count: int = 0,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.group = group
        self.setProperty("groupRow", True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 11, 14, 11)
        layout.setSpacing(12)
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(selected_count > 0)
        self.checkbox.setToolTip(f"Chọn {group.name}")
        group_info = QVBoxLayout()
        group_info.setSpacing(3)
        name = QLabel(group.name)
        name.setWordWrap(True)
        url = QLabel(group.url)
        url.setProperty("muted", True)
        url.setWordWrap(True)
        url.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        group_info.addWidget(name)
        group_info.addWidget(url)
        self.count_input = QSpinBox()
        self.count_input.setRange(1, 999)
        self.count_input.setValue(selected_count or 1)
        self.count_input.setPrefix("Số lượt: ")
        self.count_input.setFixedWidth(145)
        self.count_input.setEnabled(self.checkbox.isChecked())
        self.checkbox.toggled.connect(self.count_input.setEnabled)
        layout.addWidget(self.checkbox)
        layout.addLayout(group_info, 1)
        layout.addWidget(self.count_input)


class GroupSelectorDialog(QDialog):
    def __init__(
        self,
        group_service: GroupService,
        selected_counts: dict[str, int] | None = None,
        preferred_account: str | None = None,
        account_service: FacebookAccountService | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.group_service = group_service
        self.selected_counts = selected_counts or {}
        self.preferred_account = preferred_account
        self.account_service = account_service
        self.rows: list[GroupSelectionRow] = []
        self.setWindowTitle("Chọn nhóm đăng bài")
        self.setMinimumSize(760, 580)
        self.resize(880, 680)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(14)
        title = QLabel("Chọn nhóm và số lượt đăng")
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            "Mỗi phòng có bộ nhóm và số lượt riêng. "
            "Chỉ các nhóm đang dùng mới xuất hiện ở đây."
        )
        subtitle.setProperty("muted", True)
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        tools = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setProperty("search", True)
        self.search_input.setPlaceholderText("Tìm theo tên hoặc URL nhóm...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._filter_rows)
        add_button = QPushButton("Thêm nhóm mới")
        add_button.clicked.connect(self._add_group)
        tools.addWidget(self.search_input, 1)
        tools.addWidget(add_button)
        root.addLayout(tools)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.container = QWidget()
        self.rows_layout = QVBoxLayout(self.container)
        self.rows_layout.setContentsMargins(0, 0, 10, 0)
        self.rows_layout.setSpacing(9)
        scroll.setWidget(self.container)
        root.addWidget(scroll, 1)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        save = self.buttons.button(QDialogButtonBox.StandardButton.Save)
        cancel = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        save.setText("Xác nhận nhóm")
        save.setIcon(QIcon())
        save.setProperty("role", "primary")
        cancel.setText("Hủy")
        cancel.setIcon(QIcon())
        self.buttons.accepted.connect(self._accept_selection)
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)
        self._render_rows()

    def _render_rows(self) -> None:
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self.rows.clear()
        groups = [
            group for group in self.group_service.get_all() if group.enabled
        ]
        if not groups:
            empty = EmptyState(
                "Chưa có nhóm đang dùng",
                "Thêm hoặc bật một nhóm trước khi tạo hàng chờ đăng.",
                "Thêm nhóm mới",
            )
            empty.action_requested.connect(self._add_group)
            self.rows_layout.addWidget(empty)
            self.rows_layout.addStretch()
            return
        for group in groups:
            row = GroupSelectionRow(
                group,
                self.selected_counts.get(group.url, 0),
            )
            self.rows.append(row)
            self.rows_layout.addWidget(row)
        self.rows_layout.addStretch()
        self._filter_rows()

    def _filter_rows(self) -> None:
        query = self.search_input.text().strip().lower()
        for row in self.rows:
            row.setVisible(
                not query
                or query in row.group.name.lower()
                or query in row.group.url.lower()
            )

    def _add_group(self) -> None:
        dialog = GroupDialog(
            self.group_service,
            preferred_account=self.preferred_account,
            account_service=self.account_service,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.saved_group is not None:
                self.selected_counts[dialog.saved_group.url] = 1
            self._render_rows()

    def _accept_selection(self) -> None:
        if not any(row.checkbox.isChecked() for row in self.rows):
            QMessageBox.warning(
                self,
                "Chưa chọn nhóm",
                "Hãy chọn ít nhất một nhóm cho phòng này.",
            )
            return
        self.accept()

    def selected_targets(
        self,
    ) -> tuple[list[GroupTarget], dict[str, str]]:
        selected = [row for row in self.rows if row.checkbox.isChecked()]
        targets = [
            GroupTarget(
                url=row.group.url,
                target_count=row.count_input.value(),
            )
            for row in selected
        ]
        names = {row.group.url: row.group.name for row in selected}
        return targets, names
