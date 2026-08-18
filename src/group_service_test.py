import tempfile
import unittest

from pathlib import Path

from services.group_asset_manager import GroupAssetManager
from services.group_repository import GroupRepository
from services.group_service import GroupService


class GroupServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.service = GroupService(
            GroupRepository(root / "groups.json"),
            GroupAssetManager(root / "groups"),
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_crud_normalization_stable_ids_and_image_cache(self) -> None:
        first = self.service.create_group(
            "facebook.com/groups/123?ref=share",
            "Nhóm một",
            image_data=b"image-bytes",
            image_extension=".jpg",
        )
        second = self.service.create_group(
            "https://m.facebook.com/groups/nha-tro/",
            "Nhóm hai",
        )

        self.assertEqual(first.id, "G001")
        self.assertEqual(second.id, "G002")
        self.assertEqual(
            first.url,
            "https://www.facebook.com/groups/123",
        )
        cached = self.service.get_image_path(
            self.service.get_by_id("G001")
        )
        self.assertIsNotNone(cached)
        self.assertEqual(cached.read_bytes(), b"image-bytes")

        updated = self.service.update_group(
            "G002",
            url=second.url,
            name="Nhóm hai đã sửa",
            enabled=False,
        )
        self.assertFalse(updated.enabled)
        self.assertTrue(self.service.delete_group("G001"))
        third = self.service.create_group(
            "https://facebook.com/groups/789",
            "Nhóm ba",
        )
        self.assertEqual(third.id, "G003")

    def test_image_error_does_not_discard_group(self) -> None:
        group = self.service.create_group(
            "https://facebook.com/groups/123",
            "Nhóm vẫn được lưu",
            image_data=b"bytes",
            image_extension=".bmp",
        )
        self.assertEqual(group.id, "G001")
        self.assertIsNone(group.image_path)
        self.assertIsNotNone(self.service.last_image_error)
        self.assertEqual(self.service.get_all(), [group])

    def test_rejects_non_group_or_duplicate_url(self) -> None:
        with self.assertRaisesRegex(ValueError, "facebook.com"):
            self.service.create_group(
                "https://example.com/groups/1",
                "Sai host",
            )
        self.service.create_group(
            "https://facebook.com/groups/123",
            "Nhóm một",
        )
        with self.assertRaisesRegex(ValueError, "đã được lưu"):
            self.service.create_group(
                "https://www.facebook.com/groups/123?ref=share",
                "Bị trùng",
            )
