from playwright.sync_api import (
    Page,
    TimeoutError as PlaywrightTimeoutError,
)


def get_group_name(page: Page) -> str:
    heading = page.locator("h1").first

    try:
        heading.wait_for(
            state="visible",
            timeout=10_000,
        )

        return heading.inner_text().strip()

    except PlaywrightTimeoutError:
        return "Unknown Group"