import unittest

from pathlib import Path
from unittest.mock import patch

from facebook.group_metadata import fetch_group_metadata


class FakePage:
    def __init__(self) -> None:
        self.visited_url: str | None = None

    def goto(self, url: str, wait_until: str) -> None:
        self.visited_url = url
        self.wait_until = wait_until

    def locator(self, *_args, **_kwargs):
        raise AssertionError("Image locators must not be used")

    def get_by_role(self, *_args, **_kwargs):
        raise AssertionError("Cover image locators must not be used")


class FakeContext:
    def __init__(self) -> None:
        self.page = FakePage()
        self.pages = [self.page]
        self.closed = False

    def new_page(self):
        return self.page

    def close(self) -> None:
        self.closed = True


class FakePlaywright:
    def __init__(self) -> None:
        self.context = FakeContext()
        self.chromium = self

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def launch_persistent_context(self, **kwargs):
        self.launch_arguments = kwargs
        return self.context


class GroupMetadataTest(unittest.TestCase):
    def test_fetch_reads_only_group_name(self) -> None:
        playwright = FakePlaywright()
        group_url = "https://www.facebook.com/groups/123"
        with patch(
            "facebook.group_metadata.sync_playwright",
            return_value=playwright,
        ), patch(
            "facebook.group_metadata.get_group_name",
            return_value="Tên nhóm",
        ) as get_name:
            metadata = fetch_group_metadata(
                Path("/tmp/session"),
                group_url,
            )

        self.assertEqual(metadata.name, "Tên nhóm")
        self.assertEqual(playwright.context.page.visited_url, group_url)
        self.assertEqual(
            playwright.context.page.wait_until,
            "domcontentloaded",
        )
        get_name.assert_called_once_with(playwright.context.page)
        self.assertTrue(playwright.context.closed)


if __name__ == "__main__":
    unittest.main()

