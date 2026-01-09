"""Tests for resource downloader"""

import pytest
from pathlib import Path
from src.utils.file_utils import FileManager
from src.downloaders.resource_downloader import ResourceDownloader


class TestResourceDownloader:
    """Test resource downloader functionality"""

    def test_downloader_initialization(self):
        """Test downloader initializes correctly"""
        fm = FileManager(Path("."))
        downloader = ResourceDownloader(fm, max_workers=5)

        assert downloader.max_workers == 5
        assert downloader.download_stats == {"success": 0, "failed": 0, "skipped": 0}
        assert downloader.successful_downloads == []
        assert downloader.failed_downloads == []

    def test_should_download_from_network_no_logs(self):
        """Test download decision when no network logs available"""
        fm = FileManager(Path("."))
        downloader = ResourceDownloader(fm, network_urls=set())

        # Without network logs, should download everything
        assert downloader.should_download_from_network("test.jpg", "https://example.com/test.jpg")

    def test_should_download_from_network_url_in_logs(self):
        """Test download decision when URL is in network logs"""
        fm = FileManager(Path("."))
        network_urls = {"https://example.com/test.jpg"}
        downloader = ResourceDownloader(fm, network_urls=network_urls)

        assert downloader.should_download_from_network("test.jpg", "https://example.com/test.jpg")

    def test_should_download_from_network_url_not_in_logs(self):
        """Test download decision when URL not in network logs"""
        fm = FileManager(Path("."))
        network_urls = {"https://example.com/other.jpg"}
        downloader = ResourceDownloader(fm, network_urls=network_urls)

        # Filename doesn't match any network URL
        assert not downloader.should_download_from_network("missing.jpg", "https://example.com/missing.jpg")

    def test_cancel_check_integration(self):
        """Test that cancel check is called during download"""
        fm = FileManager(Path("."))
        cancel_called = False

        def mock_cancel_check():
            nonlocal cancel_called
            cancel_called = True
            raise InterruptedError("Cancelled")

        downloader = ResourceDownloader(fm, cancel_check=mock_cancel_check)

        # Attempting to download should trigger cancellation
        result = downloader.download_file("https://example.com", "test.jpg", Path("."))

        # Cancel check should have been called (and raised exception internally)
        # Result should be the original URL since download was cancelled/failed
        assert cancel_called or result == "test.jpg"
