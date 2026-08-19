import tempfile
import unittest

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import post
from models.listing import Listing
from services.caption_generator import format_price, generate_caption
from services.listing_asset_manager import ListingAssetManager
from services.listing_repository import ListingRepository
from services.listing_service import ListingService


class ListingServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.repository = ListingRepository(
            self.root / "listings.json"
        )
        self.asset_manager = ListingAssetManager(
            self.root / "listing-assets"
        )
        self.service = ListingService(
            repository=self.repository,
            asset_manager=self.asset_manager,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def create_source_image(
        self,
        name: str,
        content: bytes = b"test-image",
    ) -> Path:
        source_dir = self.root / "source-images"
        source_dir.mkdir(exist_ok=True)
        source_path = source_dir / name
        source_path.write_bytes(content)
        return source_path

    def test_create_read_update_caption_and_prepare(self) -> None:
        first_image = self.create_source_image(
            "room.jpg"
        )
        second_image = self.create_source_image(
            "kitchen.png"
        )

        created = self.service.create_listing(
            title="Phòng trọ Thanh Xuân",
            location="Thanh Xuân",
            price=3_500_000,
            address="Nguyễn Trãi, Hà Nội",
            area=25,
            description="Phòng sạch đẹp",
            contact="0123456789",
            image_paths=[first_image, second_image],
        )

        self.assertEqual(created.id, "R001")
        self.assertEqual(
            self.service.get_by_id("R001"),
            created,
        )

        updated = self.service.update_listing(
            "R001",
            price=3_700_000,
            area=27,
        )

        self.assertEqual(updated.price, 3_700_000)
        self.assertEqual(updated.area, 27)

        images = self.service.get_images("R001")
        self.assertEqual(
            [image.name for image in images],
            ["001.jpg", "002.png"],
        )

        caption, prepared_images = (
            self.service.prepare_for_posting("R001")
        )

        self.assertIn(
            "💰 Giá: 3,7TR/tháng",
            caption,
        )
        self.assertIn("📐 Diện tích: 27m²", caption)
        self.assertEqual(prepared_images, images)
        self.assertEqual(
            self.service.generate_caption("R001"),
            caption,
        )

    def test_caption_omits_empty_optional_fields(self) -> None:
        listing = Listing(
            id="R001",
            title="",
            location="Cầu Giấy",
            price=2_500_000,
            price_unit="tr",
        )

        caption = generate_caption(listing)

        self.assertEqual(
            caption,
            (
                "📍 Địa chỉ: Cầu Giấy\n"
                "💰 Giá: 2,5tr/tháng"
            ),
        )

    def test_price_uses_compact_million_format(self) -> None:
        self.assertEqual(format_price(3_500_000), "3,5TR")
        self.assertEqual(format_price(4_000_000), "4TR")
        self.assertEqual(format_price(7_000_000), "7TR")
        self.assertEqual(format_price(3_050_000), "3,05TR")
        self.assertEqual(format_price(3_200_000, "Triệu"), "3,2 Triệu")
        self.assertEqual(format_price(3_200_000, "Tr"), "3,2Tr")
        self.assertEqual(format_price(3_200_000, "tr"), "3,2tr")

    def test_image_number_uses_highest_existing_stem(self) -> None:
        sources = [
            self.create_source_image("a.jpg", b"a"),
            self.create_source_image("b.jpg", b"b"),
            self.create_source_image("c.png", b"c"),
        ]
        listing = self.service.create_listing(
            title="Phòng trọ",
            location="Hà Nội",
            price=2_000_000,
            image_paths=sources,
        )

        self.assertTrue(
            self.service.remove_image(
                listing.id,
                "002.jpg",
            )
        )

        fourth_source = self.create_source_image(
            "d.jpg",
            b"d",
        )
        added = self.service.add_images(
            listing.id,
            [fourth_source],
        )

        self.assertEqual(added[0].name, "004.jpg")
        self.assertEqual(
            [
                image.name
                for image in self.service.get_images(
                    listing.id
                )
            ],
            ["001.jpg", "003.png", "004.jpg"],
        )

    def test_create_rolls_back_invalid_image(self) -> None:
        unsupported_file = self.create_source_image(
            "notes.txt"
        )

        with self.assertRaisesRegex(
            ValueError,
            "Định dạng ảnh chưa được hỗ trợ",
        ):
            self.service.create_listing(
                title="Phòng trọ",
                location="Hà Nội",
                price=2_000_000,
                image_paths=[unsupported_file],
            )

        self.assertEqual(self.service.get_all(), [])
        self.assertFalse(
            self.asset_manager
            .get_listing_dir("R001")
            .exists()
        )

    def test_existing_listing_is_required_for_assets(self) -> None:
        source = self.create_source_image("room.jpg")

        with self.assertRaisesRegex(
            KeyError,
            "Không tìm thấy phòng R999",
        ):
            self.service.add_images("R999", [source])

        with self.assertRaisesRegex(
            KeyError,
            "Không tìm thấy phòng R999",
        ):
            self.service.get_images("R999")

        with self.assertRaisesRegex(
            KeyError,
            "Không tìm thấy phòng R999",
        ):
            self.service.delete_listing("R999")

    def test_prepare_rejects_disabled_or_imageless_listing(self) -> None:
        disabled = self.service.create_listing(
            title="Phòng đã ẩn",
            location="Hà Nội",
            price=2_000_000,
            enabled=False,
        )

        with self.assertRaisesRegex(
            ValueError,
            "đang bị ẩn",
        ):
            self.service.prepare_for_posting(disabled.id)

        enabled = self.service.create_listing(
            title="Phòng chưa có ảnh",
            location="Hà Nội",
            price=2_000_000,
        )

        with self.assertRaisesRegex(
            ValueError,
            "chưa có ảnh",
        ):
            self.service.prepare_for_posting(enabled.id)

    def test_delete_can_preserve_or_remove_assets(self) -> None:
        source = self.create_source_image("room.jpg")
        preserved = self.service.create_listing(
            title="Phòng giữ ảnh",
            location="Hà Nội",
            price=2_000_000,
            image_paths=[source],
        )
        preserved_dir = (
            self.asset_manager.get_listing_dir(
                preserved.id
            )
        )

        self.assertTrue(
            self.service.delete_listing(
                preserved.id,
                delete_images=False,
            )
        )
        self.assertTrue(preserved_dir.is_dir())

        next_listing = self.service.create_listing(
            title="Phòng mới",
            location="Hà Nội",
            price=2_100_000,
        )
        self.assertEqual(next_listing.id, "R002")
        self.assertEqual(
            self.service.get_images(next_listing.id),
            [],
        )

        other_repository = ListingRepository(
            self.root / "other-listings.json"
        )
        other_assets = ListingAssetManager(
            self.root / "other-assets"
        )
        other_service = ListingService(
            other_repository,
            other_assets,
        )
        removed = other_service.create_listing(
            title="Phòng xóa ảnh",
            location="Hà Nội",
            price=2_000_000,
            image_paths=[source],
        )
        removed_dir = other_assets.get_listing_dir(
            removed.id
        )

        self.assertTrue(
            other_service.delete_listing(
                removed.id,
                delete_images=True,
            )
        )
        self.assertFalse(removed_dir.exists())

    def test_invalid_model_data_and_id_update_are_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Giá thuê không được là số âm",
        ):
            self.service.create_listing(
                title="Phòng trọ",
                location="Hà Nội",
                price=-1,
            )

        with self.assertRaisesRegex(
            ValueError,
            "Diện tích phải lớn hơn 0",
        ):
            self.service.create_listing(
                title="Phòng trọ",
                location="Hà Nội",
                price=1,
                area=0,
            )

        listing = self.service.create_listing(
            title="Phòng trọ",
            location="Hà Nội",
            price=1,
        )

        with self.assertRaisesRegex(
            ValueError,
            "Không thể thay đổi mã phòng",
        ):
            self.service.update_listing(
                listing.id,
                id="R999",
            )

    def test_malformed_json_has_clear_error(self) -> None:
        self.repository.file_path.write_text(
            "{not valid JSON",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(
            ValueError,
            "Tệp danh sách phòng có JSON không hợp lệ",
        ):
            self.repository.get_all()

    def test_empty_json_and_missing_image_are_handled(self) -> None:
        self.repository.file_path.write_text(
            "   \n",
            encoding="utf-8",
        )
        self.assertEqual(self.repository.get_all(), [])

        listing = self.service.create_listing(
            title="Phòng trọ",
            location="Hà Nội",
            price=1,
        )

        with self.assertRaisesRegex(
            FileNotFoundError,
            "Không tìm thấy ảnh",
        ):
            self.service.add_images(
                listing.id,
                [self.root / "missing.jpg"],
            )

    def test_asset_paths_cannot_escape_configured_directory(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Mã phòng không hợp lệ",
        ):
            self.asset_manager.delete_listing_assets(
                "../outside"
            )

        listing = self.service.create_listing(
            title="Phòng trọ",
            location="Hà Nội",
            price=1,
        )

        with self.assertRaisesRegex(
            ValueError,
            "Tên ảnh không hợp lệ",
        ):
            self.service.remove_image(
                listing.id,
                "../outside.jpg",
            )


class PostCliTest(unittest.TestCase):
    @patch("post.post_summary")
    @patch("post.post_to_groups")
    @patch("post.ListingService")
    @patch("post.get_session")
    @patch("post.parse_args")
    def test_cli_prepares_listing_and_calls_posting_engine(
        self,
        parse_args_mock,
        get_session_mock,
        service_class_mock,
        post_to_groups_mock,
        post_summary_mock,
    ) -> None:
        parse_args_mock.return_value = SimpleNamespace(
            account="acc01",
            listing_id="R001",
            group=[
                ["https://facebook.com/groups/123", "2"],
                ["https://facebook.com/groups/456", "1"],
            ],
        )
        session_path = Path("/tmp/test-session")
        get_session_mock.return_value = session_path

        listing = Listing(
            id="R001",
            title="Phòng trọ",
            location="Hà Nội",
            price=2_000_000,
        )
        images = [Path("/tmp/001.jpg")]
        service = service_class_mock.return_value
        service.get_by_id.return_value = listing
        service.prepare_for_posting.return_value = (
            "Generated caption",
            images,
        )
        results = []
        post_to_groups_mock.return_value = results

        post.main()

        get_session_mock.assert_called_once_with("acc01")
        service.get_by_id.assert_called_once_with("R001")
        service.prepare_for_posting.assert_called_once_with(
            "R001"
        )

        call_arguments = post_to_groups_mock.call_args.kwargs
        self.assertEqual(
            call_arguments["session_path"],
            session_path,
        )
        self.assertEqual(
            call_arguments["caption"],
            "Generated caption",
        )
        self.assertEqual(
            call_arguments["image_paths"],
            images,
        )
        self.assertEqual(
            [
                target.target_count
                for target in call_arguments[
                    "group_targets"
                ]
            ],
            [2, 1],
        )
        post_summary_mock.assert_called_once_with(results)


if __name__ == "__main__":
    unittest.main()
