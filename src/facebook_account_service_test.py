import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch

from facebook.account_profile import (
    FacebookProfileMetadata,
    _capture_visible_avatar,
    _read_name_from_profile_button,
    extract_facebook_profile,
)
from models.facebook_account import FacebookAccount
from services.account_session_registry import AccountSessionRegistry
from services.facebook_account_asset_manager import (
    FacebookAccountAssetManager,
)
from services.facebook_account_repository import FacebookAccountRepository
from services.facebook_account_service import FacebookAccountService

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows has in-process locking only.
    fcntl = None


class FacebookAccountServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.sessions_dir = self.root / "browser_sessions"
        self.sessions_dir.mkdir()
        self.service = FacebookAccountService(
            FacebookAccountRepository(self.root / "accounts.json"),
            FacebookAccountAssetManager(self.root / "accounts"),
            sessions_dir=self.sessions_dir,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_merges_legacy_sessions_and_persists_profile(self) -> None:
        (self.sessions_dir / "acc01").mkdir()

        legacy = self.service.get_all()[0]
        self.assertEqual(legacy.id, "acc01")
        self.assertEqual(legacy.display_name, "acc01")

        updated = self.service.apply_metadata(
            "acc01",
            FacebookProfileMetadata(
                name="Nguyễn Minh Anh",
                profile_url="https://www.facebook.com/minhanh",
                avatar_data=b"avatar-bytes",
                avatar_extension="png",
            ),
        )
        updated = self.service.update_alias(updated.id, "Minh Anh cho thuê")

        self.assertEqual(updated.facebook_name, "Nguyễn Minh Anh")
        self.assertEqual(updated.display_name, "Minh Anh cho thuê")
        avatar_path = self.service.get_avatar_path(updated)
        self.assertIsNotNone(avatar_path)
        self.assertEqual(avatar_path.read_bytes(), b"avatar-bytes")

        reloaded = self.service.get_by_id("acc01")
        self.assertEqual(reloaded, updated)

    def test_pending_ids_delete_session_and_assets_safely(self) -> None:
        first = self.service.create_pending_account()
        second = self.service.create_pending_account()
        self.assertEqual(first.id, "account-001")
        self.assertEqual(second.id, "account-002")

        session_path = self.service.get_session_path(first.id)
        session_path.mkdir()
        self.assertFalse(self.service.has_session(first.id))
        (session_path / "Cookies").write_text("local", encoding="utf-8")
        synced = self.service.apply_metadata(
            first.id,
            FacebookProfileMetadata(
                name="Tài khoản thử nghiệm",
                profile_url="https://www.facebook.com/profile.php?id=1",
                avatar_data=b"avatar",
                avatar_extension=".jpg",
            ),
        )
        avatar_path = self.service.get_avatar_path(synced)
        self.assertTrue(self.service.has_session(first.id))

        self.assertTrue(self.service.delete_account(first.id))
        self.assertFalse(session_path.exists())
        self.assertFalse(avatar_path.exists())
        self.assertIsNone(self.service.get_by_id(first.id))
        self.assertIsNotNone(self.service.get_by_id(second.id))

    def test_busy_account_cannot_be_deleted(self) -> None:
        account = self.service.create_pending_account()
        with AccountSessionRegistry.exclusive(account.id):
            with self.assertRaisesRegex(RuntimeError, "đang chạy"):
                self.service.delete_account(account.id)
        self.assertIsNotNone(self.service.get_by_id(account.id))

    @unittest.skipUnless(fcntl is not None, "fcntl is unavailable")
    def test_external_profile_lock_prevents_session_deletion(self) -> None:
        account = self.service.create_pending_account()
        session_path = self.service.get_session_path(account.id)
        session_path.mkdir()
        lock_handle = (session_path / ".fb_poster.lock").open(
            "a+",
            encoding="utf-8",
        )
        fcntl.flock(
            lock_handle.fileno(),
            fcntl.LOCK_EX | fcntl.LOCK_NB,
        )
        try:
            with self.assertRaisesRegex(RuntimeError, "cửa sổ khác"):
                self.service.delete_account(account.id)
        finally:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
            lock_handle.close()

        self.assertTrue(session_path.is_dir())
        self.assertIsNotNone(self.service.get_by_id(account.id))

    def test_discard_pending_account_removes_unverified_session(self) -> None:
        account = self.service.create_pending_account()
        session_path = self.service.get_session_path(account.id)
        session_path.mkdir()
        (session_path / "Login Data").write_text("draft", encoding="utf-8")

        self.assertFalse(self.service.has_session(account.id))
        self.assertTrue(self.service.discard_if_unused(account.id))
        self.assertFalse(session_path.exists())
        self.assertIsNone(self.service.get_by_id(account.id))

    def test_invalid_ids_and_outside_avatar_paths_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            FacebookAccount(id="../escape")
        with self.assertRaises(ValueError):
            self.service.asset_manager.resolve_avatar_path("../avatar.jpg")

        broken = FacebookAccount(
            id="safe-account",
            facebook_name="Hồ sơ thiếu ảnh",
            avatar_path="../avatar.jpg",
        )
        self.assertIsNone(self.service.get_avatar_path(broken))

    def test_notification_title_is_not_accepted_as_profile_name(self) -> None:
        account = self.service.create_pending_account()
        corrupted = FacebookAccount(
            id=account.id,
            facebook_name="(5) Facebook",
            session_verified=True,
        )
        self.assertFalse(corrupted.is_synced)
        self.assertEqual(corrupted.display_name, account.id)

        with self.assertRaisesRegex(ValueError, "Không lấy được tên"):
            self.service.apply_metadata(
                account.id,
                FacebookProfileMetadata(
                    name="(5) Facebook",
                    profile_url="https://www.facebook.com/profile.php?id=1",
                ),
            )

        generic_profile_button = FacebookAccount(
            id=account.id,
            facebook_name="Trang cá nhân của bạn",
            session_verified=True,
        )
        self.assertFalse(generic_profile_button.is_synced)
        self.assertEqual(generic_profile_button.display_name, account.id)


class FacebookProfileExtractionTest(unittest.TestCase):
    def test_ignores_generic_profile_button_before_real_name(self) -> None:
        class EmptyLocator:
            first = None

            def __init__(self):
                self.first = self

            def count(self):
                return 0

        class ProfileButton:
            def __init__(self, text, accessible_name):
                self.text = text
                self.accessible_name = accessible_name

            def aria_snapshot(self, depth=0, timeout=None):
                return f'- button "{self.accessible_name}"'

            def inner_text(self, timeout=None):
                return self.text

        class Buttons:
            def __init__(self):
                self.buttons = (
                    ProfileButton("", "Trang cá nhân của bạn"),
                    ProfileButton("Nguyễn Dương", "Nguyễn Dương"),
                )

            def count(self):
                return len(self.buttons)

            def nth(self, index):
                return self.buttons[index]

        class Main:
            first = None

            def __init__(self):
                self.first = self

            def count(self):
                return 1

            def get_by_role(self, role):
                return Buttons() if role == "button" else EmptyLocator()

        class Page:
            def get_by_role(self, role):
                if role == "main":
                    return Main()
                return Buttons() if role == "button" else EmptyLocator()

        self.assertEqual(
            _read_name_from_profile_button(Page()),
            "Nguyễn Dương",
        )

    def test_captures_avatar_inside_profile_action_button(self) -> None:
        class Locator:
            def __init__(self, image_data=None, count=1):
                self.image_data = image_data
                self._count = count
                self.first = self

            def count(self):
                return self._count

            def is_visible(self, timeout=None):
                return self.image_data is not None

            def screenshot(self, type=None):
                return self.image_data

            def locator(self, selector):
                if selector in {"img", "svg image", "image"}:
                    return Locator(b"profile-avatar")
                return Locator(count=0)

        class Page:
            def locator(self, _selector):
                return Locator(count=0)

            def get_by_role(self, role, name, exact=False):
                if (
                    role == "button"
                    and name == "Hành động với ảnh đại diện"
                ):
                    return Locator()
                return Locator(count=0)

        avatar_data, extension = _capture_visible_avatar(Page())

        self.assertEqual(avatar_data, b"profile-avatar")
        self.assertEqual(extension, ".png")

    def test_uses_visible_heading_when_meta_title_is_generic(self) -> None:
        class Locator:
            def __init__(
                self,
                value="",
                count=1,
                visible=False,
                screenshot_data=None,
            ):
                self.value = value
                self._count = count
                self._visible = visible
                self._screenshot_data = screenshot_data
                self.first = self

            def count(self):
                return self._count

            def get_attribute(self, _name, timeout=None):
                return self.value

            def inner_text(self, timeout=None):
                return self.value

            def is_visible(self, timeout=None):
                return self._visible

            def screenshot(self, type=None):
                return self._screenshot_data

        class Page:
            url = (
                "https://www.facebook.com/profile.php?id=123"
                "&ref=profile"
            )

            def goto(self, *args, **kwargs):
                return None

            def wait_for_timeout(self, _milliseconds):
                return None

            def locator(self, selector):
                if selector == 'meta[property="og:title"]':
                    return Locator("(5) Facebook")
                if selector == 'meta[property="og:image"]':
                    return Locator("", count=0)
                if selector == "h1:visible":
                    return Locator("Nguyễn Minh Anh")
                if selector == (
                    'a[aria-label*="Ảnh đại diện" i] image'
                ):
                    return Locator(
                        visible=True,
                        screenshot_data=b"avatar-png",
                    )
                return Locator("", count=0)

            def title(self):
                return "Facebook"

        metadata = extract_facebook_profile(Page(), object())

        self.assertEqual(metadata.name, "Nguyễn Minh Anh")
        self.assertEqual(
            metadata.profile_url,
            "https://www.facebook.com/profile.php?id=123",
        )
        self.assertEqual(metadata.avatar_data, b"avatar-png")
        self.assertEqual(metadata.avatar_extension, ".png")

    def test_missing_avatar_keeps_profile_capture_open(self) -> None:
        class Page:
            url = "https://www.facebook.com/minhanh"

            def goto(self, *args, **kwargs):
                return None

            def wait_for_timeout(self, _milliseconds):
                return None

            def title(self):
                return "Nguyễn Minh Anh | Facebook"

        with patch(
            "facebook.account_profile._read_profile_heading",
            return_value="Nguyễn Minh Anh",
        ), patch(
            "facebook.account_profile._wait_for_visible_avatar",
            return_value=(None, None),
        ), patch(
            "facebook.account_profile._read_meta",
            return_value="",
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "chưa thấy ảnh đại diện",
            ):
                extract_facebook_profile(Page(), object())


if __name__ == "__main__":
    unittest.main()
