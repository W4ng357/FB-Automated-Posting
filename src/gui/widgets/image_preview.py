from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QImageReader, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from gui.widgets.design_components import RoundedThumbnail


THUMBNAIL_SIZE = QSize(128, 92)
COMPACT_THUMBNAIL_SIZE = QSize(116, 72)


class ImagePreview(QFrame):
    remove_requested = Signal(str)

    def __init__(
        self,
        image_path: Path,
        removable: bool = True,
        compact: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.image_path = image_path
        self.setProperty("imagePreview", True)
        self.setFixedWidth(136 if compact else 150)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(9, 9, 9, 9)
        layout.setSpacing(7)

        thumbnail_size = (
            COMPACT_THUMBNAIL_SIZE if compact else THUMBNAIL_SIZE
        )
        thumbnail = RoundedThumbnail(image_path, size=thumbnail_size)
        thumbnail.setToolTip(str(image_path))

        name_label = QLabel(image_path.name)
        name_label.setProperty("muted", True)
        name_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        name_label.setWordWrap(True)

        layout.addWidget(thumbnail)
        layout.addWidget(name_label)

        if removable:
            remove_button = QPushButton("Gỡ")
            remove_button.setProperty("role", "ghostDanger")
            remove_button.setProperty("density", "compact")
            remove_button.clicked.connect(
                lambda: self.remove_requested.emit(
                    str(self.image_path)
                )
            )
            layout.addWidget(remove_button)

    @staticmethod
    def _load_thumbnail(
        image_path: Path,
        thumbnail_size: QSize = THUMBNAIL_SIZE,
    ) -> QPixmap:
        reader = QImageReader(str(image_path))
        reader.setAutoTransform(True)

        image_size = reader.size()

        if image_size.isValid():
            image_size.scale(
                thumbnail_size,
                Qt.AspectRatioMode.KeepAspectRatio,
            )
            reader.setScaledSize(image_size)

        image = reader.read()

        if image.isNull():
            fallback = QPixmap(thumbnail_size)
            fallback.fill(Qt.GlobalColor.transparent)
            return fallback

        return QPixmap.fromImage(image).scaled(
            thumbnail_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
