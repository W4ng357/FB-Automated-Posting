import unittest

from pathlib import Path
from unittest.mock import patch

from facebook.group_poster import post_to_group


class FakeLocator:
    def __init__(self) -> None:
        self.clicked = False
        self.files = None
        self.text = None
        self.waited = False
        self.role_calls = []

    @property
    def first(self):
        return self

    def click(self):
        self.clicked = True

    def get_by_role(self, role, **kwargs):
        self.role_calls.append((role, kwargs))
        return self

    def locator(self, *_args, **_kwargs):
        return self

    def press_sequentially(self, text):
        self.text = text

    def set_input_files(self, files):
        self.files = files

    def wait_for(self, **_kwargs):
        self.waited = True


class FakePage(FakeLocator):
    def __init__(self, fail_navigation: bool = False) -> None:
        super().__init__()
        self.fail_navigation = fail_navigation

    def goto(self, *_args, **_kwargs):
        if self.fail_navigation:
            raise RuntimeError("navigation failed")


class GroupPosterTest(unittest.TestCase):
    def test_uses_the_original_composer_button_locator(self) -> None:
        page = FakePage()
        with patch(
            "facebook.group_poster.get_group_name",
            return_value="Nhóm thử nghiệm",
        ), patch(
            "facebook.group_poster.get_latest_post_url",
            return_value=None,
        ):
            result = post_to_group(
                page,
                "https://facebook.com/groups/123",
                "Nội dung",
                [Path("/tmp/image.jpg")],
            )

        self.assertTrue(result.success)
        self.assertIn(
            ("button", {"name": "Bạn viết gì đi..."}),
            page.role_calls,
        )

    def test_permalink_failure_does_not_turn_success_into_failure(self) -> None:
        page = FakePage()
        with patch(
            "facebook.group_poster.get_group_name",
            return_value="Nhóm thử nghiệm",
        ), patch(
            "facebook.group_poster.get_latest_post_url",
            side_effect=RuntimeError("URL unavailable"),
        ):
            result = post_to_group(
                page,
                "https://facebook.com/groups/123",
                "Nội dung",
                [Path("/tmp/image.jpg")],
            )

        self.assertTrue(result.success)
        self.assertIsNone(result.post_url)
        self.assertEqual(result.group_name, "Nhóm thử nghiệm")

    def test_posting_failure_is_returned_as_result(self) -> None:
        result = post_to_group(
            FakePage(fail_navigation=True),
            "https://facebook.com/groups/123",
            "Nội dung",
            [Path("/tmp/image.jpg")],
        )

        self.assertFalse(result.success)
        self.assertIn("navigation failed", result.error)


if __name__ == "__main__":
    unittest.main()
