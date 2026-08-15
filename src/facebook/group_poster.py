from pathlib import Path

from playwright.sync_api import Page, sync_playwright

from models.group_target import GroupTarget
from services.post_interval import wait_random_minutes, MIN_POST_INTERVAL, MAX_POST_INTERVAL, MIN_ROUND_INTERVAL, MAX_ROUND_INTERVAL
from facebook.get_post_url import get_latest_post_url
def post_to_group(
    page: Page,
    group_url: str,
    caption: str,
    image_paths: list[Path],
) -> str | None:
    print(f"[+] Opening group: {group_url}")

    page.goto(
        group_url,
        wait_until="domcontentloaded",
    )

    composer = page.get_by_role(
        "button",
        name="Bạn viết gì đi..."
    )
    composer.click()

    dialog = page.get_by_role(
        "dialog",
        name="Tạo bài viết"
    ).first

    textbox = dialog.get_by_role("textbox")
    textbox.press_sequentially(caption)

    file_input = dialog.locator(
        'input[type="file"]'
    ).first

    file_input.set_input_files(
        [str(path) for path in image_paths]
    )

    post_button = dialog.get_by_role(
        "button",
        name="Đăng",
        exact=True,
    )

    post_button.click()

    dialog.wait_for(
        state="hidden",
        timeout=60_000,
    )

    print("[✓] Post completed")
    post_url = get_latest_post_url(page)

    if post_url:
        print(f"[✓] Post URL: {post_url}")
    else:
        print("[!] Could not get post URL")

    return post_url
    return post_url


def post_to_groups(
    session_path: Path,
    group_targets: list[GroupTarget],
    caption: str,
    image_paths: list[Path],
) -> None:
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(session_path),
            headless=False,
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
                group.remaining > 0
                for group in group_targets
            ):
                print(f"\n===== ROUND {round_number} =====")

                active_groups = [
                    group
                    for group in group_targets
                    if group.remaining > 0
                ]

                for index, group in enumerate(active_groups):
                    print(
                        f"\n[{group.posted_count + 1}/"
                        f"{group.target_count}] "
                        f"{group.url}"
                    )

                    post_to_group(
                        page=page,
                        group_url=group.url,
                        caption=caption,
                        image_paths=image_paths,
                    )

                    group.mark_posted()

                    print(
                        f"[✓] Group progress: "
                        f"{group.posted_count}/"
                        f"{group.target_count}"
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
                    group.remaining > 0
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