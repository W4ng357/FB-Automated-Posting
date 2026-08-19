from __future__ import annotations

import unicodedata
from pathlib import Path

from PySide6.QtCore import QSignalBlocker, QSize, Qt, Signal
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

from gui.widgets.design_components import (
    EmptyState,
    RoundedThumbnail,
    SearchLineEdit,
)
from models.group_target import GroupTarget
from models.listing import Listing
from models.listing_posting_task import ListingPostingTask
from models.saved_group import SavedGroup
from services.caption_generator import format_area, format_price
from services.group_service import GroupService
from services.listing_service import ListingService


def _normalize_search_text(value: str) -> str:
    """Return a case- and accent-insensitive value for Vietnamese search."""
    decomposed = unicodedata.normalize("NFD", value.casefold())
    without_marks = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    return without_marks.replace("đ", "d")


class SelectAllCheckBox(QCheckBox):
    """A tri-state summary whose click always means select/clear all."""

    def nextCheckState(self) -> None:
        next_state = (
            Qt.CheckState.Unchecked
            if self.checkState() == Qt.CheckState.Checked
            else Qt.CheckState.Checked
        )
        self.setCheckState(next_state)


class RoomPlanRow(QFrame):
    activated = Signal(str)
    checked_changed = Signal(str, bool)

    def __init__(
        self,
        listing: Listing,
        image_path: Path | None,
        checked: bool,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.listing = listing
        self.setProperty("roomPlanRow", True)
        self.setProperty("active", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(f"Cấu hình phòng {listing.title}")

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 10, 10, 10)
        root.setSpacing(10)
        display_title = (
            listing.title.strip()
            or listing.address.strip()
            or listing.location.strip()
            or f"Phòng {listing.id}"
        )
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(checked)
        self.checkbox.setToolTip(f"Chọn {display_title}")
        self.checkbox.toggled.connect(
            lambda value: self.checked_changed.emit(listing.id, value)
        )
        thumbnail = RoundedThumbnail(
            image_path,
            display_title,
            QSize(58, 58),
        )
        info = QVBoxLayout()
        info.setSpacing(3)
        title = QLabel(display_title)
        title.setObjectName("CardTitle")
        title.setWordWrap(True)
        unit = getattr(listing, "price_unit", "TR") or "TR"
        details = [listing.id, format_price(listing.price, unit)]
        if listing.area is not None:
            details.append(f"{format_area(listing.area)}m²")
        metadata = QLabel(" · ".join(details))
        metadata.setProperty("muted", True)
        address = QLabel(listing.address.strip() or listing.location.strip())
        address.setProperty("meta", True)
        address.setWordWrap(True)
        if not listing.title.strip():
            address.hide()
        self.plan_summary = QLabel("Chưa chọn nhóm")
        self.plan_summary.setProperty("planMeta", True)
        info.addWidget(title)
        info.addWidget(metadata)
        info.addWidget(address)
        info.addWidget(self.plan_summary)
        root.addWidget(self.checkbox, 0, Qt.AlignmentFlag.AlignTop)
        root.addWidget(thumbnail, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(info, 1)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            self.activated.emit(self.listing.id)
            event.accept()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() in {
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
            Qt.Key.Key_Space,
        }:
            self.activated.emit(self.listing.id)
            event.accept()
            return
        super().keyPressEvent(event)

    def set_active(self, active: bool) -> None:
        self.setProperty("active", active)
        style = self.style()
        style.unpolish(self)
        style.polish(self)

    def set_plan_summary(self, group_count: int, attempts: int) -> None:
        if not group_count:
            self.plan_summary.setText("Chưa chọn nhóm")
            return
        self.plan_summary.setText(
            f"{group_count} nhóm · {attempts} lượt đăng"
        )


class PlanGroupRow(QFrame):
    changed = Signal()

    def __init__(
        self,
        group: SavedGroup,
        selected_count: int,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.group = group
        self.setProperty("groupRow", True)
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(10)
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(selected_count > 0)
        self.checkbox.setToolTip(f"Chọn {group.name}")
        name = QLabel(group.name)
        name.setObjectName("CardTitle")
        name.setWordWrap(True)
        self.count_input = QSpinBox()
        self.count_input.setRange(1, 999)
        self.count_input.setValue(selected_count or 1)
        self.count_input.setPrefix("Số lượt: ")
        self.count_input.setFixedWidth(132)
        self.count_input.setEnabled(self.checkbox.isChecked())
        self.checkbox.toggled.connect(self.count_input.setEnabled)
        self.checkbox.toggled.connect(lambda _checked: self.changed.emit())
        self.count_input.valueChanged.connect(
            lambda _value: self.changed.emit()
        )
        root.addWidget(self.checkbox, 0, Qt.AlignmentFlag.AlignTop)
        root.addWidget(name, 1, Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(self.count_input, 0, Qt.AlignmentFlag.AlignVCenter)

    def selected_count(self) -> int:
        return self.count_input.value() if self.checkbox.isChecked() else 0


class PostingPlanDialog(QDialog):
    """Configure per-room group targets without expanding the posting page."""

    def __init__(
        self,
        listing_service: ListingService,
        group_service: GroupService,
        tasks: list[ListingPostingTask] | None = None,
        scope_title: str | None = None,
        scope_description: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.listing_service = listing_service
        self.group_service = group_service
        self.listings = [
            listing
            for listing in listing_service.get_all()
            if listing.enabled
        ]
        self.groups = [
            group for group in group_service.get_all() if group.enabled
        ]
        self._listing_by_id = {
            listing.id: listing for listing in self.listings
        }
        self._room_counts: dict[str, dict[str, int]] = {}
        self._room_names: dict[str, dict[str, str]] = {}
        self.room_rows: dict[str, RoomPlanRow] = {}
        self.group_rows: list[PlanGroupRow] = []
        self.group_no_results: QLabel | None = None
        self._active_listing_id: str | None = None
        self._updating_group_selection = False

        for task in tasks or []:
            if task.listing_id not in self._listing_by_id:
                continue
            self._room_counts[task.listing_id] = {
                target.url: target.target_count
                for target in task.group_targets
            }
            self._room_names[task.listing_id] = dict(task.group_names)

        self.setWindowTitle(scope_title or "Chọn phòng và nhóm")
        self.setMinimumSize(920, 600)
        self.resize(1080, 700)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(14)
        title = QLabel(scope_title or "Thiết lập kế hoạch đăng")
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            scope_description
            or "Chọn phòng ở bên trái, sau đó đặt nhóm và số lượt riêng "
            "cho từng phòng ở bên phải."
        )
        subtitle.setProperty("muted", True)
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        columns = QHBoxLayout()
        columns.setSpacing(14)
        columns.addWidget(self._create_room_panel(), 5)
        columns.addWidget(self._create_group_panel(), 6)
        root.addLayout(columns, 1)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        save = self.buttons.button(QDialogButtonBox.StandardButton.Save)
        cancel = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        save.setText("Lưu kế hoạch")
        save.setIcon(QIcon())
        save.setProperty("role", "primary")
        cancel.setText("Hủy")
        cancel.setIcon(QIcon())
        self.buttons.accepted.connect(self._accept_plan)
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)

        self._render_room_rows()
        initial = next(iter(self._room_counts), None)
        if initial is None and self.listings:
            initial = self.listings[0].id
        self._activate_room(initial)

    def _create_room_panel(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("selectionPane", True)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        heading = QLabel("1. Chọn phòng")
        heading.setObjectName("SectionTitle")
        helper = QLabel(
            "Chọn phòng cần đăng, rồi bấm vào phòng để chọn nhóm."
        )
        helper.setProperty("muted", True)
        helper.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(helper)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.room_container = QWidget()
        self.room_layout = QVBoxLayout(self.room_container)
        self.room_layout.setContentsMargins(0, 0, 6, 0)
        self.room_layout.setSpacing(8)
        scroll.setWidget(self.room_container)
        layout.addWidget(scroll, 1)
        return panel

    def _create_group_panel(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("selectionPane", True)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        self.group_heading = QLabel("2. Chọn nhóm và số lượt")
        self.group_heading.setObjectName("SectionTitle")
        self.active_room_label = QLabel("Chưa chọn phòng")
        self.active_room_label.setProperty("muted", True)
        self.active_room_label.setWordWrap(True)
        layout.addWidget(self.group_heading)
        layout.addWidget(self.active_room_label)

        self.group_search_input = SearchLineEdit(
            placeholder="Tìm theo tên hoặc đường dẫn nhóm…"
        )
        self.group_search_input.setMaxLength(240)
        self.group_search_input.setAccessibleName("Tìm nhóm trong danh sách")
        self.group_search_input.setToolTip(
            "Có thể tìm theo tên, đường dẫn hoặc từ khóa không dấu."
        )
        self.group_search_input.liveTextChanged.connect(
            self._filter_group_rows
        )
        layout.addWidget(self.group_search_input)

        select_row = QHBoxLayout()
        select_row.setSpacing(10)
        self.select_all_groups = SelectAllCheckBox("Chọn tất cả nhóm")
        self.select_all_groups.setTristate(True)
        self.select_all_groups.setAccessibleName(
            "Chọn hoặc bỏ chọn tất cả nhóm của phòng đang cấu hình"
        )
        self.select_all_groups.stateChanged.connect(
            self._on_select_all_groups_changed
        )
        self.select_filtered_button = QPushButton("Chọn tất cả đang lọc")
        self.select_filtered_button.setProperty("density", "compact")
        self.select_filtered_button.setProperty("role", "ghost")
        self.select_filtered_button.clicked.connect(
            lambda: self._set_visible_groups_checked(True)
        )

        self.unselect_filtered_button = QPushButton("Bỏ chọn")
        self.unselect_filtered_button.setProperty("density", "compact")
        self.unselect_filtered_button.setProperty("role", "ghost")
        self.unselect_filtered_button.clicked.connect(
            lambda: self._set_visible_groups_checked(False)
        )

        select_row.addWidget(self.select_all_groups)
        select_row.addWidget(self.select_filtered_button)
        select_row.addWidget(self.unselect_filtered_button)
        select_row.addStretch()
        layout.addLayout(select_row)

        bulk = QHBoxLayout()
        bulk.setSpacing(8)
        bulk_label = QLabel("Đặt cùng số lượt cho các nhóm đã chọn")
        bulk_label.setProperty("muted", True)
        self.bulk_count_input = QSpinBox()
        self.bulk_count_input.setRange(1, 999)
        self.bulk_count_input.setValue(1)
        self.bulk_count_input.setFixedWidth(78)
        apply_bulk = QPushButton("Áp dụng")
        apply_bulk.setProperty("density", "compact")
        apply_bulk.clicked.connect(self._apply_bulk_count)
        bulk.addWidget(bulk_label)
        bulk.addStretch()
        bulk.addWidget(self.bulk_count_input)
        bulk.addWidget(apply_bulk)
        layout.addLayout(bulk)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.group_container = QWidget()
        self.group_layout = QVBoxLayout(self.group_container)
        self.group_layout.setContentsMargins(0, 0, 6, 0)
        self.group_layout.setSpacing(8)
        scroll.setWidget(self.group_container)
        layout.addWidget(scroll, 1)
        return panel

    def _render_room_rows(self) -> None:
        while self.room_layout.count():
            item = self.room_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self.room_rows.clear()
        if not self.listings:
            self.room_layout.addWidget(
                EmptyState(
                    "Chưa có phòng nào đang bật",
                    "Hãy thêm ảnh và bật ít nhất một phòng để lập kế hoạch.",
                )
            )
            self.room_layout.addStretch()
            return
        for listing in self.listings:
            row = RoomPlanRow(
                listing,
                self._first_listing_image(listing.id),
                listing.id in self._room_counts,
            )
            row.activated.connect(self._activate_room)
            row.checked_changed.connect(self._on_room_checked)
            self.room_rows[listing.id] = row
            self.room_layout.addWidget(row)
            self._update_room_summary(listing.id)
        self.room_layout.addStretch()

    def _activate_room(self, listing_id: str | None) -> None:
        if listing_id is None or listing_id not in self._listing_by_id:
            self._active_listing_id = None
            self.active_room_label.setText("Chưa chọn phòng")
            self._render_group_rows()
            return
        self._save_active_counts()
        self._active_listing_id = listing_id
        for room_id, row in self.room_rows.items():
            row.set_active(room_id == listing_id)
        listing = self._listing_by_id[listing_id]
        self.active_room_label.setText(f"Đang chọn nhóm cho: {listing.title}")
        self._render_group_rows()

    def _on_room_checked(self, listing_id: str, checked: bool) -> None:
        if checked:
            self._room_counts.setdefault(listing_id, {})
            self._room_names.setdefault(listing_id, {})
        else:
            self._room_counts.pop(listing_id, None)
            self._room_names.pop(listing_id, None)
        self._update_room_summary(listing_id)
        if checked:
            if self._active_listing_id == listing_id:
                self._render_group_rows()
            else:
                self._activate_room(listing_id)
        elif self._active_listing_id == listing_id:
            self._render_group_rows()

    def _render_group_rows(self) -> None:
        while self.group_layout.count():
            item = self.group_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self.group_rows.clear()
        self.group_no_results = None
        if self._active_listing_id is None:
            self.group_search_input.setEnabled(False)
            self._sync_select_all_groups()
            self.group_layout.addWidget(
                EmptyState(
                    "Chọn một phòng",
                    "Bấm vào một phòng ở cột bên trái để chọn nhóm đăng.",
                )
            )
            self.group_layout.addStretch()
            return
        if not self.groups:
            self.group_search_input.setEnabled(False)
            self._sync_select_all_groups()
            self.group_layout.addWidget(
                EmptyState(
                    "Chưa có nhóm nào đang bật",
                    "Hãy thêm hoặc bật ít nhất một nhóm để lập kế hoạch.",
                )
            )
            self.group_layout.addStretch()
            return
        counts = self._room_counts.get(self._active_listing_id, {})
        for group in self.groups:
            row = PlanGroupRow(group, counts.get(group.url, 0))
            row.changed.connect(self._on_group_row_changed)
            self.group_rows.append(row)
            self.group_layout.addWidget(row)
        self.group_search_input.setEnabled(True)
        self.group_no_results = QLabel(
            "Không tìm thấy nhóm phù hợp.\n"
            "Thử dùng tên hoặc một phần đường dẫn khác."
        )
        self.group_no_results.setProperty("muted", True)
        self.group_no_results.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.group_no_results.setWordWrap(True)
        self.group_no_results.setContentsMargins(16, 24, 16, 24)
        self.group_no_results.hide()
        self.group_layout.addWidget(self.group_no_results)
        self.group_layout.addStretch()
        self._filter_group_rows(self.group_search_input.text())

    def _filter_group_rows(self, query: str) -> None:
        needle = _normalize_search_text(query.strip())
        visible_count = 0
        for row in self.group_rows:
            haystack = _normalize_search_text(
                f"{row.group.name} {row.group.url}"
            )
            matches = not needle or needle in haystack
            row.setHidden(not matches)
            visible_count += int(matches)
        if self.group_no_results is not None:
            self.group_no_results.setVisible(
                bool(needle) and visible_count == 0
            )
        self._sync_select_all_groups()

    def _visible_group_rows(self) -> list[PlanGroupRow]:
        return [row for row in self.group_rows if not row.isHidden()]

    def _on_group_row_changed(self) -> None:
        if self._updating_group_selection:
            return
        if any(row.checkbox.isChecked() for row in self.group_rows):
            self._ensure_active_room_selected()
        self._save_active_counts()
        self._sync_select_all_groups()

    def _on_select_all_groups_changed(self, state: int) -> None:
        if self._updating_group_selection:
            return
        checked = state != Qt.CheckState.Unchecked.value
        self._set_visible_groups_checked(checked)

    def _set_visible_groups_checked(self, checked: bool) -> None:
        visible_rows = self._visible_group_rows()
        if not visible_rows:
            return
        if checked:
            self._ensure_active_room_selected()
        self._updating_group_selection = True
        try:
            for row in visible_rows:
                row.checkbox.setChecked(checked)
        finally:
            self._updating_group_selection = False
        self._save_active_counts()
        self._sync_select_all_groups()

    def _sync_select_all_groups(self) -> None:
        visible_rows = self._visible_group_rows()
        total = len(visible_rows)
        selected = sum(row.checkbox.isChecked() for row in visible_rows)

        if hasattr(self, "select_filtered_button"):
            self.select_filtered_button.setEnabled(total > 0)
        if hasattr(self, "unselect_filtered_button"):
            self.unselect_filtered_button.setEnabled(total > 0)

        if not selected:
            state = Qt.CheckState.Unchecked
        elif selected == total:
            state = Qt.CheckState.Checked
        else:
            state = Qt.CheckState.PartiallyChecked
        blocker = QSignalBlocker(self.select_all_groups)
        self.select_all_groups.setEnabled(total > 0)
        self.select_all_groups.setCheckState(state)
        filtered = bool(self.group_search_input.effective_text().strip())
        label = (
            "Chọn tất cả nhóm đang hiển thị"
            if filtered
            else "Chọn tất cả nhóm"
        )
        self.select_all_groups.setText(
            f"{label} ({selected}/{total})"
            if total
            else label
        )
        del blocker

    def _ensure_active_room_selected(self) -> None:
        listing_id = self._active_listing_id
        row = self.room_rows.get(listing_id) if listing_id else None
        if row is None or row.checkbox.isChecked():
            return
        blocker = QSignalBlocker(row.checkbox)
        row.checkbox.setChecked(True)
        del blocker
        self._room_counts.setdefault(listing_id, {})
        self._room_names.setdefault(listing_id, {})

    def _save_active_counts(self) -> None:
        listing_id = self._active_listing_id
        if listing_id is None or not self.group_rows:
            return
        counts = {
            row.group.url: row.selected_count()
            for row in self.group_rows
            if row.selected_count() > 0
        }
        names = {
            row.group.url: row.group.name
            for row in self.group_rows
            if row.selected_count() > 0
        }
        row = self.room_rows.get(listing_id)
        if row is not None and row.checkbox.isChecked():
            self._room_counts[listing_id] = counts
            self._room_names[listing_id] = names
        self._update_room_summary(listing_id)

    def _update_room_summary(self, listing_id: str) -> None:
        row = self.room_rows.get(listing_id)
        if row is None:
            return
        counts = self._room_counts.get(listing_id, {})
        row.set_plan_summary(len(counts), sum(counts.values()))

    def _apply_bulk_count(self) -> None:
        selected = [row for row in self.group_rows if row.checkbox.isChecked()]
        if not selected:
            QMessageBox.information(
                self,
                "Chưa chọn nhóm",
                "Chọn ít nhất một nhóm trước khi áp dụng số lượt.",
            )
            return
        value = self.bulk_count_input.value()
        for row in selected:
            row.count_input.setValue(value)
        self._save_active_counts()

    def _accept_plan(self) -> None:
        self._save_active_counts()
        selected_ids = [
            listing.id
            for listing in self.listings
            if self.room_rows[listing.id].checkbox.isChecked()
        ]
        if not selected_ids:
            QMessageBox.warning(
                self,
                "Chưa chọn phòng",
                "Chọn ít nhất một phòng cho kế hoạch đăng.",
            )
            return
        missing = [
            self._listing_by_id[listing_id].title
            for listing_id in selected_ids
            if not self._room_counts.get(listing_id)
        ]
        if missing:
            QMessageBox.warning(
                self,
                "Phòng chưa có nhóm",
                "Chọn ít nhất một nhóm cho: " + ", ".join(missing),
            )
            return
        self.accept()

    def selected_tasks(self) -> list[ListingPostingTask]:
        self._save_active_counts()
        tasks: list[ListingPostingTask] = []
        for listing in self.listings:
            row = self.room_rows.get(listing.id)
            if row is None or not row.checkbox.isChecked():
                continue
            counts = self._room_counts.get(listing.id, {})
            if not counts:
                continue
            tasks.append(
                ListingPostingTask(
                    listing_id=listing.id,
                    listing_title=listing.title,
                    group_targets=[
                        GroupTarget(url=url, target_count=count)
                        for url, count in counts.items()
                    ],
                    group_names=dict(self._room_names.get(listing.id, {})),
                )
            )
        return tasks

    def _first_listing_image(self, listing_id: str) -> Path | None:
        try:
            images = self.listing_service.get_images(listing_id)
        except (KeyError, OSError):
            return None
        return images[0] if images else None
