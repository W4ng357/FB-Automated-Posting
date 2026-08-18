import tempfile
import threading
import unittest

from pathlib import Path
from unittest.mock import patch

from models.account_posting_plan import AccountPostingPlan
from models.group_target import GroupTarget
from models.listing_posting_task import ListingPostingTask
from models.post_result import PostResult
from services.account_posting_service import AccountPostingService
from services.account_session_registry import (
    AccountSessionBusyError,
    AccountSessionRegistry,
)
from services.listing_asset_manager import ListingAssetManager
from services.listing_repository import ListingRepository
from services.listing_service import ListingService
from services.post_interval import (
    MAX_POST_INTERVAL,
    MAX_ROUND_INTERVAL,
    MIN_POST_INTERVAL,
    MIN_ROUND_INTERVAL,
    wait_random_minutes,
)


class FakeContext:
    def __init__(self) -> None:
        self.page = object()
        self.pages = [self.page]
        self.closed = False
        self.permissions = []
        self.close_error: Exception | None = None

    def new_page(self):
        return self.page

    def grant_permissions(self, permissions, origin):
        self.permissions.append((permissions, origin))

    def close(self):
        self.closed = True
        if self.close_error is not None:
            raise self.close_error


class FakeChromium:
    def __init__(self, context: FakeContext) -> None:
        self.context = context
        self.launches = 0
        self.last_launch_kwargs = None

    def launch_persistent_context(self, **kwargs):
        self.launches += 1
        self.last_launch_kwargs = kwargs
        return self.context


class FakePlaywrightManager:
    def __init__(self) -> None:
        self.context = FakeContext()
        self.chromium = FakeChromium(self.context)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class AccountPostingServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.session_path = root / "session"
        self.session_path.mkdir()
        self.listing_service = ListingService(
            ListingRepository(root / "listings.json"),
            ListingAssetManager(root / "listings"),
        )
        source = root / "room.jpg"
        source.write_bytes(b"test")
        self.first = self.listing_service.create_listing(
            title="Tin một",
            location="Hà Nội",
            price=2_000_000,
            image_paths=[source],
        )
        self.second = self.listing_service.create_listing(
            title="Tin hai",
            location="Hà Nội",
            price=3_000_000,
            image_paths=[source],
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_one_browser_and_page_is_reused_for_all_listing_tasks(self) -> None:
        playwright = FakePlaywrightManager()
        seen_pages = []

        def fake_posting_function(*, page, group_url, **_kwargs):
            seen_pages.append(page)
            return PostResult(
                group_url=group_url,
                group_name="Tên nhóm",
                success=True,
                post_url=None,
            )

        plan = AccountPostingPlan(
            "acc01",
            [
                ListingPostingTask(
                    self.first.id,
                    self.first.title,
                    [GroupTarget("https://facebook.com/groups/1", 2)],
                    {"https://facebook.com/groups/1": "Nhóm một"},
                ),
                ListingPostingTask(
                    self.second.id,
                    self.second.title,
                    [GroupTarget("https://facebook.com/groups/2", 1)],
                    {"https://facebook.com/groups/2": "Nhóm hai"},
                ),
            ],
        )
        progress = []
        service = AccountPostingService(
            listing_service=self.listing_service,
            playwright_factory=lambda: playwright,
            posting_function=fake_posting_function,
            wait_function=lambda *_args, **_kwargs: None,
        )
        entries = service.run_plan(
            self.session_path,
            plan,
            progress.append,
        )

        self.assertEqual(playwright.chromium.launches, 1)
        self.assertTrue(
            playwright.chromium.last_launch_kwargs["headless"]
        )
        self.assertEqual(seen_pages, [playwright.context.page] * 3)
        self.assertTrue(playwright.context.closed)
        self.assertEqual(len(entries), 3)
        self.assertEqual(progress[-1].completed, 3)
        self.assertEqual(progress[-1].total, 3)
        self.assertTrue(progress[-1].finished)

    def test_same_account_is_rejected_while_different_account_can_run(self) -> None:
        entered = threading.Event()
        release = threading.Event()

        def hold_account() -> None:
            with AccountSessionRegistry.exclusive("acc01"):
                entered.set()
                release.wait(2)

        thread = threading.Thread(target=hold_account)
        thread.start()
        self.assertTrue(entered.wait(1))
        self.assertTrue(AccountSessionRegistry.is_busy("acc01"))
        with self.assertRaises(AccountSessionBusyError):
            with AccountSessionRegistry.exclusive("acc01"):
                pass
        with AccountSessionRegistry.exclusive("acc02"):
            self.assertTrue(AccountSessionRegistry.is_busy("acc02"))
        release.set()
        thread.join(2)
        self.assertFalse(AccountSessionRegistry.is_busy("acc01"))

    def test_failed_attempt_does_not_skip_remaining_slots(self) -> None:
        playwright = FakePlaywrightManager()
        post_results = iter([False, True, True])

        def fail_first_attempt(*, group_url, **_kwargs):
            success = next(post_results)
            return PostResult(
                group_url=group_url,
                group_name="Nhóm lỗi",
                success=success,
                error=None if success else "Lỗi giả lập",
            )

        plan = AccountPostingPlan(
            "acc01",
            [
                ListingPostingTask(
                    self.first.id,
                    self.first.title,
                    [
                        GroupTarget(
                            "https://facebook.com/groups/1",
                            3,
                        )
                    ],
                )
            ],
        )
        progress = []
        service = AccountPostingService(
            listing_service=self.listing_service,
            playwright_factory=lambda: playwright,
            posting_function=fail_first_attempt,
            wait_function=lambda *_args, **_kwargs: None,
        )
        service.run_plan(
            self.session_path,
            plan,
            progress.append,
        )
        final = progress[-1]
        self.assertTrue(final.finished)
        self.assertEqual(final.attempted, 3)
        self.assertEqual(final.completed, 2)
        self.assertEqual(final.failed, 1)
        self.assertEqual(final.skipped, 0)
        self.assertEqual(final.remaining, 0)

    def test_composer_timeout_retries_once_without_using_an_extra_slot(
        self,
    ) -> None:
        playwright = FakePlaywrightManager()
        results = iter(
            [
                PostResult(
                    "https://facebook.com/groups/1",
                    "Nhóm",
                    False,
                    error=(
                        "Locator.press_sequentially: "
                        "Timeout 30000ms exceeded."
                    ),
                ),
                PostResult(
                    "https://facebook.com/groups/1",
                    "Nhóm",
                    True,
                ),
            ]
        )
        calls = []

        def post_once(**kwargs):
            calls.append(kwargs["group_url"])
            return next(results)

        plan = AccountPostingPlan(
            "acc01",
            [
                ListingPostingTask(
                    self.first.id,
                    self.first.title,
                    [GroupTarget("https://facebook.com/groups/1", 1)],
                )
            ],
        )
        progress = []
        entries = AccountPostingService(
            listing_service=self.listing_service,
            playwright_factory=lambda: playwright,
            posting_function=post_once,
            wait_function=lambda *_args, **_kwargs: None,
        ).run_plan(
            self.session_path,
            plan,
            progress.append,
        )

        self.assertEqual(
            calls,
            [
                "https://facebook.com/groups/1",
                "https://facebook.com/groups/1",
            ],
        )
        self.assertEqual(len(entries), 1)
        self.assertTrue(entries[0].result.success)
        self.assertEqual(progress[-1].attempted, 1)
        self.assertEqual(progress[-1].completed, 1)
        self.assertEqual(progress[-1].failed, 0)
        self.assertTrue(
            any("đang thử lại 1/1" in item.message for item in progress)
        )

    def test_stop_ignores_close_error_from_already_closed_browser(self) -> None:
        playwright = FakePlaywrightManager()
        playwright.context.close_error = RuntimeError(
            "Target page, context or browser has been closed"
        )
        stop = threading.Event()

        def post_once(*, group_url, **_kwargs):
            stop.set()
            return PostResult(group_url, "Nhóm", True)

        plan = AccountPostingPlan(
            "acc01",
            [
                ListingPostingTask(
                    self.first.id,
                    self.first.title,
                    [GroupTarget("https://facebook.com/groups/1", 2)],
                )
            ],
        )
        progress = []
        entries = AccountPostingService(
            listing_service=self.listing_service,
            playwright_factory=lambda: playwright,
            posting_function=post_once,
            wait_function=lambda *_args, **_kwargs: None,
        ).run_plan(
            self.session_path,
            plan,
            progress.append,
            stop_requested=stop.is_set,
        )

        self.assertEqual(len(entries), 1)
        self.assertTrue(progress[-1].stopped)

    def test_round_spans_all_listings_before_round_interval(self) -> None:
        playwright = FakePlaywrightManager()
        timeline = []
        waits = []

        def post_once(*, group_url, caption, **_kwargs):
            listing_title = caption.splitlines()[0]
            timeline.append(("post", listing_title, group_url))
            return PostResult(
                group_url=group_url,
                group_name=group_url.rsplit("/", 1)[-1],
                success=True,
                post_url=f"{group_url}/posts/{len(timeline)}",
            )

        def wait_once(
            minimum,
            maximum,
            message,
            progress_callback=None,
            **_kwargs,
        ):
            kind = "round" if minimum == MIN_ROUND_INTERVAL else "post"
            waits.append((kind, minimum, maximum, message))
            timeline.append(("wait", kind))
            if progress_callback is not None:
                progress_callback(message)

        plan = AccountPostingPlan(
            "acc01",
            [
                ListingPostingTask(
                    self.first.id,
                    self.first.title,
                    [
                        GroupTarget("https://facebook.com/groups/A", 2),
                        GroupTarget("https://facebook.com/groups/B", 3),
                        GroupTarget("https://facebook.com/groups/C", 2),
                    ],
                ),
                ListingPostingTask(
                    self.second.id,
                    self.second.title,
                    [
                        GroupTarget("https://facebook.com/groups/B", 4),
                        GroupTarget("https://facebook.com/groups/D", 5),
                    ],
                ),
            ],
        )
        live_results = []
        service = AccountPostingService(
            listing_service=self.listing_service,
            playwright_factory=lambda: playwright,
            posting_function=post_once,
            wait_function=wait_once,
        )
        entries = service.run_plan(
            self.session_path,
            plan,
            result_callback=lambda entry: (
                live_results.append(entry),
                timeline.append((
                    "result",
                    entry.listing_title,
                    entry.result.group_url,
                )),
            ),
        )

        posts = [item for item in timeline if item[0] == "post"]
        self.assertEqual(
            posts,
            [
                ("post", "Tin một", "https://facebook.com/groups/A"),
                ("post", "Tin một", "https://facebook.com/groups/B"),
                ("post", "Tin một", "https://facebook.com/groups/C"),
                ("post", "Tin hai", "https://facebook.com/groups/B"),
                ("post", "Tin hai", "https://facebook.com/groups/D"),
                ("post", "Tin một", "https://facebook.com/groups/A"),
                ("post", "Tin một", "https://facebook.com/groups/B"),
                ("post", "Tin một", "https://facebook.com/groups/C"),
                ("post", "Tin hai", "https://facebook.com/groups/B"),
                ("post", "Tin hai", "https://facebook.com/groups/D"),
                ("post", "Tin một", "https://facebook.com/groups/B"),
                ("post", "Tin hai", "https://facebook.com/groups/B"),
                ("post", "Tin hai", "https://facebook.com/groups/D"),
                ("post", "Tin hai", "https://facebook.com/groups/B"),
                ("post", "Tin hai", "https://facebook.com/groups/D"),
                ("post", "Tin hai", "https://facebook.com/groups/D"),
            ],
        )
        self.assertEqual(len(entries), 16)
        self.assertEqual(live_results, entries)
        self.assertEqual(
            sum(wait[0] == "post" for wait in waits),
            11,
        )
        self.assertEqual(
            sum(wait[0] == "round" for wait in waits),
            4,
        )
        self.assertTrue(
            all(
                (minimum, maximum)
                == (
                    (MIN_POST_INTERVAL, MAX_POST_INTERVAL)
                    if kind == "post"
                    else (MIN_ROUND_INTERVAL, MAX_ROUND_INTERVAL)
                )
                for kind, minimum, maximum, _message in waits
            )
        )
        for index, item in enumerate(timeline):
            if item[0] == "post":
                self.assertEqual(timeline[index + 1][0], "result")

    def test_stop_requested_during_post_stops_at_next_boundary(self) -> None:
        playwright = FakePlaywrightManager()
        stop = threading.Event()
        posted_urls = []

        def post_once(*, group_url, **_kwargs):
            posted_urls.append(group_url)
            stop.set()
            return PostResult(group_url, "Nhóm", True)

        plan = AccountPostingPlan(
            "acc01",
            [
                ListingPostingTask(
                    self.first.id,
                    self.first.title,
                    [
                        GroupTarget("https://facebook.com/groups/1", 2),
                        GroupTarget("https://facebook.com/groups/2", 2),
                    ],
                )
            ],
        )
        progress = []
        live_results = []
        service = AccountPostingService(
            listing_service=self.listing_service,
            playwright_factory=lambda: playwright,
            posting_function=post_once,
            wait_function=lambda *_args, **_kwargs: None,
        )
        entries = service.run_plan(
            self.session_path,
            plan,
            progress.append,
            live_results.append,
            stop.is_set,
        )

        self.assertEqual(posted_urls, ["https://facebook.com/groups/1"])
        self.assertEqual(live_results, entries)
        self.assertEqual(len(entries), 1)
        self.assertTrue(progress[-1].finished)
        self.assertTrue(progress[-1].stopped)
        self.assertEqual(progress[-1].attempted, 1)

    def test_stop_requested_during_interval_cancels_next_post(self) -> None:
        playwright = FakePlaywrightManager()
        stop = threading.Event()
        posted_urls = []

        def post_once(*, group_url, **_kwargs):
            posted_urls.append(group_url)
            return PostResult(group_url, "Nhóm", True)

        def stop_in_wait(*_args, **_kwargs):
            stop.set()

        plan = AccountPostingPlan(
            "acc01",
            [
                ListingPostingTask(
                    self.first.id,
                    self.first.title,
                    [
                        GroupTarget("https://facebook.com/groups/1", 2),
                        GroupTarget("https://facebook.com/groups/2", 2),
                    ],
                )
            ],
        )
        progress = []
        service = AccountPostingService(
            listing_service=self.listing_service,
            playwright_factory=lambda: playwright,
            posting_function=post_once,
            wait_function=stop_in_wait,
        )
        service.run_plan(
            self.session_path,
            plan,
            progress.append,
            stop_requested=stop.is_set,
        )

        self.assertEqual(posted_urls, ["https://facebook.com/groups/1"])
        self.assertTrue(progress[-1].stopped)

    def test_default_interval_wait_can_be_interrupted(self) -> None:
        stop_checks = iter((False, True))
        messages = []

        with patch(
            "services.post_interval.random.randint",
            return_value=60,
        ), patch("services.post_interval.time.sleep") as sleep:
            completed = wait_random_minutes(
                1,
                1,
                "Đang chờ",
                progress_callback=messages.append,
                stop_requested=lambda: next(stop_checks),
            )

        self.assertFalse(completed)
        self.assertEqual(messages, ["[~] Đang chờ: 1m 0s"])
        sleep.assert_called_once_with(0.25)
