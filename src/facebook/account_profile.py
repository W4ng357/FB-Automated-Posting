import json
import re

from dataclasses import dataclass
from pathlib import Path
from threading import Event
from time import monotonic
from typing import Callable
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from playwright.sync_api import BrowserContext, Page, sync_playwright

from facebook.browser_launcher import launch_persistent_context as launch_browser_context
from models.facebook_account import normalize_facebook_name
from services.account_session_registry import AccountSessionRegistry


class FacebookProfileNotReadyError(RuntimeError):
    pass


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
        timeout=30_000,
    )
    # Chờ Facebook điều hướng từ /me sang trang cá nhân thực tế
    deadline = monotonic() + 4.0
    while monotonic() < deadline:
        cur = page.url.lower().rstrip("/")
        if not cur.endswith("/me") and not cur.endswith("facebook.com") and not cur.endswith("facebook.com/"):
            break
        page.wait_for_timeout(200)

    current_url = page.url.lower()
    if any(
        marker in current_url
        for marker in ("/login", "/checkpoint", "/recover")
    ):
        raise FacebookProfileNotReadyError(
            "Facebook chưa xác nhận đăng nhập. Hoàn tất bước xác minh rồi thử lại."
        )

    # 1. Trích xuất chính xác Tên và Avatar CDN qua JavaScript DOM
    js_data = _extract_profile_data_js(page)
    name = js_data.get("name") or _wait_for_profile_name(page)
    if not name:
        raise FacebookProfileNotReadyError(
            "Chưa lấy được tên tài khoản. Hãy mở trang cá nhân trong cửa sổ "
            "Facebook, rồi thử lại."
        )

    # 2. Tải ảnh đại diện gốc (scontent) từ URL
    avatar_data, avatar_extension = None, None
    avatar_url = js_data.get("avatarUrl") or _find_avatar_url_from_dom(page)
    if not avatar_url:
        og_img = _read_meta(page, "og:image")
        if og_img and "rsrc.php" not in og_img and "silhouette" not in og_img:
            avatar_url = og_img

    if avatar_url:
        avatar_data, avatar_extension = _download_avatar(
            context,
            avatar_url,
        )

    # 3. Fallback: Nếu không tải được qua URL thì chụp phần tử avatar
    if avatar_data is None:
        avatar_data, avatar_extension = _wait_for_visible_avatar(page, timeout_ms=2_500)

    if avatar_data is None:
        raise FacebookProfileNotReadyError(
            "Đã đọc được tên nhưng chưa thấy ảnh đại diện. "
            "Chờ trang cá nhân tải xong rồi thử lấy thông tin lại."
        )

    return FacebookProfileMetadata(
        name=name,
        profile_url=_clean_profile_url(js_data.get("profileUrl") or page.url),
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
            context = launch_browser_context(
                playwright,
                user_data_dir=session_path,
                headless=False,
            )
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.goto("https://www.facebook.com")
                status_callback(
                    "Đăng nhập Facebook trong cửa sổ vừa mở, rồi quay lại "
                    "ứng dụng để lấy thông tin tài khoản."
                )
                while not cancel_requested.is_set():
                    if capture_requested.is_set():
                        capture_requested.clear()
                        try:
                            active_page = context.pages[-1] if context.pages else page
                            return extract_facebook_profile(active_page, context)
                        except FacebookProfileNotReadyError as error:
                            status_callback(str(error))
                    try:
                        page.wait_for_timeout(200)
                    except Exception:
                        break
                return None
            finally:
                context.close()


def _extract_profile_data_js(page: Page) -> dict[str, str]:
    try:
        return page.evaluate("""() => {
            let name = "";
            let avatarUrl = "";
            let profileUrl = "";

            const isInvalidName = (str) => {
                if (!str || str.length < 2 || str.length > 50 || str.includes('\\n')) return true;
                const lower = str.toLowerCase();
                const blocked = [
                    'sống ở', 'đến từ', 'từ ', 'lives in', 'from ', 'làm việc', 'works at',
                    'học tại', 'studied at', 'từng học', 'kết hôn', 'married', 'hẹn hò',
                    'theo dõi', 'followers', 'bạn bè', 'friends', 'tham gia', 'joined',
                    'bài viết', 'posts', 'giới thiệu', 'about', 'ảnh', 'photos', 'video',
                    'trang cá nhân', 'tài khoản', 'chỉnh sửa', 'facebook', 'menu', 'tìm kiếm'
                ];
                return blocked.some(b => lower.includes(b));
            };

            // 1. Lấy tên từ H1 trong ProfileHeader
            const h1Elements = document.querySelectorAll('div[data-pagelet="ProfileHeader"] h1, [role="main"] h1, main h1, h1');
            for (const h1 of h1Elements) {
                const text = (h1.innerText || h1.textContent || "").trim();
                if (!isInvalidName(text)) {
                    name = text;
                    break;
                }
            }

            // 2. Lấy tên & avatar từ LeftRail nếu có
            const navLinks = document.querySelectorAll('div[data-pagelet="LeftRail"] a, div[role="navigation"] a');
            for (const link of navLinks) {
                const href = link.getAttribute('href') || '';
                const textEl = link.querySelector('span');
                const text = (textEl ? textEl.innerText : link.innerText || '').trim();
                const img = link.querySelector('image, img');
                const src = img ? (img.getAttribute('xlink:href') || img.getAttribute('href') || img.src || '') : '';

                if (!name && !isInvalidName(text) && text.length >= 2) {
                    name = text;
                    if (href) profileUrl = href;
                }
                if (!avatarUrl && src && src.includes('scontent') && !src.includes('rsrc.php') && !src.includes('silhouette')) {
                    avatarUrl = src;
                }
            }

            // 3. Tìm Avatar trong ProfileHeader
            if (!avatarUrl) {
                const avatarSelectors = [
                    'div[data-pagelet="ProfileHeader"] svg image',
                    'div[data-pagelet="ProfileHeader"] img',
                    'svg[aria-label*="ảnh đại diện" i] image',
                    'svg[aria-label*="profile picture" i] image',
                    'div[aria-label*="ảnh đại diện" i] image',
                    'div[aria-label*="profile picture" i] image',
                    'div[aria-label*="hành động với ảnh đại diện" i] image',
                    '[role="main"] svg image',
                    'svg image',
                    'img[alt*="ảnh đại diện" i]',
                    'img[alt*="profile picture" i]'
                ];
                for (const sel of avatarSelectors) {
                    const elements = document.querySelectorAll(sel);
                    for (const el of elements) {
                        const src = el.getAttribute('xlink:href') || el.getAttribute('href') || el.src || '';
                        if (src && src.includes('scontent') && !src.includes('rsrc.php') && !src.includes('silhouette')) {
                            avatarUrl = src;
                            break;
                        }
                    }
                    if (avatarUrl) break;
                }
            }

            // 4. Nếu chưa có tên, lấy từ document.title
            if (!name) {
                let docTitle = (document.title || '').replace(/^\\(\\d+\\)\\s*/, '').replace(/\\s*\\|\\s*Facebook.*$/i, '').trim();
                if (!isInvalidName(docTitle)) {
                    name = docTitle;
                }
            }

            return {
                name: name,
                avatarUrl: avatarUrl,
                profileUrl: profileUrl
            };
        }""")
    except Exception:
        return {}


def _find_avatar_url_from_dom(page: Page) -> str:
    try:
        return page.evaluate("""() => {
            const avatarSelectors = [
                'svg[aria-label*="ảnh đại diện" i] image',
                'svg[aria-label*="profile picture" i] image',
                'div[aria-label*="ảnh đại diện" i] image',
                'div[aria-label*="profile picture" i] image',
                'a[aria-label*="ảnh đại diện" i] image',
                'a[aria-label*="profile picture" i] image',
                '[role="main"] svg image',
                'main svg image',
                'svg image',
                'a[aria-label*="ảnh đại diện" i] img',
                'a[aria-label*="profile picture" i] img',
                'div[aria-label*="ảnh đại diện" i] img',
                'div[aria-label*="profile picture" i] img',
                'img[alt*="ảnh đại diện" i]',
                'img[alt*="profile picture" i]'
            ];
            for (const sel of avatarSelectors) {
                const elements = document.querySelectorAll(sel);
                for (const el of elements) {
                    const src = el.getAttribute('xlink:href') || el.getAttribute('href') || el.src || '';
                    if (src && src.includes('scontent') && !src.includes('rsrc.php') && !src.includes('silhouette')) {
                        return src;
                    }
                }
            }
            return '';
        }""")
    except Exception:
        return ""


def _read_meta(page: Page, property_name: str) -> str:
    locator = page.locator(
        f'meta[property="{property_name}"]'
    ).first
    if locator.count() == 0:
        return ""
    return (locator.get_attribute("content", timeout=1_500) or "").strip()


def _name_from_title(page: Page) -> str:
    try:
        raw_title = page.title() or ""
        clean = re.sub(r"^\(\d+\)\s*", "", raw_title)
        clean = re.sub(r"\s*\|\s*Facebook.*$", "", clean, flags=re.IGNORECASE).strip()
        if (
            clean
            and clean.casefold() != "facebook"
            and not _is_profile_action_name(clean)
            and _looks_like_person_name(clean)
        ):
            return clean
    except Exception:
        pass
    return ""


def _read_profile_heading(page: Page) -> str:
    for selector in (
        '[role="main"] h1:visible',
        "main h1:visible",
        '[role="main"] h1',
        "h1:visible",
        "h1",
    ):
        try:
            heading = page.locator(selector).first
            if heading.count():
                value = (
                    heading.inner_text(timeout=1_500)
                    or heading.text_content(timeout=1_000)
                    or ""
                ).strip()
                if value and not _is_profile_action_name(value) and _looks_like_person_name(value):
                    return value
        except Exception:
            continue
    return ""


def _wait_for_profile_name(page: Page, timeout_ms: int = 6_000) -> str:
    deadline = monotonic() + timeout_ms / 1_000
    while monotonic() < deadline:
        readers = (
            lambda: _name_from_title(page),
            lambda: _read_profile_heading(page),
            lambda: _read_meta(page, "og:title"),
            lambda: _read_name_from_avatar_label(page),
            lambda: _read_name_from_profile_button(page),
        )
        for reader in readers:
            try:
                candidate = reader()
            except Exception:
                continue
            name = normalize_facebook_name(candidate)
            if name and not _is_profile_action_name(name):
                return name
        page.wait_for_timeout(150)
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
        button_count = min(buttons.count(), 30)
    except Exception:
        return ""

    text_candidates: list[str] = []
    aria_candidates: list[str] = []
    for index in range(button_count):
        button = buttons.nth(index)
        try:
            visible_text = normalize_facebook_name(
                button.inner_text(timeout=200)
            )
        except Exception:
            visible_text = ""
        if (
            visible_text
            and not _is_profile_action_name(visible_text)
            and _looks_like_person_name(visible_text)
        ):
            text_candidates.append(visible_text)
            return visible_text

        try:
            snapshot = button.aria_snapshot(
                depth=0,
                timeout=250,
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
            return name
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
        "sống ở",
        "lives in",
        "đến từ",
        "từ ",
        "from ",
        "làm việc tại",
        "works at",
        "học tại",
        "studied at",
        "từng học",
        "đã kết hôn",
        "married",
        "hẹn hò",
        "theo dõi",
        "followers",
        "bạn bè",
        "friends",
        "tham gia",
        "joined",
        "bài viết",
        "posts",
        "giới thiệu",
        "about",
        "ảnh",
        "photos",
        "video",
        "videos",
        "reels",
        "quản trị viên",
        "admin",
        "thành viên",
        "facebook",
    )
    return any(fragment in lowered for fragment in blocked_fragments)


def _looks_like_person_name(value: str) -> bool:
    if not value or len(value.strip()) < 2 or len(value.strip()) > 60:
        return False
    words = re.findall(r"[^\W\d_]+", value, flags=re.UNICODE)
    if not 1 <= len(words) <= 8:
        return False
    uppercase_words = sum(word[:1].isupper() for word in words)
    return uppercase_words >= 1


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
    timeout_ms: int = 3_000,
) -> tuple[bytes | None, str | None]:
    deadline = monotonic() + timeout_ms / 1_000
    while monotonic() < deadline:
        avatar = _capture_visible_avatar(page)
        if avatar[0]:
            return avatar
        page.wait_for_timeout(200)
    return None, None


def _screenshot_visible(locator) -> bytes | None:
    try:
        if locator.count() and locator.is_visible(timeout=400):
            return locator.screenshot(type="png")
    except Exception:
        return None
    return None
