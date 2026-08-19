import json
import logging
import re
import sys

from dataclasses import dataclass
from pathlib import Path
from threading import Event
from time import monotonic
from typing import Callable
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from playwright.sync_api import (
    BrowserContext,
    Error as PlaywrightError,
    Page,
    sync_playwright,
)

from models.facebook_account import normalize_facebook_name
from services.account_session_registry import AccountSessionRegistry


class FacebookProfileNotReadyError(RuntimeError):
    pass


LOGGER = logging.getLogger(__name__)
WINDOWS_FACEBOOK_ARGS = (
    "--disable-blink-features=AutomationControlled",
    "--disable-dev-shm-usage",
    "--no-first-run",
    "--no-default-browser-check",
)


@dataclass(frozen=True)
class FacebookProfileMetadata:
    name: str
    profile_url: str
    avatar_data: bytes | None = None
    avatar_extension: str | None = None


def extract_facebook_profile(
    page: Page,
    context: BrowserContext,
) -> FacebookProfileMetadata:
    page.goto(
        "https://www.facebook.com/me",
        wait_until="domcontentloaded",
        timeout=45_000,
    )
    page.wait_for_timeout(500)

    current_url = page.url.lower()
    if any(
        marker in current_url
        for marker in ("/login", "/checkpoint", "/recover")
    ):
        raise FacebookProfileNotReadyError(
            "Facebook chưa xác nhận đăng nhập. Hoàn tất bước xác minh rồi thử lại."
        )

    name = _wait_for_profile_name(page)
    if not name:
        raise FacebookProfileNotReadyError(
            "Chưa lấy được tên tài khoản. Hãy mở trang cá nhân trong cửa sổ "
            "Facebook, rồi thử lại."
        )

    avatar_data, avatar_extension = _wait_for_visible_avatar(page)
    if avatar_data is None:
        avatar_url = _read_meta(page, "og:image")
        if avatar_url:
            avatar_data, avatar_extension = _download_avatar(
                context,
                avatar_url,
            )
    if avatar_data is None:
        raise FacebookProfileNotReadyError(
            "Đã đọc được tên nhưng chưa thấy ảnh đại diện. "
            "Chờ trang cá nhân tải xong rồi thử lấy thông tin lại."
        )

    return FacebookProfileMetadata(
        name=name,
        profile_url=_clean_profile_url(page.url),
        avatar_data=avatar_data,
        avatar_extension=avatar_extension,
    )


def run_account_login_session(
    account_id: str,
    session_path: Path,
    capture_requested: Event,
    cancel_requested: Event,
    status_callback: Callable[[str], None],
) -> FacebookProfileMetadata | None:
    session_path.mkdir(parents=True, exist_ok=True)
    with AccountSessionRegistry.exclusive(account_id, session_path):
        with sync_playwright() as playwright:
            context = _launch_login_context(playwright, session_path)
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(
                    "https://www.facebook.com",
                    wait_until="domcontentloaded",
                    timeout=60_000,
                )
                status_callback(
                    "Đăng nhập Facebook trong cửa sổ vừa mở, rồi quay lại "
                    "ứng dụng để lấy thông tin tài khoản."
                )
                while not cancel_requested.is_set():
                    if not capture_requested.wait(0.2):
                        continue
                    capture_requested.clear()
                    try:
                        active_page = context.pages[-1] if context.pages else page
                        return extract_facebook_profile(active_page, context)
                    except FacebookProfileNotReadyError as error:
                        status_callback(str(error))
                return None
            finally:
                context.close()


def _launch_login_context(playwright, session_path: Path) -> BrowserContext:
    launch_options = {
        "user_data_dir": str(session_path),
        "headless": False,
    }
    if sys.platform != "win32":
        return playwright.chromium.launch_persistent_context(**launch_options)

    windows_options = {
        **launch_options,
        "args": list(WINDOWS_FACEBOOK_ARGS),
        "ignore_default_args": ["--enable-automation"],
        "locale": "en-US",
    }
    try:
        return playwright.chromium.launch_persistent_context(
            channel="chrome",
            **windows_options,
        )
    except PlaywrightError as error:
        LOGGER.warning(
            "Không mở được Chrome channel, fallback về Chromium mặc định.",
            exc_info=error,
        )
        return playwright.chromium.launch_persistent_context(
            **windows_options,
        )


def _read_meta(page: Page, property_name: str) -> str:
    locator = page.locator(
        f'meta[property="{property_name}"]'
    ).first
    if locator.count() == 0:
        return ""
    return (locator.get_attribute("content", timeout=1_500) or "").strip()


def _read_profile_heading(page: Page) -> str:
    for selector in (
        '[role="main"] h1:visible',
        '[role="main"] [role="heading"][aria-level="1"]:visible',
        "main h1:visible",
        "h1:visible",
        '[role="heading"][aria-level="1"]:visible',
        '[role="main"] h1',
        "h1",
    ):
        try:
            heading = page.locator(selector).first
            if heading.count():
                value = (
                    heading.inner_text(timeout=3_000)
                    or heading.text_content(timeout=1_000)
                    or ""
                ).strip()
                if value:
                    return value
        except Exception:
            continue
    return ""


def _wait_for_profile_name(page: Page, timeout_ms: int = 15_000) -> str:
    deadline = monotonic() + timeout_ms / 1_000
    while monotonic() < deadline:
        readers = (
            lambda: _read_profile_heading(page),
            lambda: _read_name_from_profile_button(page),
            lambda: _read_name_from_avatar_label(page),
            lambda: _read_meta(page, "og:title"),
            page.title,
        )
        for reader in readers:
            try:
                candidate = reader()
            except Exception:
                continue
            name = normalize_facebook_name(candidate)
            if name:
                return name
        page.wait_for_timeout(500)
    return ""


def _read_name_from_profile_button(page: Page) -> str:
    button_groups = []
    try:
        main = page.get_by_role("main").first
        if main.count():
            button_groups.append(main.get_by_role("button"))
    except Exception:
        pass

    try:
        button_groups.append(page.get_by_role("button"))
    except Exception:
        pass

    for buttons in button_groups:
        name = _read_name_from_buttons(buttons)
        if name:
            return name
    return ""


def _read_name_from_buttons(buttons) -> str:
    try:
        button_count = min(buttons.count(), 80)
    except Exception:
        return ""

    text_candidates: list[str] = []
    aria_candidates: list[str] = []
    for index in range(button_count):
        button = buttons.nth(index)
        try:
            visible_text = normalize_facebook_name(
                button.inner_text(timeout=500)
            )
        except Exception:
            visible_text = ""
        if (
            visible_text
            and not _is_profile_action_name(visible_text)
            and _looks_like_person_name(visible_text)
        ):
            text_candidates.append(visible_text)

        try:
            snapshot = button.aria_snapshot(
                depth=0,
                timeout=700,
            )
        except Exception:
            continue
        name = normalize_facebook_name(
            _button_name_from_aria_snapshot(snapshot)
        )
        if not name or _is_profile_action_name(name):
            continue
        if _looks_like_person_name(name):
            aria_candidates.append(name)
    candidates = text_candidates or aria_candidates
    return candidates[0] if candidates else ""


def _button_name_from_aria_snapshot(snapshot: str) -> str:
    match = re.search(
        r'^\s*-\s*button\s+"((?:[^"\\]|\\.)*)"',
        snapshot,
        flags=re.MULTILINE,
    )
    if not match:
        return ""
    try:
        return json.loads(f'"{match.group(1)}"')
    except json.JSONDecodeError:
        return match.group(1)


def _is_profile_action_name(value: str) -> bool:
    lowered = value.casefold()
    blocked_fragments = (
        "ảnh đại diện",
        "profile picture",
        "hành động với",
        "actions",
        "tài khoản",
        "account",
        "trang cá nhân của bạn",
        "your profile",
        "menu",
        "chỉnh sửa",
        "edit",
        "thêm ",
        "add ",
        "tìm kiếm",
        "search",
        "messenger",
        "nhắn tin",
        "message",
        "chia sẻ",
        "share",
        "bình luận",
        "comment",
        "thích",
        "like",
    )
    return any(fragment in lowered for fragment in blocked_fragments)


def _looks_like_person_name(value: str) -> bool:
    words = re.findall(r"[^\W\d_]+", value, flags=re.UNICODE)
    if not 2 <= len(words) <= 6:
        return False
    uppercase_words = sum(word[:1].isupper() for word in words)
    return uppercase_words >= 2


def _read_name_from_avatar_label(page: Page) -> str:
    selectors = (
        '[aria-label*="Ảnh đại diện" i]',
        '[aria-label*="profile picture" i]',
        'img[alt*="ảnh đại diện" i]',
        'img[alt*="profile picture" i]',
    )
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if not locator.count():
                continue
            label = (
                locator.get_attribute("aria-label", timeout=700)
                or locator.get_attribute("alt", timeout=700)
                or ""
            ).strip()
        except Exception:
            continue
        name = _name_from_avatar_label(label)
        if name:
            return name
    return ""


def _name_from_avatar_label(label: str) -> str:
    patterns = (
        r"^Ảnh đại diện của\s+(.+)$",
        r"^(.+?),?\s*ảnh đại diện$",
        r"^Profile picture of\s+(.+)$",
        r"^(.+?)(?:'s)?\s+profile picture$",
    )
    for pattern in patterns:
        match = re.match(pattern, label.strip(), flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def _clean_profile_url(url: str) -> str:
    parts = urlsplit(url)
    query = ""
    if parts.path.rstrip("/").endswith("profile.php"):
        profile_id = parse_qs(parts.query).get("id", [])
        if profile_id:
            query = urlencode({"id": profile_id[0]})
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))


def _download_avatar(
    context: BrowserContext,
    avatar_url: str,
) -> tuple[bytes | None, str | None]:
    try:
        response = context.request.get(avatar_url, timeout=10_000)
        if not response.ok:
            return None, None
        content_type = response.headers.get("content-type", "").lower()
        extension = {
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
        }.get(content_type.split(";", 1)[0].strip())
        if extension is None:
            return None, None
        image_data = response.body()
        return (image_data, extension) if image_data else (None, None)
    except Exception:
        return None, None


def _capture_visible_avatar(page: Page) -> tuple[bytes | None, str | None]:
    selectors = (
        'a[aria-label*="Ảnh đại diện" i] img',
        'a[aria-label*="Ảnh đại diện" i] image',
        'a[aria-label*="profile picture" i] img',
        'a[aria-label*="profile picture" i] image',
        '[aria-label*="Ảnh đại diện" i] img',
        '[aria-label*="Ảnh đại diện" i] image',
        '[aria-label*="profile picture" i] img',
        '[aria-label*="profile picture" i] image',
        'img[alt*="ảnh đại diện" i]',
        'img[alt*="profile picture" i]',
    )
    for selector in selectors:
        try:
            locator = page.locator(selector).first
        except Exception:
            continue
        image_data = _screenshot_visible(locator)
        if image_data:
            return image_data, ".png"

    for accessible_name in ("Ảnh đại diện", "Profile picture"):
        try:
            link = page.get_by_role(
                "link",
                name=accessible_name,
                exact=False,
            ).first
        except Exception:
            continue
        for descendant in ("img", "image"):
            image_data = _screenshot_visible(
                link.locator(descendant).first
            )
            if image_data:
                return image_data, ".png"
        image_data = _screenshot_visible(link)
        if image_data:
            return image_data, ".png"

    for accessible_name in (
        "Hành động với ảnh đại diện",
        "Profile picture actions",
    ):
        try:
            button = page.get_by_role(
                "button",
                name=accessible_name,
                exact=False,
            ).first
        except Exception:
            continue
        for descendant in ("img", "svg image", "image"):
            image_data = _screenshot_visible(
                button.locator(descendant).first
            )
            if image_data:
                return image_data, ".png"
        image_data = _screenshot_visible(button)
        if image_data:
            return image_data, ".png"
    return None, None


def _wait_for_visible_avatar(
    page: Page,
    timeout_ms: int = 8_000,
) -> tuple[bytes | None, str | None]:
    deadline = monotonic() + timeout_ms / 1_000
    while monotonic() < deadline:
        avatar = _capture_visible_avatar(page)
        if avatar[0]:
            return avatar
        page.wait_for_timeout(500)
    return None, None


def _screenshot_visible(locator) -> bytes | None:
    try:
        if locator.count() and locator.is_visible(timeout=1_200):
            return locator.screenshot(type="png")
    except Exception:
        return None
    return None
