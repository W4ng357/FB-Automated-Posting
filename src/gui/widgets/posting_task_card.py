from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from models.listing_posting_task import ListingPostingTask


class PostingTaskCard(QFrame):
    edit_requested = Signal(str)
    remove_requested = Signal(str)

    def __init__(
        self,
        task: ListingPostingTask,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("taskCard", True)
        root = QHBoxLayout(self)
        root.setContentsMargins(15, 13, 15, 13)
        root.setSpacing(14)
        content = QVBoxLayout()
        content.setSpacing(4)
        title = QLabel(task.listing_title)
        title.setObjectName("CardTitle")
        details = QLabel(
            f"{task.listing_id} · {len(task.group_targets)} nhóm · "
            f"{task.total_attempts} lượt dự kiến"
        )
        details.setProperty("muted", True)
        group_names = [
            task.group_names.get(target.url, target.url)
            for target in task.group_targets
        ]
        group_summary = QLabel(
            "Chưa chọn nhóm"
            if not group_names
            else group_names[0]
            + (f" và {len(group_names) - 1} nhóm khác" if len(group_names) > 1 else "")
        )
        group_summary.setProperty("meta", True)
        group_summary.setWordWrap(True)
        content.addWidget(title)
        content.addWidget(details)
        content.addWidget(group_summary)
        root.addLayout(content, 1)
        edit_button = QPushButton("Chọn nhóm")
        edit_button.setProperty("density", "compact")
        edit_button.clicked.connect(
            lambda: self.edit_requested.emit(task.listing_id)
        )
        remove_button = QPushButton("Gỡ")
        remove_button.setProperty("role", "ghostDanger")
        remove_button.setProperty("density", "compact")
        remove_button.clicked.connect(
            lambda: self.remove_requested.emit(task.listing_id)
        )
        root.addWidget(edit_button)
        root.addWidget(remove_button)
