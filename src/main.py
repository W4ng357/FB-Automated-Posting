import sys

from playwright.sync_api import sync_playwright

from session_manager import (
    get_session_path,
    list_sessions,
)
from services.account_session_registry import AccountSessionRegistry


def open_account(account_name: str):
    session_dir = get_session_path(account_name)

    session_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    with AccountSessionRegistry.exclusive(account_name, session_dir):
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(session_dir),
                headless=False,
            )

            if context.pages:
                page = context.pages[0]
            else:
                page = context.new_page()

            page.goto("https://www.facebook.com")

            print(f"Opened account session: {account_name}")
            page.pause()
            input("Press Enter to close...")

            context.close()


def show_accounts():
    sessions = list_sessions()

    if not sessions:
    # Nếu list sessions rỗng thì false, not sessions sẽ là true
        print("No browser sessions found.")
        return

    print("Available sessions:")

    for session in sessions:
        print(f"- {session}")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python src/main.py list")
        print("  python src/main.py <account>")
        return

    command = sys.argv[1]

    if command == "list":
        show_accounts()
        return

    open_account(command)


if __name__ == "__main__":
    main()
