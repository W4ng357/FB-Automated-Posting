import faulthandler
import logging
import sys
import traceback

from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import os
from PySide6.QtCore import QCoreApplication

from app_paths import (
    APP_NAME,
    CURRENT_UPDATE_DIR,
    LOGS_DIR,
    ORG_NAME,
    ensure_app_paths,
    get_resource_path,
    setup_playwright_env,
)

# If an updated code package exists, load modules from it first
if CURRENT_UPDATE_DIR.is_dir():
    update_path_str = str(CURRENT_UPDATE_DIR)
    if update_path_str not in sys.path:
        sys.path.insert(0, update_path_str)

# Discover system Qt6 platform input context plugins (Fcitx5, IBus) on Linux
if sys.platform.startswith("linux"):
    for plugin_dir in (
        "/usr/lib/qt6/plugins",
        "/usr/lib64/qt6/plugins",
        "/usr/lib/x86_64-linux-gnu/qt6/plugins",
        "/usr/lib/qt/plugins",
        "/usr/lib64/qt/plugins",
    ):
        if Path(plugin_dir).is_dir():
            QCoreApplication.addLibraryPath(plugin_dir)

    xmod = os.environ.get("XMODIFIERS", "").lower()
    if "fcitx" in xmod and not os.environ.get("QT_IM_MODULE"):
        os.environ["QT_IM_MODULE"] = "fcitx"
    elif "ibus" in xmod and not os.environ.get("QT_IM_MODULE"):
        os.environ["QT_IM_MODULE"] = "ibus"


def _setup_logging():
    """Configure persistent file logging for startup and uncaught GUI exceptions."""
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        log_file = LOGS_DIR / "app.log"
        logging.basicConfig(
            filename=str(log_file),
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            encoding="utf-8",
        )
        logging.info(f"Starting {APP_NAME}...")
    except Exception as err:
        sys.stderr.write(f"Failed to initialize file logging: {err}\n")


def _enable_native_crash_log():
    """Keep a Python stack trace when Qt or another native module crashes."""
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        crash_log = (LOGS_DIR / "native-crash.log").open(
            "a",
            encoding="utf-8",
            buffering=1,
        )
    except OSError:
        faulthandler.enable(all_threads=True)
        return None
    crash_log.write(f"\n=== Khởi động {APP_NAME} ===\n")
    faulthandler.enable(file=crash_log, all_threads=True)
    return crash_log


def _uncaught_exception_handler(exc_type, exc_value, exc_traceback):
    """Log uncaught exceptions to app.log before default sys.excepthook runs."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.critical(
        "Uncaught exception",
        exc_info=(exc_type, exc_value, exc_traceback),
    )
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


sys.excepthook = _uncaught_exception_handler
_NATIVE_CRASH_LOG = _enable_native_crash_log()
_setup_logging()

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow
from gui.system_tray import SystemTrayController


def load_stylesheet() -> str:
    stylesheet_path = get_resource_path("src/gui/styles/dark.qss")
    if not stylesheet_path.is_file():
        # Fallback if relative structure differs
        stylesheet_path = Path(__file__).resolve().parent / "styles" / "dark.qss"
    return stylesheet_path.read_text(encoding="utf-8")


def create_application(
    arguments: list[str] | None = None,
) -> QApplication:
    ensure_app_paths()
    setup_playwright_env()

    application = QApplication(
        arguments if arguments is not None else sys.argv
    )
    from services.update_service import UpdateService
    active_version = UpdateService().get_current_installed_version()
    application.setApplicationVersion(active_version)
    application.setStyle("Fusion")
    application.setFont(QFont("Noto Sans", 10))
    application.setStyleSheet(load_stylesheet())

    return application


def main() -> int:
    application = create_application()
    window = MainWindow()
    tray_controller = SystemTrayController(application, window)
    tray_controller.start()
    window.show()

    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
