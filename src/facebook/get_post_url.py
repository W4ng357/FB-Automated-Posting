from playwright.sync_api import (
    Page,
    TimeoutError as PlaywrightTimeoutError,
)


def get_latest_post_url(page: Page) -> str | None:
    try:
        # Xóa clipboard cũ để tránh đọc nhầm
        page.evaluate(
            "navigator.clipboard.writeText('')"
        )

        share_button = page.get_by_role(
            "button",
            name="Gửi nội dung này cho bạn bè",
        ).first

        share_button.click()

        copy_link_button = page.get_by_role(
            "button",
            name="Sao chép liên kết",
        )

        copy_link_button.click()

        page.wait_for_function(
            """
            async () => {
                const text = await navigator.clipboard.readText();
                return text.length > 0;
            }
            """,
            timeout=5_000,
        )

        post_url = page.evaluate(
            "navigator.clipboard.readText()"
        )

        return post_url.strip() if post_url else None

    except PlaywrightTimeoutError:
        return None