from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImageReader, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class PreviewImageLabel(QLabel):
    def __init__(self, image_path: Path, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("facebookMedia", True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(120, 105)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        reader = QImageReader(str(image_path))
        reader.setAutoTransform(True)
        source_size = reader.size()
        if source_size.isValid():
            source_size.scale(
                1200,
                1200,
                Qt.AspectRatioMode.KeepAspectRatio,
            )
            reader.setScaledSize(source_size)
        image = reader.read()
        self._source = QPixmap.fromImage(image)
        if self._source.isNull():
            self.setText("Không đọc được ảnh")
            self.setProperty("muted", True)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._source.isNull():
            return
        self.setPixmap(
            self._source.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        )


class FacebookMediaGrid(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("facebookMediaGrid", True)
        self.setMinimumHeight(230)
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setHorizontalSpacing(3)
        self.layout.setVerticalSpacing(3)

    def set_images(self, image_paths: list[Path]) -> None:
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        visible = image_paths[:4]
        if not visible:
            empty = QLabel("Chưa có ảnh trong bài viết")
            empty.setProperty("facebookMedia", True)
            empty.setProperty("muted", True)
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.layout.addWidget(empty, 0, 0, 2, 2)
            return

        labels = [PreviewImageLabel(path) for path in visible]
        if len(labels) == 1:
            self.layout.addWidget(labels[0], 0, 0, 2, 2)
        elif len(labels) == 2:
            self.layout.addWidget(labels[0], 0, 0, 2, 1)
            self.layout.addWidget(labels[1], 0, 1, 2, 1)
        elif len(labels) == 3:
            self.layout.addWidget(labels[0], 0, 0, 2, 1)
            self.layout.addWidget(labels[1], 0, 1)
            self.layout.addWidget(labels[2], 1, 1)
        else:
            for index, label in enumerate(labels):
                self.layout.addWidget(label, index // 2, index % 2)


class FacebookPostPreview(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("previewPane", True)
        self.setMinimumWidth(370)
        self._image_paths: list[Path] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        heading = QVBoxLayout()
        heading.setSpacing(3)
        title = QLabel("Xem trước bài viết")
        title.setObjectName("SectionTitle")
        hint = QLabel("Bài viết sẽ hiển thị gần giống thế này trên Facebook")
        hint.setProperty("muted", True)
        heading.addWidget(title)
        heading.addWidget(hint)
        header.addLayout(heading, 1)
        root.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setProperty("previewScroll", True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 8, 0)
        content_layout.setSpacing(10)

        post = QFrame()
        post.setProperty("facebookPost", True)
        post.setMinimumWidth(520)
        post.setMaximumWidth(720)
        post.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        post_layout = QVBoxLayout(post)
        post_layout.setContentsMargins(0, 0, 0, 0)
        post_layout.setSpacing(0)

        post_header = QHBoxLayout()
        post_header.setContentsMargins(14, 14, 14, 10)
        post_header.setSpacing(10)
        avatar = QLabel("P")
        avatar.setProperty("previewAvatar", True)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setFixedSize(38, 38)
        author = QVBoxLayout()
        author.setSpacing(2)
        author_name = QLabel("Bài đăng của bạn")
        author_name.setObjectName("CardTitle")
        context = QLabel("Vừa xong · Nhóm Facebook")
        context.setProperty("muted", True)
        author.addWidget(author_name)
        author.addWidget(context)
        post_header.addWidget(avatar)
        post_header.addLayout(author, 1)
        post_layout.addLayout(post_header)

        self.caption = QLabel()
        self.caption.setProperty("facebookCaption", True)
        self.caption.setWordWrap(True)
        self.caption.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.caption.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        post_layout.addWidget(self.caption)

        self.media_grid = FacebookMediaGrid()
        post_layout.addWidget(self.media_grid)

        self.image_count = QLabel()
        self.image_count.setProperty("facebookImageCount", True)
        self.image_count.setProperty("muted", True)
        post_layout.addWidget(self.image_count)

        actions = QLabel("Thích        Bình luận        Chia sẻ")
        actions.setProperty("facebookActions", True)
        actions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        post_layout.addWidget(actions)

        content_layout.addWidget(
            post,
            0,
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter,
        )
        note = QLabel(
            "Cách hiển thị thực tế có thể khác đôi chút tùy nhóm Facebook."
        )
        note.setProperty("muted", True)
        note.setWordWrap(True)
        content_layout.addWidget(note)
        content_layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

    def set_content(self, caption: str, image_paths: list[Path]) -> None:
        self.caption.setText(caption)
        if image_paths != self._image_paths:
            self._image_paths = list(image_paths)
            self.media_grid.set_images(image_paths)
        count = len(image_paths)
        self.image_count.setText(
            "Chưa có ảnh"
            if count == 0
            else f"{count} ảnh trong bài viết"
        )
