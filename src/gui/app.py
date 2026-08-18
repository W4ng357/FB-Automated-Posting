import faulthandler
import sys

from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = SRC_DIR.parent


def _enable_native_crash_log():
    """Keep a Python stack trace when Qt or another native module crashes."""
    try:
        log_dir = PROJECT_DIR / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        crash_log = (log_dir / "native-crash.log").open(
            "a",
            encoding="utf-8",
            buffering=1,
        )
    except OSError:
        faulthandler.enable(all_threads=True)
        return None
    crash_log.write("\n=== Khởi động FB Poster ===\n")
    faulthandler.enable(file=crash_log, all_threads=True)
    return crash_log


_NATIVE_CRASH_LOG = _enable_native_crash_log()

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow


def load_stylesheet() -> str:
    stylesheet_path = (
        Path(__file__).resolve().parent
        / "styles"
        / "dark.qss"
    )

    return stylesheet_path.read_text(encoding="utf-8")


def create_application(
    arguments: list[str] | None = None,
) -> QApplication:
    application = QApplication(
        arguments if arguments is not None else sys.argv
    )
    application.setApplicationName("FB Poster")
    application.setStyle("Fusion")
    application.setFont(QFont("Noto Sans", 10))
    application.setStyleSheet(load_stylesheet())

    return application


def main() -> int:
    application = create_application()
    window = MainWindow()
    window.show()

    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
