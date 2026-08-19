import unicodedata

from PySide6.QtCore import QSignalBlocker, Qt
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
from gui.widgets.design_components import EmptyState, SearchLineEdit
from models.group_target import GroupTarget
from services.group_service import GroupService
from services.facebook_account_service import FacebookAccountService


def _normalize_search_text(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text.casefold())
    without_marks = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )
    return without_marks.replace("đ", "d")


class SelectAllCheckBox(QCheckBox):
    """A tri-state summary checkbox whose click always toggles all visible items."""

    def nextCheckState(self) -> None:
        next_state = (
            Qt.CheckState.Unchecked
            if self.checkState() == Qt.CheckState.Checked
            else Qt.CheckState.Checked
        )
        self.setCheckState(next_state)


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
        self._updating_selection = False

        self.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled, True)
        self.setWindowTitle("Chọn nhóm đăng bài")
        self.setMinimumSize(780, 600)
        self.resize(900, 700)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(14)
        title = QLabel("Chọn nhóm và số lượt đăng")
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            "Mỗi phòng có danh sách nhóm và số lượt đăng riêng. "
            "Chỉ hiển thị các nhóm đang bật."
        )
        subtitle.setProperty("muted", True)
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        tools = QHBoxLayout()
        self.search_input = SearchLineEdit(
            placeholder="Tìm theo tên hoặc URL nhóm…"
        )
        self.search_input.liveTextChanged.connect(self._filter_rows)
        add_button = QPushButton("Thêm nhóm mới")
        add_button.clicked.connect(self._add_group)
        tools.addWidget(self.search_input, 1)
        tools.addWidget(add_button)
        root.addLayout(tools)

        # Toolbar for selecting all filtered groups and bulk count
        selection_bar = QHBoxLayout()
        selection_bar.setSpacing(10)
        self.select_all_checkbox = SelectAllCheckBox("Chọn tất cả nhóm")
        self.select_all_checkbox.setTristate(True)
        self.select_all_checkbox.stateChanged.connect(self._on_select_all_changed)

        self.select_filtered_button = QPushButton("Chọn tất cả đang lọc")
        self.select_filtered_button.setProperty("density", "compact")
        self.select_filtered_button.setProperty("role", "ghost")
        self.select_filtered_button.clicked.connect(self._select_all_visible)

        self.unselect_filtered_button = QPushButton("Bỏ chọn")
        self.unselect_filtered_button.setProperty("density", "compact")
        self.unselect_filtered_button.setProperty("role", "ghost")
        self.unselect_filtered_button.clicked.connect(self._unselect_all_visible)

        bulk_label = QLabel("Số lượt chung:")
        bulk_label.setProperty("muted", True)
        self.bulk_count_input = QSpinBox()
        self.bulk_count_input.setRange(1, 999)
        self.bulk_count_input.setValue(1)
        self.bulk_count_input.setFixedWidth(70)
        self.bulk_apply_button = QPushButton("Áp dụng")
        self.bulk_apply_button.setProperty("density", "compact")
        self.bulk_apply_button.clicked.connect(self._apply_bulk_count)

        selection_bar.addWidget(self.select_all_checkbox)
        selection_bar.addWidget(self.select_filtered_button)
        selection_bar.addWidget(self.unselect_filtered_button)
        selection_bar.addStretch()
        selection_bar.addWidget(bulk_label)
        selection_bar.addWidget(self.bulk_count_input)
        selection_bar.addWidget(self.bulk_apply_button)
        root.addLayout(selection_bar)

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
        save.setText("Lưu lựa chọn")
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
                "Chưa có nhóm nào đang bật",
                "Thêm hoặc bật ít nhất một nhóm để tiếp tục.",
                "Thêm nhóm mới",
            )
            empty.action_requested.connect(self._add_group)
            self.rows_layout.addWidget(empty)
            self.rows_layout.addStretch()
            self._sync_select_all_state()
            return
        for group in groups:
            row = GroupSelectionRow(
                group,
                self.selected_counts.get(group.url, 0),
            )
            row.checkbox.toggled.connect(self._on_row_checkbox_toggled)
            self.rows.append(row)
            self.rows_layout.addWidget(row)
        self.rows_layout.addStretch()
        self._filter_rows()

    def _visible_rows(self) -> list[GroupSelectionRow]:
        return [row for row in self.rows if not row.isHidden()]

    def _filter_rows(self, query: str | None = None) -> None:
        if query is None:
            raw_query = self.search_input.effective_text().strip()
        else:
            raw_query = query.strip()
        needle = _normalize_search_text(raw_query)
        for row in self.rows:
            haystack = _normalize_search_text(
                f"{row.group.name} {row.group.url}"
            )
            matches = not needle or needle in haystack
            row.setHidden(not matches)
        self._sync_select_all_state()

    def _sync_select_all_state(self) -> None:
        if self._updating_selection:
            return
        visible = self._visible_rows()
        total = len(visible)
        selected = sum(1 for row in visible if row.checkbox.isChecked())

        blocker = QSignalBlocker(self.select_all_checkbox)
        self.select_all_checkbox.setEnabled(total > 0)
        self.select_filtered_button.setEnabled(total > 0)
        self.unselect_filtered_button.setEnabled(total > 0)

        if not selected:
            state = Qt.CheckState.Unchecked
        elif selected == total:
            state = Qt.CheckState.Checked
        else:
            state = Qt.CheckState.PartiallyChecked

        self.select_all_checkbox.setCheckState(state)

        is_filtered = bool(self.search_input.effective_text().strip())
        prefix = "Chọn tất cả nhóm đang lọc" if is_filtered else "Chọn tất cả nhóm"
        self.select_all_checkbox.setText(
            f"{prefix} ({selected}/{total})" if total else prefix
        )
        del blocker

    def _on_row_checkbox_toggled(self) -> None:
        self._sync_select_all_state()

    def _on_select_all_changed(self, state: int) -> None:
        visible = self._visible_rows()
        if not visible or self._updating_selection:
            return
        checked = state != Qt.CheckState.Unchecked.value
        self._set_visible_checked(checked)

    def _select_all_visible(self) -> None:
        self._set_visible_checked(True)

    def _unselect_all_visible(self) -> None:
        self._set_visible_checked(False)

    def _set_visible_checked(self, checked: bool) -> None:
        visible = self._visible_rows()
        if not visible:
            return
        self._updating_selection = True
        try:
            for row in visible:
                row.checkbox.setChecked(checked)
        finally:
            self._updating_selection = False
        self._sync_select_all_state()

    def _apply_bulk_count(self) -> None:
        visible = self._visible_rows()
        count = self.bulk_count_input.value()
        for row in visible:
            if row.checkbox.isChecked():
                row.count_input.setValue(count)

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
                "Chọn ít nhất một nhóm cho phòng này.",
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
