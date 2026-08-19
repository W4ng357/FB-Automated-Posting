import io
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from services.update_service import ReleaseInfo, UpdateService
from version import is_newer_version, parse_version


class VersionTest(unittest.TestCase):
    def test_parse_version(self) -> None:
        self.assertEqual(parse_version("1.0.0"), (1, 0, 0))
        self.assertEqual(parse_version("v1.2.3"), (1, 2, 3))
        self.assertEqual(parse_version("V2.0"), (2, 0))
        self.assertEqual(parse_version("v1.0.1-alpha"), (1, 0, 1))
        self.assertEqual(parse_version(""), (0,))

    def test_is_newer_version(self) -> None:
        self.assertTrue(is_newer_version("v1.0.1", "v1.0.0"))
        self.assertTrue(is_newer_version("1.1.0", "1.0.9"))
        self.assertTrue(is_newer_version("2.0.0", "1.9.9"))
        self.assertFalse(is_newer_version("1.0.0", "1.0.0"))
        self.assertFalse(is_newer_version("1.0.0", "1.0.1"))
        self.assertFalse(is_newer_version("0.9.9", "1.0.0"))


class UpdateServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.test_dir = Path(tempfile.mkdtemp())
        self.updates_dir = self.test_dir / "updates"
        self.current_dir = self.updates_dir / "current"
        self.temp_dir = self.updates_dir / "temp"

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch("services.update_service.CURRENT_UPDATE_DIR")
    def test_get_current_installed_version(self, mock_current_dir: Path) -> None:
        mock_current_dir.__truediv__.return_value = self.current_dir / "update_manifest.json"
        service = UpdateService()
        self.assertEqual(service.get_current_installed_version(), "1.0.0")

        self.current_dir.mkdir(parents=True, exist_ok=True)
        manifest = self.current_dir / "update_manifest.json"
        manifest.write_text(json.dumps({"version": "v1.2.3"}), encoding="utf-8")
        mock_current_dir.is_dir.return_value = True

        # Now reads from manifest
        with patch.object(Path, "is_file", return_value=True), \
             patch.object(Path, "read_text", return_value='{"version": "v1.2.3"}'):
            self.assertEqual(service.get_current_installed_version(), "v1.2.3")

    @patch("urllib.request.urlopen")
    def test_check_for_updates_found(self, mock_urlopen) -> None:
        fake_payload = {
            "tag_name": "v1.0.1",
            "name": "Bản cập nhật v1.0.1",
            "body": "Nội dung cập nhật tính năng mới",
            "published_at": "2026-08-20T00:00:00Z",
            "html_url": "https://github.com/W4ng357/FB-Automated-Posting/releases/tag/v1.0.1",
            "assets": [
                {
                    "name": "app_code.zip",
                    "browser_download_url": "https://example.com/app_code.zip",
                    "size": 102400,
                }
            ],
            "zipball_url": "https://example.com/zipball.zip",
        }
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps(fake_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        service = UpdateService()
        with patch.object(service, "get_current_installed_version", return_value="1.0.0"):
            release = service.check_for_updates()
            self.assertIsNotNone(release)
            self.assertEqual(release.version, "v1.0.1")
            self.assertEqual(release.code_zip_url, "https://example.com/app_code.zip")
            self.assertEqual(release.file_size, 102400)

    @patch("urllib.request.urlopen")
    def test_check_for_updates_no_newer_version(self, mock_urlopen) -> None:
        fake_payload = {
            "tag_name": "v1.0.0",
            "name": "Bản phát hành v1.0.0",
        }
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps(fake_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        service = UpdateService()
        with patch.object(service, "get_current_installed_version", return_value="1.0.0"):
            release = service.check_for_updates()
            self.assertIsNone(release)

    @patch("services.update_service.UPDATES_DIR")
    @patch("services.update_service.CURRENT_UPDATE_DIR")
    @patch("services.update_service.TEMP_UPDATE_DIR")
    @patch("urllib.request.urlopen")
    def test_download_and_apply_update(
        self,
        mock_urlopen,
        mock_temp_dir: Path,
        mock_current_dir: Path,
        mock_updates_dir: Path,
    ) -> None:
        mock_updates_dir.__truediv__.side_effect = lambda x: self.updates_dir / x
        mock_updates_dir.mkdir.side_effect = lambda **kwargs: self.updates_dir.mkdir(parents=True, exist_ok=True)
        mock_temp_dir.mkdir.side_effect = lambda **kwargs: self.temp_dir.mkdir(parents=True, exist_ok=True)
        mock_temp_dir.__truediv__.side_effect = lambda x: self.temp_dir / x

        # Create dummy update zip content
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("version.py", 'APP_VERSION = "1.0.1"')
            zf.writestr("test_module.py", 'print("Updated!")')
        zip_bytes = zip_buf.getvalue()

        mock_resp = MagicMock()
        mock_resp.headers = {"Content-Length": str(len(zip_bytes))}
        mock_resp.read.side_effect = [zip_bytes, b""]
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        release = ReleaseInfo(
            version="v1.0.1",
            name="v1.0.1",
            body="Changelog",
            published_at="",
            html_url="",
            code_zip_url="https://example.com/app_code.zip",
            file_size=len(zip_bytes),
        )

        progress_called = []
        def progress(d, t):
            progress_called.append((d, t))

        service = UpdateService()
        with patch("services.update_service.CURRENT_UPDATE_DIR", self.current_dir):
            success = service.download_and_apply_update(release, progress_callback=progress)
            self.assertTrue(success)
            self.assertTrue((self.current_dir / "version.py").is_file())
            self.assertTrue((self.current_dir / "update_manifest.json").is_file())
            self.assertTrue(len(progress_called) > 0)


if __name__ == "__main__":
    unittest.main()
