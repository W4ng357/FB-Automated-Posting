from pathlib import Path

from PySide6.QtCore import QEasingCurve, QRectF, QSize, Qt, Signal, QVariantAnimation
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QImageReader,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)


class StatusBadge(QLabel):
    """Compact, text-backed status indicator shared across the GUI."""

    def __init__(
        self,
        text: str,
        state: str = "idle",
        parent=None,
    ) -> None:
        super().__init__(text, parent)
        self.setProperty("badge", True)
        self.set_state(text, state)

    def set_state(self, text: str, state: str) -> None:
        self.setText(text)
        self.setProperty("state", state)
        style = self.style()
        style.unpolish(self)
        style.polish(self)


def circular_avatar_icon(
    image_path: Path | None,
    size: QSize = QSize(22, 22),
) -> QIcon:
    """Build a transparent, center-cropped circular icon for account tabs."""
    if image_path is None:
        return QIcon()

    reader = QImageReader(str(image_path))
    reader.setAutoTransform(True)
    source_size = reader.size()
    if source_size.isValid():
        source_size.scale(
            QSize(size.width() * 2, size.height() * 2),
            Qt.AspectRatioMode.KeepAspectRatio,
        )
        reader.setScaledSize(source_size)
    image = reader.read()
    if image.isNull():
        return QIcon()

    source = QPixmap.fromImage(image).scaled(
        size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    canvas = QPixmap(size)
    canvas.fill(Qt.GlobalColor.transparent)

    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    bounds = QRectF(canvas.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
    shape = QPainterPath()
    shape.addEllipse(bounds)
    painter.setClipPath(shape)
    painter.fillPath(shape, QColor("#202029"))
    painter.drawPixmap(
        (canvas.width() - source.width()) // 2,
        (canvas.height() - source.height()) // 2,
        source,
    )
    painter.setClipping(False)
    painter.setPen(QPen(QColor("#30303A"), 1))
    painter.drawPath(shape)
    painter.end()
    return QIcon(canvas)


class EmptyState(QFrame):
    """Restrained empty state with an optional local call to action."""

    action_requested = Signal()

    def __init__(
        self,
        title: str,
        description: str,
        action_text: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("emptyState", True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 32, 28, 32)
        layout.setSpacing(8)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("EmptyStateTitle")
        self.description_label = QLabel(description)
        self.description_label.setProperty("muted", True)
        self.description_label.setWordWrap(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.description_label)

        self.action_button = QPushButton(action_text or "")
        self.action_button.setProperty("role", "primary")
        self.action_button.setProperty("density", "compact")
        self.action_button.setVisible(bool(action_text))
        self.action_button.clicked.connect(self.action_requested)
        layout.addSpacing(6)
        layout.addWidget(
            self.action_button,
            0,
            Qt.AlignmentFlag.AlignLeft,
        )

    def set_content(self, title: str, description: str) -> None:
        self.title_label.setText(title)
        self.description_label.setText(description)


class RoundedThumbnail(QLabel):
    """Small cached image/initial preview with a clipped media mask."""

    def __init__(
        self,
        image_path: Path | None = None,
        fallback_text: str = "",
        size: QSize = QSize(76, 76),
        circular: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._source = QPixmap()
        self._fallback_text = ""
        self._radius = 11.0
        self._circular = circular
        self.setFixedSize(size)
        self.set_source(image_path, fallback_text)

    def set_source(
        self,
        image_path: Path | None,
        fallback_text: str = "",
    ) -> None:
        self._source = QPixmap()
        self._fallback_text = fallback_text[:1].upper()
        self.setAccessibleName(
            "Ảnh đại diện" if image_path else "Ký hiệu nhận diện"
        )

        if image_path is not None:
            reader = QImageReader(str(image_path))
            reader.setAutoTransform(True)
            source_size = reader.size()
            if source_size.isValid():
                source_size.scale(
                    QSize(self.width() * 2, self.height() * 2),
                    Qt.AspectRatioMode.KeepAspectRatio,
                )
                reader.setScaledSize(source_size)
            image = reader.read()
            if not image.isNull():
                self._source = QPixmap.fromImage(image)
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        bounds = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        shape = QPainterPath()
        if self._circular:
            shape.addEllipse(bounds)
        else:
            shape.addRoundedRect(bounds, self._radius, self._radius)
        painter.setClipPath(shape)
        painter.fillPath(shape, QColor("#202029"))

        if not self._source.isNull():
            scaled = self._source.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        elif self._fallback_text:
            painter.setPen(QColor("#D9CCFF"))
            font = painter.font()
            font.setPointSize(16)
            font.setWeight(QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                self._fallback_text,
            )

        painter.setClipping(False)
        painter.setPen(QPen(QColor("#30303A"), 1))
        painter.drawPath(shape)


class SmoothProgressBar(QProgressBar):
    """Progress bar with one inexpensive, interruptible value animation."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(320)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.valueChanged.connect(
            lambda value: QProgressBar.setValue(self, round(float(value)))
        )

    def set_animated_value(self, value: int) -> None:
        target = max(self.minimum(), min(value, self.maximum()))
        if not self.isVisible() or target == self.value():
            self._animation.stop()
            QProgressBar.setValue(self, target)
            return
        self._animation.stop()
        self._animation.setStartValue(self.value())
        self._animation.setEndValue(target)
        self._animation.start()
