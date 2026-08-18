from __future__ import annotations

from PySide6.QtCore import QObject, QRectF, Qt, Slot
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from gui.main_window import MainWindow


def create_w4_tray_icon() -> QIcon:
    """Create a crisp W4 app mark at the sizes used by desktop trays."""
    icon = QIcon()
    for size in (16, 20, 24, 32, 48, 64, 128, 256):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        inset = max(1.0, size * 0.045)
        bounds = QRectF(inset, inset, size - 2 * inset, size - 2 * inset)
        painter.setPen(
            QPen(QColor("#9B7AE8"), max(1.0, size * 0.025))
        )
        painter.setBrush(QColor("#6D42C6"))
        painter.drawRoundedRect(bounds, size * 0.22, size * 0.22)

        font = QFont("Noto Sans")
        font.setWeight(QFont.Weight.ExtraBold)
        font.setPixelSize(max(7, round(size * 0.39)))
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, -size * 0.025)
        painter.setFont(font)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(
            bounds.adjusted(0, -size * 0.015, 0, 0),
            Qt.AlignmentFlag.AlignCenter,
            "W4",
        )
        painter.end()
        icon.addPixmap(pixmap)
    return icon


class SystemTrayController(QObject):
    """Own the tray icon and keep window visibility behavior in one place."""

    def __init__(
        self,
        application: QApplication,
        window: MainWindow,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent or application)
        self.application = application
        self.window = window
        self.icon = create_w4_tray_icon()
        self.tray_icon = QSystemTrayIcon(self.icon, self)
        self.tray_icon.setToolTip("W4nwy Automation")
        self.context_menu = QMenu(window)
        self.open_action = self.context_menu.addAction(
            "Mở W4nwy Automation"
        )
        self.hide_action = self.context_menu.addAction("Ẩn cửa sổ")
        self.context_menu.addSeparator()
        self.quit_action = self.context_menu.addAction("Thoát")
        self.tray_icon.setContextMenu(self.context_menu)
        self.open_action.triggered.connect(self.show_window)
        self.hide_action.triggered.connect(self.hide_window)
        self.quit_action.triggered.connect(self.quit_application)
        self.context_menu.aboutToShow.connect(self._sync_action_states)
        self.tray_icon.activated.connect(self._on_activated)
        self.window.minimized_to_tray.connect(self._notify_minimized)
        self.application.aboutToQuit.connect(self.tray_icon.hide)
        self._minimized_message_shown = False
        self._started = False

        self.application.setWindowIcon(self.icon)
        self.window.setWindowIcon(self.icon)

    def start(self) -> bool:
        if self._started:
            return True
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return False
        self.application.setQuitOnLastWindowClosed(False)
        self.window.enable_system_tray(True)
        self.tray_icon.show()
        self._started = True
        return True

    @Slot()
    def show_window(self) -> None:
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    @Slot()
    def hide_window(self) -> None:
        self.window.hide()

    @Slot()
    def quit_application(self) -> None:
        if not self.window.request_application_exit():
            return
        self.tray_icon.hide()
        self.application.quit()

    @Slot(QSystemTrayIcon.ActivationReason)
    def _on_activated(
        self,
        reason: QSystemTrayIcon.ActivationReason,
    ) -> None:
        if reason in {
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        }:
            self.show_window()

    @Slot()
    def _sync_action_states(self) -> None:
        visible = self.window.isVisible() and not self.window.isMinimized()
        self.open_action.setEnabled(not visible)
        self.hide_action.setEnabled(visible)

    @Slot()
    def _notify_minimized(self) -> None:
        if self._minimized_message_shown or not self._started:
            return
        self._minimized_message_shown = True
        if QSystemTrayIcon.supportsMessages():
            self.tray_icon.showMessage(
                "W4nwy Automation vẫn đang chạy",
                "Bấm vào biểu tượng W4 để mở lại cửa sổ.",
                QSystemTrayIcon.MessageIcon.Information,
                3500,
            )
