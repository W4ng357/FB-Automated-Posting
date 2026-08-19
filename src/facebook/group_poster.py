from pathlib import Path

from playwright.sync_api import Page, sync_playwright

from facebook.browser_launcher import launch_persistent_context as launch_browser_context
from facebook.get_group_name import get_group_name
from models.group_target import GroupTarget
from models.post_result import PostResult
from services.post_interval import wait_random_minutes, MIN_POST_INTERVAL, MAX_POST_INTERVAL, MIN_ROUND_INTERVAL, MAX_ROUND_INTERVAL
from facebook.get_post_url import get_latest_post_url
def post_to_group(
    page: Page,
    group_url: str,
    caption: str,
    image_paths: list[Path],
) -> PostResult:
    group_name = None
    try:
        page.goto(
            group_url,
            wait_until="domcontentloaded",
        )
        if hasattr(page, "wait_for_timeout"):
            page.wait_for_timeout(1_500)

        group_name = get_group_name(page)
        print(f"[+] Group name: {group_name}")

        # 1. Click mở khung soạn thảo
        composer = page.get_by_role(
            "button",
            name="Bạn viết gì đi...",
        )
        try:
            if hasattr(composer, "count") and composer.count():
                composer.click()
            else:
                _find_and_click_composer(page)
        except Exception:
            _find_and_click_composer(page)

        if hasattr(page, "wait_for_timeout"):
            page.wait_for_timeout(1_000)

        # 2. Tìm Dialog tạo bài viết
        dialog = _find_composer_dialog(page)

        # 3. Nhập Caption
        textbox = _find_composer_textbox(dialog)
        textbox.press_sequentially(caption)

        # 4. Upload ảnh nếu có
        if image_paths:
            file_input = dialog.locator('input[type="file"]').first
            file_input.set_input_files(
                [str(path) for path in image_paths]
            )
            if hasattr(page, "wait_for_timeout"):
                page.wait_for_timeout(2_000)

        # 5. Bấm nút Đăng
        post_button = _find_post_button(dialog)
        post_button.click()

        dialog.wait_for(
            state="hidden",
            timeout=60_000,
        )

        print("[✓] Post completed")

        # Lấy URL là bước phụ.
        # Fail bước này không có nghĩa post fail.
        try:
            post_url = get_latest_post_url(page)
        except Exception as error:
            print(
                f"[!] Post succeeded but "
                f"could not get URL: {error}"
            )
            post_url = None

        return PostResult(
            group_url=group_url,
            group_name=group_name,
            success=True,
            post_url=post_url,
        )

    except Exception as error:
        return PostResult(
            group_url=group_url,
            group_name=group_name,
            success=False,
            error=str(error),
        )


def _find_and_click_composer(page: Page) -> None:
    selectors = (
        'div[role="main"] div[role="button"]:has-text("Bạn viết gì đi")',
        'div[role="main"] div[role="button"]:has-text("Tạo bài viết")',
        'div[role="main"] div[role="button"]:has-text("Viết gì đó")',
        'div[role="main"] div[role="button"]:has-text("Write something")',
        'div[role="main"] div[role="button"]:has-text("Create a public post")',
        'div[role="main"] div[role="button"]:has-text("Bạn đang nghĩ gì")',
        '[role="button"]:has-text("Bạn viết gì đi")',
        '[role="button"]:has-text("Tạo bài viết")',
        '[role="button"]:has-text("Write something")',
    )
    for selector in selectors:
        try:
            btn = page.locator(selector).first
            if hasattr(btn, "count") and btn.count():
                btn.click()
                return
        except Exception:
            continue
    page.get_by_role("button", name="Bạn viết gì đi...").click()


def _find_composer_dialog(page: Page):
    try:
        dialog = page.get_by_role("dialog", name="Tạo bài viết").first
        if hasattr(dialog, "wait_for"):
            dialog.wait_for(state="visible", timeout=4_000)
            return dialog
    except Exception:
        pass

    for selector in (
        '[role="dialog"]:visible',
        '[aria-label*="Tạo bài viết" i]',
        '[aria-label*="Create a post" i]',
        '[aria-label*="Create post" i]',
        '[role="dialog"]',
    ):
        try:
            dialog = page.locator(selector).first
            if hasattr(dialog, "count") and dialog.count():
                return dialog
        except Exception:
            continue

    return page.get_by_role("dialog", name="Tạo bài viết").first


def _find_composer_textbox(dialog):
    for selector in (
        '[role="textbox"]:visible',
        '[contenteditable="true"]:visible',
        '[role="textbox"]',
        '[contenteditable="true"]',
    ):
        try:
            tb = dialog.locator(selector).first
            if hasattr(tb, "count") and tb.count():
                return tb
        except Exception:
            continue
    return dialog.get_by_role("textbox")


def _find_post_button(dialog):
    for selector in (
        '[role="button"]:has-text("Đăng"):visible',
        '[role="button"]:has-text("Post"):visible',
        '[role="button"]:has-text("Đăng")',
        '[role="button"]:has-text("Post")',
    ):
        try:
            btn = dialog.locator(selector).first
            if hasattr(btn, "count") and btn.count():
                return btn
        except Exception:
            continue
    return dialog.get_by_role("button", name="Đăng", exact=True)


def post_to_groups(
    session_path: Path,
    group_targets: list[GroupTarget],
    caption: str,
    image_paths: list[Path],
) -> list[PostResult]:
    results: list[PostResult] = []
    with sync_playwright() as p:
        context = launch_browser_context(
            p,
            user_data_dir=session_path,
            headless=True,
        )
        context.grant_permissions(
            ["clipboard-read", "clipboard-write"],
            origin="https://www.facebook.com",
        )
        try:
            page = (
                context.pages[0]
                if context.pages
                else context.new_page()
            )

            round_number = 1

            while any(
                group.active
                for group in group_targets
            ):
                print(f"\n===== ROUND {round_number} =====")

                active_groups = [
                    group
                    for group in group_targets
                    if group.active
                ]

                for index, group in enumerate(active_groups):
                    print(
                        f"\n[{group.posted_count + 1}/"
                        f"{group.target_count}] "
                        f"{group.url}"
                    )

                    result = post_to_group(
                    page=page,
                    group_url=group.url,
                    caption=caption,
                    image_paths=image_paths,
                    )
                    results.append(result)
                    if result.success:
                        group.mark_posted()

                        print(
                            f"[✓] Group progress: "
                            f"{group.posted_count}/"
                            f"{group.target_count}"
                        )

                        if result.post_url:
                            print(f"[✓] URL: {result.post_url}")
                        else:
                            print("[!] URL unavailable")

                    else:
                        group.mark_failed()

                        print(f"[✗] Post failed: {result.error}")
                        print(
                            f"[!] Group disabled for this run "
                            f"({group.posted_count}/{group.target_count})"
                        )

                    # Chỉ chờ ngắn nếu còn group khác
                    # trong cùng round hiện tại
                    if index < len(active_groups) - 1:
                        wait_random_minutes(
                            MIN_POST_INTERVAL,
                            MAX_POST_INTERVAL,
                            "Waiting before next group",
                        )

                # Kiểm tra sau khi hoàn thành cả round
                if any(
                    group.active
                    for group in group_targets
                ):
                    wait_random_minutes(
                        MIN_ROUND_INTERVAL,
                        MAX_ROUND_INTERVAL,
                        "Round completed. Waiting before next round",
                    )

                round_number += 1

        finally:
            context.close()
    return results
