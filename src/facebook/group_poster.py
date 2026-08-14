from pathlib import Path

from playwright.sync_api import Page, sync_playwright



def post_to_a_group(
    page: Page,
    group_url: str,
    caption: str,
    image_paths: list[Path],
) -> None:
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
    textbox.fill(caption)

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

def post_to_groups(
    session_path: Path,
    group_urls: list[str],
    caption: str,
    image_paths: list[Path],
) -> None:
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(session_path),
            headless=True,
        )

        try:
            page = (
                context.pages[0]
                if context.pages
                else context.new_page()
            )

            for group_url in group_urls:
                post_to_a_group(
                    page=page,
                    group_url=group_url,
                    caption=caption,
                    image_paths=image_paths,
                )

        finally:
            context.close()