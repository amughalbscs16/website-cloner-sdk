"""Network-mocked tests for the ResourceDownloader fallback chain and file saving"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.utils.file_utils import FileManager
from src.downloaders.resource_downloader import ResourceDownloader


def make_downloader(tmp_path: Path, **kwargs) -> ResourceDownloader:
    return ResourceDownloader(FileManager(tmp_path), **kwargs)


class TestDownloadFallbackChain:
    """The requests -> urllib3 -> httpx fallback chain, fully mocked"""

    def test_requests_success_short_circuits(self):
        with tempfile.TemporaryDirectory() as tmp:
            downloader = make_downloader(Path(tmp))
            response = MagicMock(content=b"payload")

            with patch.object(downloader, "download_with_requests", return_value=response) as r, \
                 patch.object(downloader, "download_with_urllib") as u, \
                 patch.object(downloader, "download_with_httpx") as h:
                content, method = downloader.download_resource("https://example.com/a.css")

            assert content == b"payload"
            assert method == "requests"
            u.assert_not_called()
            h.assert_not_called()

    def test_falls_back_to_urllib3_when_requests_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            downloader = make_downloader(Path(tmp))
            response = MagicMock(data=b"payload")

            with patch.object(downloader, "download_with_requests", return_value=None), \
                 patch.object(downloader, "download_with_urllib", return_value=response):
                content, method = downloader.download_resource("https://example.com/a.css")

            assert content == b"payload"
            assert method == "urllib3"

    def test_falls_back_to_httpx_last(self):
        with tempfile.TemporaryDirectory() as tmp:
            downloader = make_downloader(Path(tmp))
            response = MagicMock(content=b"payload")

            with patch.object(downloader, "download_with_requests", return_value=None), \
                 patch.object(downloader, "download_with_urllib", return_value=None), \
                 patch.object(downloader, "download_with_httpx", return_value=response):
                content, method = downloader.download_resource("https://example.com/a.css")

            assert content == b"payload"
            assert method == "httpx"

    def test_all_methods_fail_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            downloader = make_downloader(Path(tmp))

            with patch.object(downloader, "download_with_requests", return_value=None), \
                 patch.object(downloader, "download_with_urllib", return_value=None), \
                 patch.object(downloader, "download_with_httpx", return_value=None):
                content, method = downloader.download_resource("https://example.com/a.css")

            assert content is None
            assert method is None


class TestDownloadFile:
    """download_file behavior with the network mocked out"""

    def test_successful_download_saves_file_and_tracks_stats(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            downloader = make_downloader(project)

            with patch.object(downloader, "download_resource", return_value=(b"body{}", "requests")):
                local = downloader.download_file(
                    "https://example.com", "https://example.com/style.css", project
                )

            assert downloader.download_stats["success"] == 1
            assert downloader.successful_downloads[0]["url"] == "https://example.com/style.css"
            assert downloader.successful_downloads[0]["method"] == "requests"
            saved = project / Path(local)
            assert saved.read_bytes() == b"body{}"

    def test_repeat_url_is_skipped_via_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            downloader = make_downloader(project)

            with patch.object(downloader, "download_resource", return_value=(b"x", "requests")):
                first = downloader.download_file("https://example.com", "https://example.com/a.js", project)
                second = downloader.download_file("https://example.com", "https://example.com/a.js", project)

            assert first == second
            assert downloader.download_stats["success"] == 1
            assert downloader.download_stats["skipped"] == 1

    def test_failed_download_records_reason_and_returns_original_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            downloader = make_downloader(project)

            with patch.object(downloader, "download_resource", return_value=(None, None)):
                result = downloader.download_file(
                    "https://example.com", "https://example.com/missing.png", project
                )

            assert result == "https://example.com/missing.png"
            assert downloader.download_stats["failed"] == 1
            assert downloader.failed_downloads[0]["url"] == "https://example.com/missing.png"

    def test_data_uri_is_passed_through_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            downloader = make_downloader(project)
            uri = "data:image/png;base64,iVBORw0KGgo="

            result = downloader.download_file("https://example.com", uri, project)

            assert result == uri
            assert downloader.download_stats == {"success": 0, "failed": 0, "skipped": 0}

    def test_empty_url_is_passed_through(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            downloader = make_downloader(project)

            assert downloader.download_file("https://example.com", "", project) == ""
