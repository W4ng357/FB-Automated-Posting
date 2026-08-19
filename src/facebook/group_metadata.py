from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import sync_playwright

from facebook.browser_launcher import launch_persistent_context as launch_browser_context
from facebook.get_group_name import get_group_name
from services.account_session_registry import AccountSessionRegistry
from session_manager import get_session


@dataclass(frozen=True)
class GroupMetadata:
    name: str


def fetch_group_metadata(
    session_path: Path,
    group_url: str,
) -> GroupMetadata:
    """Fetch only the Facebook group name using the selected session."""
    with sync_playwright() as playwright:
        context = launch_browser_context(
            playwright,
            user_data_dir=session_path,
            headless=False,
        )
        try:
            page = (
                context.pages[0]
                if context.pages
                else context.new_page()
            )
            page.goto(group_url, wait_until="domcontentloaded")
            return GroupMetadata(name=get_group_name(page))
        finally:
            context.close()


def fetch_group_metadata_for_account(
    account_name: str,
    group_url: str,
) -> GroupMetadata:
    session_path = get_session(account_name)
    with AccountSessionRegistry.exclusive(account_name, session_path):
        return fetch_group_metadata(session_path, group_url)

