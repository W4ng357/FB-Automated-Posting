import logging
import os
import subprocess
import sys
from pathlib import Path
from playwright.sync_api import BrowserContext, Playwright


def _install_playwright_chromium() -> bool:
    """Attempt to install Playwright Chromium binary in background if missing."""
    try:
        from playwright._impl._driver import compute_driver_executable
        driver_executable, driver_cli = compute_driver_executable()
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        result = subprocess.run(
            [driver_executable, driver_cli, "install", "chromium"],
            check=False,
            creationflags=creationflags,
            capture_output=True,
            text=True,
            timeout=180,
        )
        return result.returncode == 0
    except Exception as e:
        logging.warning(f"Failed to auto-install playwright chromium: {e}")
        return False


def launch_persistent_context(
    playwright: Playwright,
    user_data_dir: Path | str,
    headless: bool = False,
    **kwargs,
) -> BrowserContext:
    """Launch Playwright Chromium with fallback to system Edge/Chrome or auto-install."""
    user_data_dir = str(user_data_dir)

    # 1. Thử mở bằng Chromium mặc định của Playwright
    try:
        return playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=headless,
            **kwargs,
        )
    except Exception as err:
        err_msg = str(err)
        if "Executable doesn't exist" not in err_msg and "Please run the following command" not in err_msg:
            raise

    # 2. Nếu thiếu Chromium, thử mở bằng Microsoft Edge có sẵn trên Windows
    if sys.platform == "win32":
        try:
            return playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=headless,
                channel="msedge",
                **kwargs,
            )
        except Exception:
            pass

        # 3. Thử mở bằng Google Chrome có sẵn trên máy
        try:
            return playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=headless,
                channel="chrome",
                **kwargs,
            )
        except Exception:
            pass

    # 4. Tự động tải Chromium nếu chưa có sẵn trình duyệt nào
    logging.info("Playwright Chromium not found. Attempting auto-installation...")
    if _install_playwright_chromium():
        return playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=headless,
            **kwargs,
        )

    # 5. Lần thử cuối cùng để ném lỗi chi tiết nếu vẫn thất bại
    return playwright.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        headless=headless,
        **kwargs,
    )
