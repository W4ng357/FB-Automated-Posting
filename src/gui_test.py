import base64
import tempfile
import time
import unittest

from pathlib import Path
from unittest.mock import patch


try:
    from PySide6.QtCore import QEventLoop, QSize, QTimer
    from PySide6.QtWidgets import (
        QApplication,
        QDialog,
        QMessageBox,
        QPushButton,
    )

    PYSIDE_AVAILABLE = True
except ModuleNotFoundError:
    PYSIDE_AVAILABLE = False


if PYSIDE_AVAILABLE:
    from gui.dialogs.group_selector_dialog import GroupSelectorDialog
    from gui.dialogs.group_dialog import GroupDialog
    from gui.dialogs.listing_dialog import ListingDialog
    from gui.dialogs.account_login_dialog import AccountLoginDialog
    from gui.dialogs.account_manager_dialog import (
        AccountCard,
        AccountEditDialog,
        AccountManagerDialog,
    )
    from gui.main_window import MainWindow
    from gui.pages.groups_page import GroupsPage
    from gui.widgets.account_posting_tab import AccountPostingTab
    from gui.widgets.design_components import RoundedThumbnail
    from gui.workers.group_metadata_worker import GroupMetadataWorker
    from gui.workers.account_login_worker import AccountLoginWorker
    from gui.workers.posting_worker import PostingWorker
    from facebook.group_metadata import GroupMetadata
    from facebook.account_profile import FacebookProfileMetadata
    from models.group_target import GroupTarget
    from models.listing_posting_task import ListingPostingTask
    from models.post_result import PostResult
    from models.posting_progress import PostingProgress
    from models.posting_result_entry import PostingResultEntry
    from services.group_asset_manager import GroupAssetManager
    from services.group_repository import GroupRepository
    from services.group_service import GroupService
    from services.listing_asset_manager import ListingAssetManager
    from services.listing_draft_manager import ListingDraftManager
    from services.listing_repository import ListingRepository
    from services.listing_service import ListingService
    from services.facebook_account_asset_manager import (
        FacebookAccountAssetManager,
    )
    from services.facebook_account_repository import FacebookAccountRepository
    from services.facebook_account_service import FacebookAccountService


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed")
class GuiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.listing_service = ListingService(
            ListingRepository(self.root / "listings.json"),
            ListingAssetManager(self.root / "listings"),
        )
        self.group_service = GroupService(
            GroupRepository(self.root / "groups.json"),
            GroupAssetManager(self.root / "groups"),
        )
        self.sessions_dir = self.root / "browser_sessions"
        self.sessions_dir.mkdir()
        self.account_service = FacebookAccountService(
            FacebookAccountRepository(self.root / "accounts.json"),
            FacebookAccountAssetManager(self.root / "accounts"),
            sessions_dir=self.sessions_dir,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _source_image(self, name: str = "room.jpg") -> Path:
        source = self.root / name
        source.write_bytes(b"test-image")
        return source

    @staticmethod
    def _avatar_png() -> bytes:
        return base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC"
            "AAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )

    def test_circular_avatar_clips_its_corners(self) -> None:
        avatar = RoundedThumbnail(
            fallback_text="N",
            size=QSize(54, 54),
            circular=True,
        )
        avatar.show()
        self.application.processEvents()
        image = avatar.grab().toImage()
        avatar.close()

        self.assertNotEqual(
            image.pixelColor(5, 10).getRgb(),
            image.pixelColor(27, 1).getRgb(),
        )
        self.assertEqual(image.pixelColor(27, 27).alpha(), 255)

    def test_account_profile_is_used_across_posting_and_group_ui(self) -> None:
        account = self.account_service.create_pending_account()
        self.account_service.get_session_path(account.id).mkdir()
        account = self.account_service.apply_metadata(
            account.id,
            FacebookProfileMetadata(
                name="Nguyễn Minh Anh",
                profile_url="https://www.facebook.com/minhanh",
                avatar_data=self._avatar_png(),
                avatar_extension=".png",
            ),
        )

        window = MainWindow(
            self.listing_service,
            self.group_service,
            self.account_service,
        )
        tab = window.posting_page.account_tabs[account.id]
        tab_index = window.posting_page.tabs.indexOf(tab)
        self.assertEqual(tab.account_title.text(), "Nguyễn Minh Anh")
        self.assertIn(
            "Nguyễn Minh Anh",
            window.posting_page.tabs.tabText(tab_index),
        )
        tab_avatar = window.posting_page.tabs.tabIcon(tab_index).pixmap(
            QSize(22, 22)
        ).toImage()
        self.assertEqual(tab_avatar.pixelColor(0, 0).alpha(), 0)
        self.assertEqual(tab_avatar.pixelColor(11, 11).alpha(), 255)
        self.assertTrue(tab.session_available)
        self.assertTrue(tab.start_button.isEnabled())

        edit = AccountEditDialog(self.account_service, account)
        edit.alias_input.setText("Tài khoản chủ nhà")
        edit._save()
        window.posting_page.refresh_data()
        self.assertEqual(tab.account_title.text(), "Tài khoản chủ nhà")
        self.assertIn(
            "Tài khoản chủ nhà",
            window.posting_page.tabs.tabText(tab_index),
        )

        group_dialog = GroupDialog(
            self.group_service,
            account_service=self.account_service,
        )
        self.assertEqual(group_dialog.account_combo.currentData(), account.id)
        self.assertEqual(
            group_dialog.account_combo.currentText(),
            "Tài khoản chủ nhà",
        )
        group_dialog.reject()

        manager = AccountManagerDialog(self.account_service)
        card = manager.accounts_layout.itemAt(0).widget()
        self.assertIsInstance(card, AccountCard)
        manager.reject()
        window.close()

    def test_pending_account_is_visible_but_cannot_start(self) -> None:
        account = self.account_service.create_pending_account()
        window = MainWindow(
            self.listing_service,
            self.group_service,
            self.account_service,
        )
        tab = window.posting_page.account_tabs[account.id]
        tab_index = window.posting_page.tabs.indexOf(tab)

        self.assertFalse(tab.start_button.isEnabled())
        self.assertEqual(tab.status_label.text(), "Chưa đăng nhập")
        self.assertIn(
            "Chưa đăng nhập",
            window.posting_page.tabs.tabText(tab_index),
        )
        self.assertFalse(window.posting_page.start_all_button.isEnabled())
        window.close()

    def test_login_dialog_saves_received_profile(self) -> None:
        account = self.account_service.create_pending_account()
        dialog = AccountLoginDialog(self.account_service, account)
        dialog._on_profile_ready(
            FacebookProfileMetadata(
                name="Hồ sơ vừa đăng nhập",
                profile_url="https://www.facebook.com/new-account",
                avatar_data=self._avatar_png(),
                avatar_extension="png",
            )
        )

        saved = self.account_service.get_by_id(account.id)
        self.assertEqual(saved.facebook_name, "Hồ sơ vừa đăng nhập")
        self.assertEqual(dialog.status_badge.text(), "Đã đồng bộ")
        self.assertTrue(dialog._profile_saved)
        dialog.reject()

    def test_login_worker_round_trip_closes_browser_thread(self) -> None:
        account = self.account_service.create_pending_account()

        def worker_factory(account_id, session_path):
            def fake_runner(
                _account_id,
                _session_path,
                capture_requested,
                _cancel_requested,
                status_callback,
            ):
                status_callback("Cửa sổ Facebook đã sẵn sàng.")
                if not capture_requested.wait(1):
                    raise TimeoutError("Không nhận được yêu cầu lấy hồ sơ")
                return FacebookProfileMetadata(
                    name="Hồ sơ qua worker",
                    profile_url="https://www.facebook.com/worker-profile",
                    avatar_data=self._avatar_png(),
                    avatar_extension=".png",
                )

            return AccountLoginWorker(
                account_id,
                session_path,
                session_runner=fake_runner,
            )

        dialog = AccountLoginDialog(
            self.account_service,
            account,
            worker_factory=worker_factory,
        )
        loop = QEventLoop()
        dialog.accepted.connect(loop.quit)
        dialog._start_browser()
        QTimer.singleShot(20, dialog._request_profile)
        QTimer.singleShot(2_000, loop.quit)
        loop.exec()

        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        self.assertFalse(dialog.is_running)
        self.assertEqual(
            self.account_service.get_by_id(account.id).facebook_name,
            "Hồ sơ qua worker",
        )

    def test_account_manager_confirms_and_deletes_account(self) -> None:
        account = self.account_service.create_pending_account()
        session_path = self.account_service.get_session_path(account.id)
        session_path.mkdir()
        manager = AccountManagerDialog(self.account_service)

        with patch(
            "gui.dialogs.account_manager_dialog.QMessageBox.warning",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            manager._delete_account(account.id)

        self.assertIsNone(self.account_service.get_by_id(account.id))
        self.assertFalse(session_path.exists())
        manager.reject()

    def test_main_window_has_three_pages_and_account_tabs(self) -> None:
        listing = self.listing_service.create_listing(
            title="Phòng trọ",
            location="Hà Nội",
            price=2_000_000,
        )
        (self.sessions_dir / "acc01").mkdir()
        (self.sessions_dir / "acc02").mkdir()
        window = MainWindow(
            self.listing_service,
            self.group_service,
            self.account_service,
        )
        self.assertEqual(window.listings_page.listings, [listing])
        self.assertEqual(window.page_stack.count(), 3)
        self.assertEqual(window.listings_button.text(), "Phòng")
        self.assertEqual(
            set(window.posting_page.account_tabs),
            {"acc01", "acc02"},
        )
        window.close()

    def test_listing_dialog_uses_and_cleans_draft_folder(self) -> None:
        draft_manager = ListingDraftManager(self.root / "drafts")
        dialog = ListingDialog(
            self.listing_service,
            draft_manager=draft_manager,
        )
        source = self._source_image()
        second = self._source_image("kitchen.png")
        draft_manager.add_images(dialog.draft_id, [source, second])
        pasted = draft_manager.get_images_dir(dialog.draft_id) / "pasted.jpg"
        pasted.write_bytes(b"pasted-image")
        dialog._refresh_images_from_disk()
        draft_dir = draft_manager.get_images_dir(dialog.draft_id).parent
        self.assertTrue(draft_dir.is_dir())
        dialog.title_input.setText("Phòng trọ")
        dialog.address_input.setText("Cầu Giấy, Hà Nội")
        dialog.price_input.setValue(2.5)
        self.assertEqual(
            dialog.price_input.price_in_vnd(),
            2_500_000,
        )
        dialog.preview_button.click()
        self.application.processEvents()
        self.assertIs(
            dialog.workspace_tabs.currentWidget(),
            dialog.post_preview,
        )
        self.assertIn(
            "📍 Địa chỉ: Cầu Giấy, Hà Nội",
            dialog.post_preview.caption.text(),
        )
        self.assertNotIn(
            "Khu vực",
            dialog.post_preview.caption.text(),
        )
        dialog._save()
        created = dialog.saved_listing
        self.assertIsNotNone(created)
        self.assertEqual(created.price, 2_500_000)
        self.assertEqual(created.address, "Cầu Giấy, Hà Nội")
        self.assertEqual(created.location, "Cầu Giấy, Hà Nội")
        self.assertEqual(
            len(self.listing_service.get_images(created.id)),
            3,
        )
        self.assertFalse(draft_dir.exists())

        cancel_dialog = ListingDialog(
            self.listing_service,
            draft_manager=draft_manager,
        )
        cancel_dir = draft_manager.get_images_dir(
            cancel_dialog.draft_id
        ).parent
        cancel_dialog.reject()
        self.assertFalse(cancel_dir.exists())

        with patch(
            "gui.dialogs.listing_dialog.QDesktopServices.openUrl"
        ) as open_url:
            edit_dialog = ListingDialog(
                self.listing_service,
                created,
                draft_manager=draft_manager,
            )
            edit_dialog._open_images_folder()
            open_url.assert_called_once()
            edit_dialog.title_input.setText("Phòng trọ đã sửa")
            edit_dialog._save()
        self.assertEqual(
            self.listing_service.get_by_id(created.id).title,
            "Phòng trọ đã sửa",
        )

    def test_new_listing_cannot_be_saved_without_an_image(self) -> None:
        draft_manager = ListingDraftManager(self.root / "drafts")
        dialog = ListingDialog(
            self.listing_service,
            draft_manager=draft_manager,
        )
        dialog.title_input.setText("Phòng chưa có ảnh")
        dialog.address_input.setText("Cầu Giấy, Hà Nội")

        with patch(
            "gui.dialogs.listing_dialog.QMessageBox.warning"
        ) as warning:
            dialog._save()

        warning.assert_called_once_with(
            dialog,
            "Thiếu ảnh phòng",
            "Hãy thêm ít nhất 1 ảnh phòng trước khi lưu.",
        )
        self.assertIsNone(dialog.saved_listing)
        self.assertEqual(self.listing_service.get_all(), [])
        self.assertIs(
            dialog.workspace_tabs.currentWidget(),
            dialog.editor_pane,
        )
        dialog.reject()

    def test_edit_cannot_remove_the_last_listing_image(self) -> None:
        source = self._source_image()
        listing = self.listing_service.create_listing(
            title="Phòng có ảnh",
            location="Cầu Giấy, Hà Nội",
            address="Cầu Giấy, Hà Nội",
            price=3_500_000,
            image_paths=[source],
        )
        dialog = ListingDialog(self.listing_service, listing)
        stored_image = self.listing_service.get_images(listing.id)[0]
        dialog._remove_image_from_selection(str(stored_image))
        dialog.title_input.setText("Tên không được lưu")

        with patch(
            "gui.dialogs.listing_dialog.QMessageBox.warning"
        ) as warning:
            dialog._save()

        warning.assert_called_once_with(
            dialog,
            "Thiếu ảnh phòng",
            "Hãy thêm ít nhất 1 ảnh phòng trước khi lưu.",
        )
        unchanged = self.listing_service.get_by_id(listing.id)
        self.assertEqual(unchanged.title, "Phòng có ảnh")
        self.assertEqual(
            self.listing_service.get_images(listing.id),
            [stored_image],
        )
        dialog.reject()

    def test_preview_switches_tabs_without_resizing_or_clipping(self) -> None:
        draft_manager = ListingDraftManager(self.root / "drafts")
        dialog = ListingDialog(
            self.listing_service,
            draft_manager=draft_manager,
        )
        dialog.resize(980, 720)
        dialog.show()
        self.application.processEvents()
        self.application.processEvents()
        compact_size = dialog.size()

        self.assertLess(
            dialog.details_panel.geometry().bottom(),
            dialog.images_panel.geometry().top(),
        )
        self.assertLess(
            dialog.description_input.geometry().bottom(),
            dialog.contact_input.geometry().top(),
        )

        dialog.preview_button.click()
        self.application.processEvents()

        self.assertEqual(dialog.size(), compact_size)
        self.assertIs(
            dialog.workspace_tabs.currentWidget(),
            dialog.post_preview,
        )
        self.assertLessEqual(
            dialog.post_preview.geometry().right(),
            dialog.workspace_tabs.rect().right(),
        )

        dialog.preview_button.click()
        self.application.processEvents()
        self.assertEqual(dialog.size(), compact_size)
        self.assertIs(
            dialog.workspace_tabs.currentWidget(),
            dialog.editor_pane,
        )
        dialog.reject()

    def test_saved_groups_feed_checkbox_selector(self) -> None:
        first = self.group_service.create_group(
            "https://facebook.com/groups/123",
            "Nhóm một",
        )
        self.group_service.create_group(
            "https://facebook.com/groups/456",
            "Nhóm hai",
        )
        selector = GroupSelectorDialog(
            self.group_service,
            selected_counts={first.url: 3},
        )
        targets, names = selector.selected_targets()
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].target_count, 3)
        self.assertEqual(names[first.url], first.name)
        selector.reject()

    def test_group_name_persistence_refresh_and_search(self) -> None:
        captured = []
        worker = GroupMetadataWorker(
            "acc01",
            "https://facebook.com/groups/123",
            fetch_function=lambda _account, _url: GroupMetadata(
                name="Nhóm lấy từ Facebook",
            ),
        )
        worker.finished.connect(captured.append)
        worker.run()
        self.assertEqual(captured[0].name, "Nhóm lấy từ Facebook")

        with patch(
            "gui.dialogs.group_dialog.list_sessions",
            return_value=["acc01"],
        ):
            dialog = GroupDialog(self.group_service)
        dialog.url_input.setText(
            "https://www.facebook.com/groups/123"
        )
        dialog._on_metadata_ready(captured[0])
        self.assertEqual(
            dialog.name_input.text(),
            "Nhóm lấy từ Facebook",
        )
        dialog._save()
        saved = dialog.saved_group
        self.assertIsNotNone(saved)

        reloaded_service = GroupService(
            GroupRepository(self.root / "groups.json"),
            GroupAssetManager(self.root / "groups"),
        )
        self.assertEqual(reloaded_service.get_by_id(saved.id), saved)

        with patch(
            "gui.dialogs.group_dialog.list_sessions",
            return_value=["acc01"],
        ):
            refresh_dialog = GroupDialog(
                reloaded_service,
                group=saved,
            )
        refresh_dialog._on_metadata_ready(
            GroupMetadata(
                name="Tên nhóm đã làm mới",
            )
        )
        refresh_dialog._save()
        self.assertEqual(
            reloaded_service.get_by_id(saved.id).name,
            "Tên nhóm đã làm mới",
        )

        page = GroupsPage(reloaded_service)
        page.show()
        page.search_input.setText("không tồn tại")
        self.application.processEvents()
        self.assertEqual(page.search_input.text(), "không tồn tại")
        page.close()
        self.assertTrue(reloaded_service.delete_group(saved.id))

    def test_account_worker_keeps_gui_responsive_and_renders_results(self) -> None:
        source = self._source_image()
        listing = self.listing_service.create_listing(
            title="Phòng trọ",
            location="Hà Nội",
            price=2_000_000,
            image_paths=[source],
        )
        group = self.group_service.create_group(
            "https://facebook.com/groups/123",
            "Nhóm thử nghiệm",
        )

        class FakePostingService:
            def run_plan(
                self,
                session_path,
                plan,
                progress_callback,
                result_callback,
                stop_requested,
            ):
                time.sleep(0.05)
                progress_callback(
                    PostingProgress(
                        completed=1,
                        total=1,
                        current_group_name=group.name,
                        next_group_name=None,
                        current_listing_title=listing.title,
                        message="Thành công",
                        attempted=1,
                        finished=True,
                    )
                )
                entry = PostingResultEntry(
                    account_name=plan.account_name,
                    listing_id=listing.id,
                    listing_title=listing.title,
                    result=PostResult(
                        group_url=group.url,
                        group_name=group.name,
                        success=True,
                        post_url=None,
                    ),
                )
                result_callback(entry)
                time.sleep(0.03)
                return [entry]

        def worker_factory(session_path, plan):
            return PostingWorker(
                session_path,
                plan,
                posting_service=FakePostingService(),
            )

        tab = AccountPostingTab(
            "acc01",
            self.listing_service,
            self.group_service,
            worker_factory=worker_factory,
        )
        tab.tasks.append(
            ListingPostingTask(
                listing.id,
                listing.title,
                [GroupTarget(group.url, 1)],
                {group.url: group.name},
            )
        )
        tab._render_queue()
        event_loop = QEventLoop()
        timer_fired: list[bool] = []
        tab.running_changed.connect(
            lambda _account, running: (
                event_loop.quit() if not running else None
            )
        )
        QTimer.singleShot(10, lambda: timer_fired.append(True))
        with patch(
            "gui.widgets.account_posting_tab.get_session",
            return_value=self.root,
        ):
            self.assertTrue(tab.start())
            live_result_seen = []

            def observe_live_result() -> None:
                if tab.result_entries:
                    live_result_seen.append(
                        (tab.is_running, len(tab.result_entries))
                    )
                    return
                QTimer.singleShot(5, observe_live_result)

            QTimer.singleShot(5, observe_live_result)
            event_loop.exec()

        self.assertEqual(timer_fired, [True])
        self.assertEqual(tab.last_progress.completed, 1)
        self.assertEqual(tab._completion_status, "Hoàn tất")
        self.assertEqual(live_result_seen, [(True, 1)])
        self.assertEqual(
            tab.activity_tabs.tabText(tab.results_tab_index),
            "Kết quả (1)",
        )
        self.assertGreater(tab.results_layout.count(), 1)
        result_card = tab.results_layout.itemAt(0).widget()
        self.assertTrue(
            any(
                button.text() == "Mở nhóm"
                for button in result_card.findChildren(QPushButton)
            )
        )

    def test_concurrent_accounts_and_duplicate_start_stops(self) -> None:
        source = self._source_image()
        listing = self.listing_service.create_listing(
            title="Phòng trọ",
            location="Hà Nội",
            price=2_000_000,
            image_paths=[source],
        )
        group = self.group_service.create_group(
            "https://facebook.com/groups/123",
            "Nhóm thử nghiệm",
        )

        class SlowFakeService:
            def run_plan(
                self,
                session_path,
                plan,
                progress_callback,
                result_callback,
                stop_requested,
            ):
                time.sleep(0.08)
                progress_callback(
                    PostingProgress(
                        completed=1,
                        total=1,
                        current_group_name=group.name,
                        next_group_name=None,
                        current_listing_title=listing.title,
                        message="Hoàn tất",
                        attempted=1,
                        finished=True,
                    )
                )
                entry = PostingResultEntry(
                    plan.account_name,
                    listing.id,
                    listing.title,
                    PostResult(
                        group.url,
                        group.name,
                        True,
                    ),
                )
                result_callback(entry)
                return [entry]

        def worker_factory(session_path, plan):
            return PostingWorker(
                session_path,
                plan,
                posting_service=SlowFakeService(),
            )

        tabs = [
            AccountPostingTab(
                account,
                self.listing_service,
                self.group_service,
                worker_factory=worker_factory,
            )
            for account in ("acc01", "acc02")
        ]
        for tab in tabs:
            tab.tasks.append(
                ListingPostingTask(
                    listing.id,
                    listing.title,
                    [GroupTarget(group.url, 1)],
                    {group.url: group.name},
                )
            )
            tab._render_queue()

        event_loop = QEventLoop()
        finished_accounts: set[str] = set()
        observed_parallel: list[bool] = []

        def on_running(account: str, running: bool) -> None:
            if not running:
                finished_accounts.add(account)
                if len(finished_accounts) == 2:
                    event_loop.quit()

        for tab in tabs:
            tab.running_changed.connect(on_running)

        with patch(
            "gui.widgets.account_posting_tab.get_session",
            return_value=self.root,
        ):
            self.assertTrue(tabs[0].start())
            self.assertFalse(tabs[0].start())
            self.assertTrue(tabs[1].start())
            QTimer.singleShot(
                10,
                lambda: observed_parallel.append(
                    tabs[0].is_running and tabs[1].is_running
                ),
            )
            event_loop.exec()

        self.assertEqual(observed_parallel, [True])
        self.assertEqual(finished_accounts, {"acc01", "acc02"})
        self.assertTrue(all(tab.start_button.isEnabled() for tab in tabs))

    def test_worker_error_restores_account_controls(self) -> None:
        source = self._source_image()
        listing = self.listing_service.create_listing(
            title="Phòng trọ",
            location="Hà Nội",
            price=2_000_000,
            image_paths=[source],
        )
        group = self.group_service.create_group(
            "https://facebook.com/groups/123",
            "Nhóm thử nghiệm",
        )

        class FailingService:
            def run_plan(self, **_kwargs):
                raise RuntimeError("Lỗi giả lập")

        tab = AccountPostingTab(
            "acc01",
            self.listing_service,
            self.group_service,
            worker_factory=lambda session_path, plan: PostingWorker(
                session_path,
                plan,
                posting_service=FailingService(),
            ),
        )
        tab.tasks.append(
            ListingPostingTask(
                listing.id,
                listing.title,
                [GroupTarget(group.url, 1)],
                {group.url: group.name},
            )
        )
        tab._render_queue()
        loop = QEventLoop()
        tab.running_changed.connect(
            lambda _account, running: loop.quit() if not running else None
        )
        with patch(
            "gui.widgets.account_posting_tab.get_session",
            return_value=self.root,
        ), patch(
            "gui.widgets.account_posting_tab.QMessageBox.critical"
        ), patch(
            "gui.workers.posting_worker.traceback.print_exc"
        ):
            self.assertTrue(tab.start())
            loop.exec()
        self.assertEqual(tab._completion_status, "Lỗi")
        self.assertTrue(tab.start_button.isEnabled())

    def test_stop_button_waits_for_current_post_and_keeps_result(self) -> None:
        source = self._source_image()
        listing = self.listing_service.create_listing(
            title="Phòng cần dừng",
            location="Hà Nội",
            price=2_000_000,
            image_paths=[source],
        )
        group = self.group_service.create_group(
            "https://facebook.com/groups/stop-test",
            "Nhóm kiểm tra dừng",
        )

        class StoppableService:
            def run_plan(
                self,
                session_path,
                plan,
                progress_callback,
                result_callback,
                stop_requested,
            ):
                progress_callback(
                    PostingProgress(
                        completed=0,
                        total=2,
                        current_group_name=group.name,
                        next_group_name=group.name,
                        current_listing_title=listing.title,
                        message="Đang đăng bài hiện tại",
                        remaining=2,
                    )
                )
                time.sleep(0.05)
                entry = PostingResultEntry(
                    plan.account_name,
                    listing.id,
                    listing.title,
                    PostResult(
                        group.url,
                        group.name,
                        True,
                        f"{group.url}/posts/1",
                    ),
                )
                result_callback(entry)
                progress_callback(
                    PostingProgress(
                        completed=1,
                        total=2,
                        current_group_name=None,
                        next_group_name=None,
                        current_listing_title=None,
                        message="Đã dừng theo yêu cầu sau 1/2 lượt",
                        attempted=1,
                        remaining=1,
                        finished=True,
                        stopped=stop_requested(),
                    )
                )
                return [entry]

        tab = AccountPostingTab(
            "acc01",
            self.listing_service,
            self.group_service,
            worker_factory=lambda session_path, plan: PostingWorker(
                session_path,
                plan,
                posting_service=StoppableService(),
            ),
        )
        tab.tasks.append(
            ListingPostingTask(
                listing.id,
                listing.title,
                [GroupTarget(group.url, 2)],
                {group.url: group.name},
            )
        )
        tab._render_queue()
        loop = QEventLoop()
        tab.running_changed.connect(
            lambda _account, running: loop.quit() if not running else None
        )
        with patch(
            "gui.widgets.account_posting_tab.get_session",
            return_value=self.root,
        ):
            self.assertTrue(tab.start())
            QTimer.singleShot(10, tab.stop)
            loop.exec()

        self.assertEqual(tab._completion_status, "Đã dừng")
        self.assertEqual(len(tab.result_entries), 1)
        self.assertFalse(tab.stop_button.isEnabled())
        self.assertEqual(tab.stop_button.text(), "Dừng đăng bài")
        self.assertIn("Đã nhận yêu cầu dừng", tab.log_output.toPlainText())


if __name__ == "__main__":
    unittest.main()
