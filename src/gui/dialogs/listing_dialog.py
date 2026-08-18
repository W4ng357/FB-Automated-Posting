from pathlib import Path

from PySide6.QtCore import (
    QFileSystemWatcher,
    QLocale,
    Qt,
    QTimer,
    QUrl,
)
from PySide6.QtGui import QCloseEvent, QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gui.widgets.facebook_post_preview import FacebookPostPreview
from gui.widgets.flow_layout import FlowLayout
from gui.widgets.image_preview import ImagePreview
from models.listing import Listing
from services.caption_generator import generate_caption
from services.content_loader import SUPPORTED_IMAGE_EXTENSIONS
from services.listing_draft_manager import ListingDraftManager
from services.listing_service import ListingService


class MillionPriceSpinBox(QDoubleSpinBox):
    VND_PER_MILLION = 1_000_000

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setLocale(QLocale("vi_VN"))
        self.setRange(0, 2_000)
        self.setDecimals(6)
        self.setSingleStep(0.1)
        self.setSuffix(" tr")

    def textFromValue(self, value: float) -> str:
        compact = f"{value:.6f}".rstrip("0").rstrip(".")
        return compact.replace(".", ",")

    def valueFromText(self, text: str) -> float:
        compact = text.strip()
        suffix = self.suffix().strip()
        if compact.casefold().endswith(suffix.casefold()):
            compact = compact[:-len(suffix)].strip()
        try:
            normalized = (
                compact.replace(".", "").replace(",", ".")
                if "," in compact
                else compact
            )
            return float(normalized)
        except ValueError:
            return 0.0

    def price_in_vnd(self) -> int:
        return round(self.value() * self.VND_PER_MILLION)

    def set_price_in_vnd(self, price: int) -> None:
        self.setValue(price / self.VND_PER_MILLION)


class AreaSpinBox(QDoubleSpinBox):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setLocale(QLocale("vi_VN"))
        self.setRange(0, 100_000)
        self.setDecimals(2)
        self.setSingleStep(1)
        self.setSuffix(" m²")
        self.setSpecialValueText("Chưa nhập")

    def textFromValue(self, value: float) -> str:
        compact = f"{value:.2f}".rstrip("0").rstrip(".")
        return compact.replace(".", ",")


class ListingDialog(QDialog):
    def __init__(
        self,
        listing_service: ListingService,
        listing: Listing | None = None,
        draft_manager: ListingDraftManager | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.listing_service = listing_service
        self.listing = listing
        self.saved_listing: Listing | None = None
        self.pending_images: list[Path] = []
        self.removed_image_names: set[str] = set()
        self.draft_manager = draft_manager or ListingDraftManager()
        self.draft_id = (
            self.draft_manager.create_draft()
            if listing is None
            else None
        )
        self._draft_cleaned = False
        self._compact_width = 1000

        if listing is None:
            self.images_dir = self.draft_manager.get_images_dir(
                self.draft_id
            )
            self.current_images = self.draft_manager.get_images(
                self.draft_id
            )
        else:
            self.images_dir = (
                self.listing_service.asset_manager
                .create_listing_folder(listing.id)
            )
            self.current_images = self.listing_service.get_images(
                listing.id
            )

        self.setWindowTitle(
            "Chỉnh sửa thông tin phòng" if listing else "Thêm phòng"
        )
        self.setMinimumSize(780, 660)
        self.resize(self._compact_width, 880)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(14)

        header = QHBoxLayout()
        heading = QVBoxLayout()
        heading.setSpacing(5)
        title = QLabel(
            "Chỉnh sửa thông tin phòng"
            if listing
            else "Thêm phòng mới"
        )
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            "Nhập thông tin và ảnh phòng; dữ liệu được lưu cục bộ trên máy này."
        )
        subtitle.setProperty("muted", True)
        subtitle.setWordWrap(True)
        heading.addWidget(title)
        heading.addWidget(subtitle)
        self.preview_button = QPushButton("Xem trước bài viết")
        self.preview_button.setProperty("role", "ghost")
        self.preview_button.setMinimumHeight(40)
        self.preview_button.clicked.connect(self._toggle_preview)
        header.addLayout(heading, 1)
        header.addWidget(self.preview_button)
        root.addLayout(header)

        self.editor_pane = QScrollArea()
        self.editor_pane.setWidgetResizable(True)
        self.editor_pane.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.editor_pane.setProperty("dialogBody", True)
        self.editor_content = QWidget()
        editor_layout = QVBoxLayout(self.editor_content)
        editor_layout.setContentsMargins(10, 10, 12, 10)
        editor_layout.setSpacing(16)
        self.details_panel = self._create_details_panel()
        self.images_panel = self._create_images_panel()
        editor_layout.addWidget(self.details_panel)
        editor_layout.addWidget(self.images_panel)
        editor_layout.addStretch()
        self.editor_pane.setWidget(self.editor_content)

        self.post_preview = FacebookPostPreview()
        self.workspace_tabs = QTabWidget()
        self.workspace_tabs.setObjectName("RoomEditorTabs")
        self.workspace_tabs.addTab(
            self.editor_pane,
            "Thông tin phòng",
        )
        self.workspace_tabs.addTab(
            self.post_preview,
            "Xem trước bài viết",
        )
        self.workspace_tabs.currentChanged.connect(
            self._on_workspace_tab_changed
        )
        root.addWidget(self.workspace_tabs, 1)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.save_button = self.buttons.button(
            QDialogButtonBox.StandardButton.Save
        )
        self.cancel_button = self.buttons.button(
            QDialogButtonBox.StandardButton.Cancel
        )
        self.save_button.setText("Lưu phòng")
        self.save_button.setIcon(QIcon())
        self.save_button.setProperty("role", "primary")
        self.cancel_button.setText("Hủy")
        self.cancel_button.setIcon(QIcon())
        self.buttons.accepted.connect(self._save)
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)

        self.file_watcher = QFileSystemWatcher(self)
        self.file_watcher.addPath(str(self.images_dir))
        self.file_watcher.directoryChanged.connect(
            self._refresh_images_from_disk
        )

        if listing is not None:
            self._populate_fields(listing)
        self._render_images()
        self._connect_preview_signals()
        self._update_preview()
        self._set_tab_order()
        QTimer.singleShot(0, self._stabilize_editor_layout)

    @staticmethod
    def _field_label(text: str, buddy: QWidget) -> QLabel:
        label = QLabel(text)
        label.setBuddy(buddy)
        return label

    def _create_details_panel(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("formSection", True)
        layout = QGridLayout(panel)
        layout.setContentsMargins(18, 17, 18, 18)
        layout.setHorizontalSpacing(18)
        layout.setVerticalSpacing(7)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)

        section_title = QLabel("Thông tin phòng")
        section_title.setObjectName("SectionTitle")
        layout.addWidget(section_title, 0, 0, 1, 2)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText(
            "Ví dụ: Phòng khép kín Thanh Xuân"
        )
        layout.addWidget(
            self._field_label("Tên phòng *", self.title_input), 1, 0
        )
        layout.addWidget(self.title_input, 2, 0)

        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText(
            "Số nhà, đường, quận/huyện, tỉnh/thành phố"
        )
        layout.addWidget(
            self._field_label("Địa chỉ *", self.address_input), 1, 1
        )
        layout.addWidget(self.address_input, 2, 1)

        self.price_input = MillionPriceSpinBox()
        layout.addWidget(
            self._field_label("Giá thuê *", self.price_input), 3, 0
        )
        layout.addWidget(self.price_input, 4, 0)

        self.area_input = AreaSpinBox()
        layout.addWidget(
            self._field_label("Diện tích", self.area_input), 3, 1
        )
        layout.addWidget(self.area_input, 4, 1)

        self.description_input = QPlainTextEdit()
        self.description_input.setPlaceholderText(
            "Mô tả nội thất, tiện ích và điều kiện thuê"
        )
        self.description_input.setMinimumHeight(72)
        self.description_input.setMaximumHeight(88)
        description_label = self._field_label(
            "Mô tả", self.description_input
        )
        description_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        layout.addWidget(description_label, 5, 0, 1, 2)
        layout.addWidget(self.description_input, 6, 0, 1, 2)

        self.contact_input = QLineEdit()
        self.contact_input.setPlaceholderText(
            "Số điện thoại hoặc cách liên hệ"
        )
        layout.addWidget(
            self._field_label("Liên hệ", self.contact_input), 7, 0
        )
        layout.addWidget(self.contact_input, 8, 0)

        self.enabled_input = QCheckBox("Sẵn sàng đưa vào hàng chờ đăng")
        self.enabled_input.setChecked(True)
        layout.addWidget(
            self._field_label("Trạng thái", self.enabled_input), 7, 1
        )
        layout.addWidget(self.enabled_input, 8, 1)
        return panel

    def _create_images_panel(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("formSection", True)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(9)

        header = QHBoxLayout()
        title = QLabel("Ảnh phòng *")
        title.setObjectName("SectionTitle")
        self.image_count_label = QLabel()
        self.image_count_label.setProperty("muted", True)
        self.refresh_images_button = QPushButton("Làm mới")
        self.refresh_images_button.setProperty("role", "ghost")
        self.refresh_images_button.setProperty("density", "compact")
        self.refresh_images_button.clicked.connect(
            self._refresh_images_from_disk
        )
        self.open_folder_button = QPushButton("Mở thư mục")
        self.open_folder_button.setProperty("density", "compact")
        self.open_folder_button.clicked.connect(self._open_images_folder)
        self.add_image_button = QPushButton("Thêm ảnh")
        self.add_image_button.setProperty("role", "primary")
        self.add_image_button.setProperty("density", "compact")
        self.add_image_button.clicked.connect(self._select_images)
        header.addWidget(title)
        header.addWidget(self.image_count_label)
        header.addStretch()
        header.addWidget(self.refresh_images_button)
        header.addWidget(self.open_folder_button)
        header.addWidget(self.add_image_button)
        layout.addLayout(header)

        note = QLabel(
            "Bắt buộc có ít nhất 1 ảnh. Ảnh tự sắp xếp theo chiều rộng "
            "và không tạo cuộn ngang."
        )
        note.setProperty("muted", True)
        note.setWordWrap(True)
        layout.addWidget(note)

        self.images_container = QWidget()
        self.images_layout = FlowLayout(
            self.images_container,
            horizontal_spacing=10,
            vertical_spacing=10,
        )
        self.images_container.setMinimumHeight(118)
        layout.addWidget(self.images_container)
        return panel

    def _connect_preview_signals(self) -> None:
        self.title_input.textChanged.connect(self._update_preview)
        self.address_input.textChanged.connect(self._update_preview)
        self.price_input.valueChanged.connect(self._update_preview)
        self.area_input.valueChanged.connect(self._update_preview)
        self.description_input.textChanged.connect(self._update_preview)
        self.contact_input.textChanged.connect(self._update_preview)

    def _set_tab_order(self) -> None:
        ordered = [
            self.title_input,
            self.address_input,
            self.price_input,
            self.area_input,
            self.description_input,
            self.contact_input,
            self.enabled_input,
            self.add_image_button,
            self.open_folder_button,
            self.refresh_images_button,
            self.preview_button,
            self.save_button,
            self.cancel_button,
        ]
        for current, following in zip(ordered, ordered[1:]):
            self.setTabOrder(current, following)

    def _populate_fields(self, listing: Listing) -> None:
        self.title_input.setText(listing.title)
        self.address_input.setText(
            listing.address.strip() or listing.location.strip()
        )
        self.price_input.set_price_in_vnd(listing.price)
        self.area_input.setValue(listing.area or 0)
        self.description_input.setPlainText(listing.description)
        self.contact_input.setText(listing.contact)
        self.enabled_input.setChecked(listing.enabled)

    def _toggle_preview(self) -> None:
        preview_index = self.workspace_tabs.indexOf(self.post_preview)
        editor_index = self.workspace_tabs.indexOf(self.editor_pane)
        if self.workspace_tabs.currentIndex() == preview_index:
            self.workspace_tabs.setCurrentIndex(editor_index)
        else:
            self._update_preview()
            self.workspace_tabs.setCurrentIndex(preview_index)

    def _on_workspace_tab_changed(self, index: int) -> None:
        is_preview = (
            self.workspace_tabs.widget(index) is self.post_preview
        )
        self.preview_button.setText(
            "Quay lại chỉnh sửa" if is_preview else "Xem trước bài viết"
        )

    def _stabilize_editor_layout(self) -> None:
        self._sync_image_gallery_height()
        self.editor_content.updateGeometry()
        self.workspace_tabs.updateGeometry()

    def _select_images(self) -> None:
        extensions = " ".join(
            f"*{extension}"
            for extension in sorted(SUPPORTED_IMAGE_EXTENSIONS)
        )
        selected_files, _ = QFileDialog.getOpenFileNames(
            self,
            "Chọn ảnh phòng",
            "",
            f"Ảnh ({extensions})",
        )
        selected = [Path(path).resolve() for path in selected_files]
        if not selected:
            return

        try:
            if self.draft_id is not None:
                self.draft_manager.add_images(self.draft_id, selected)
                self._refresh_images_from_disk()
            else:
                for image_path in selected:
                    if image_path not in self.pending_images:
                        self.pending_images.append(image_path)
                self._render_images()
        except Exception as error:
            QMessageBox.critical(self, "Không thể thêm ảnh", str(error))

    def _open_images_folder(self) -> None:
        self.images_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.images_dir)))

    def _refresh_images_from_disk(self, *_args) -> None:
        try:
            if self.draft_id is not None:
                self.current_images = self.draft_manager.get_images(
                    self.draft_id
                )
            else:
                self.current_images = self.listing_service.get_images(
                    self.listing.id
                )
        except Exception as error:
            QMessageBox.warning(self, "Không thể làm mới ảnh", str(error))
            return
        self._render_images()

    def _visible_images(self) -> list[Path]:
        current = [
            image
            for image in self.current_images
            if image.name not in self.removed_image_names
        ]
        return current + [
            image for image in self.pending_images if image not in current
        ]

    def _render_images(self) -> None:
        self.images_layout.clear()
        visible_images = self._visible_images()
        count = len(visible_images)
        self.image_count_label.setText(
            f"· {count} ảnh" if count else "· Chưa có ảnh"
        )
        if not visible_images:
            empty_label = QLabel(
                "Chưa có ảnh. Hãy thêm ít nhất 1 ảnh hoặc chép ảnh vào "
                "thư mục phòng trước khi lưu."
            )
            empty_label.setProperty("muted", True)
            empty_label.setWordWrap(True)
            self.images_layout.addWidget(empty_label)
        else:
            for image_path in visible_images:
                preview = ImagePreview(image_path, compact=True)
                preview.remove_requested.connect(
                    self._remove_image_from_selection
                )
                self.images_layout.addWidget(preview)
        self._update_preview()
        QTimer.singleShot(0, self._sync_image_gallery_height)

    def _sync_image_gallery_height(self) -> None:
        width = max(self.images_container.width(), 180)
        content_height = self.images_layout.heightForWidth(width)
        self.images_container.setMinimumHeight(max(content_height, 115))
        self.images_panel.updateGeometry()
        self.editor_content.updateGeometry()

    def _remove_image_from_selection(self, image_path_text: str) -> None:
        image_path = Path(image_path_text)
        try:
            if (
                self.draft_id is not None
                and image_path.parent.resolve() == self.images_dir.resolve()
            ):
                self.draft_manager.remove_image(
                    self.draft_id,
                    image_path.name,
                )
                self._refresh_images_from_disk()
                return
            if image_path in self.pending_images:
                self.pending_images.remove(image_path)
            else:
                self.removed_image_names.add(image_path.name)
            self._render_images()
        except Exception as error:
            QMessageBox.critical(self, "Không thể gỡ ảnh", str(error))

    def _listing_values(self) -> dict[str, object]:
        title = self.title_input.text().strip()
        address = self.address_input.text().strip()
        if not title:
            raise ValueError("Cần nhập tên phòng")
        if not address:
            raise ValueError("Cần nhập địa chỉ phòng")
        area_value = self.area_input.value()
        return {
            "title": title,
            "location": address,
            "price": self.price_input.price_in_vnd(),
            "address": address,
            "area": area_value if area_value > 0 else None,
            "description": self.description_input.toPlainText().strip(),
            "contact": self.contact_input.text().strip(),
            "enabled": self.enabled_input.isChecked(),
        }

    def _build_preview_listing(self) -> Listing:
        title = self.title_input.text().strip() or "Tên phòng"
        address = self.address_input.text().strip() or "Địa chỉ phòng"
        area_value = self.area_input.value()
        return Listing(
            id=self.listing.id if self.listing else "PREVIEW",
            title=title,
            location=address,
            price=self.price_input.price_in_vnd(),
            address=address,
            area=area_value if area_value > 0 else None,
            description=self.description_input.toPlainText().strip(),
            contact=self.contact_input.text().strip(),
            enabled=self.enabled_input.isChecked(),
        )

    def _update_preview(self, *_args) -> None:
        caption = generate_caption(self._build_preview_listing())
        self.post_preview.set_content(caption, self._visible_images())

    def _has_required_images(self) -> bool:
        if self._visible_images():
            return True

        self.workspace_tabs.setCurrentWidget(self.editor_pane)
        self.editor_pane.ensureWidgetVisible(
            self.images_panel,
            24,
            24,
        )
        self.add_image_button.setFocus()
        QMessageBox.warning(
            self,
            "Thiếu ảnh phòng",
            "Hãy thêm ít nhất 1 ảnh phòng trước khi lưu.",
        )
        return False

    def _save(self) -> None:
        try:
            values = self._listing_values()
            if not self._has_required_images():
                return
            if self.listing is None:
                self.saved_listing = self.listing_service.create_listing(
                    **values,
                    image_paths=self._visible_images(),
                )
            else:
                self.saved_listing = self.listing_service.update_listing(
                    self.listing.id,
                    **values,
                )
                if self.pending_images:
                    self.listing_service.add_images(
                        self.listing.id,
                        self.pending_images,
                    )
                for image_name in sorted(self.removed_image_names):
                    self.listing_service.remove_image(
                        self.listing.id,
                        image_name,
                    )
        except Exception as error:
            QMessageBox.critical(self, "Không thể lưu phòng", str(error))
            return

        self._cleanup_draft()
        self.accept()

    def _cleanup_draft(self) -> None:
        if self.draft_id is None or self._draft_cleaned:
            return
        try:
            self.draft_manager.cleanup(self.draft_id)
        finally:
            self._draft_cleaned = True

    def reject(self) -> None:
        self._cleanup_draft()
        super().reject()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.result() != QDialog.DialogCode.Accepted:
            self._cleanup_draft()
        super().closeEvent(event)
