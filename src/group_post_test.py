from pathlib import Path
from tkinter import dialog

from playwright.sync_api import sync_playwright


ROOT_DIR = Path(__file__).resolve().parent.parent

SESSION_DIR = (
    ROOT_DIR
    / "browser_sessions"
    / "accQuan"
)

GROUP_URL = "https://www.facebook.com/groups/1363667009223009"

IMAGE_PATHS = [
    ROOT_DIR / "data" / "test" / "huy.jpg",
    ROOT_DIR / "data" / "test" / "dang.png",
]
def main():
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            headless=True,
        )

        page = (
            context.pages[0]
            if context.pages
            else context.new_page()
        )

        print("[1] Opening group...")

        page.goto(
            GROUP_URL,
            wait_until="domcontentloaded",
        )

        print("URL:", page.url)
        print("Title:", page.title())

        composer = page.get_by_role("button", name="Bạn viết gì đi...")
        composer.click()

        dialog = page.get_by_role(
            "dialog",
            name="Tạo bài viết"
        ).first
        textbox = dialog.get_by_role("textbox")
        textbox.fill("2k8 mới lên HN tìm người thương bao nuôi")


        file_inputs = dialog.locator('input[type="file"]')
        file_inputs.first.set_input_files([str(path) for path in IMAGE_PATHS])

        print("Image uploaded")

        post_button = dialog.get_by_role("button", name="Đăng", exact=True)
        post_button.click()

        print("Waiting for post to finish...")

        dialog.wait_for(
            state="hidden",
            timeout=60_000
        )
        print("Post completed")
        context.close()


if __name__ == "__main__":
    main()