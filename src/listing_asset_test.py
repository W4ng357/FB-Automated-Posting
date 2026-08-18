import tempfile
import unittest

from pathlib import Path

from services.listing_asset_manager import ListingAssetManager


class ListingAssetManagerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.manager = ListingAssetManager(self.root / "listings")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_add_list_delete_and_cleanup_images(self) -> None:
        first = self.root / "first.jpg"
        second = self.root / "second.png"
        first.write_bytes(b"first")
        second.write_bytes(b"second")

        imported = self.manager.add_images(
            "R001",
            [first, second],
        )
        self.assertEqual(
            [path.name for path in imported],
            ["001.jpg", "002.png"],
        )
        self.assertEqual(self.manager.get_images("R001"), imported)
        self.assertTrue(self.manager.delete_image("R001", "001.jpg"))
        self.assertEqual(
            [path.name for path in self.manager.get_images("R001")],
            ["002.png"],
        )
        self.assertTrue(self.manager.delete_listing_assets("R001"))
        self.assertFalse(self.manager.get_listing_dir("R001").exists())


if __name__ == "__main__":
    unittest.main()
