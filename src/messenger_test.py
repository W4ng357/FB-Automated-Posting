from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir="/home/wanwy/Documents/Prj/FB-Automated-Posting/browser_sessions/accQuan",
            headless=True
            )
        if browser.pages:
            page = browser.pages[0]
        else:
            page = browser.new_page()

        page.goto("https://www.facebook.com")

        #input("Press Enter to find the link...")
        
        messenger_button = page.get_by_role(
            "button",
            name="Messenger"
        )

        #print("Link text:", messenger_button.get_attribute("innerHTML"))

        #input("Press Enter to click...")

        messenger_button.click()
        chat_button = page.get_by_role(
            "row",
            name="Tâm Nguyễn"
        )
        chat_button.click()
        #print("Current URL:", page.url)
        type_button = page.get_by_role(
            "textbox",
            name="Viết cho"
        )
        type_button.click()
        input("Press Enter to send message...")
        type_button.press_sequentially("nigger")
        type_button.press("Enter")
        input("Press Enter to close...")

        browser.close()


if __name__ == "__main__":
    main()