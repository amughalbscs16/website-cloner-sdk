"""Tests for CDP response capture: log parsing, body decoding, cdp-first downloads"""

import base64
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.drivers.chrome_driver import ChromeDriverManager
from src.drivers.cdp_capture import CapturedResource, harvest_captured_resources
from src.downloaders.resource_downloader import ResourceDownloader
from src.utils.file_utils import FileManager


def perf_entry(method: str, params: dict) -> dict:
    """Build a performance-log entry as ChromeDriver returns them"""
    return {"message": json.dumps({"message": {"method": method, "params": params}})}


def make_fake_driver(log_entries):
    driver = MagicMock()
    driver.get_log.return_value = log_entries
    return driver


class TestHarvestNetwork:
    """Performance-log parsing into request URLs + response metadata"""

    def setup_method(self):
        self.manager = ChromeDriverManager.__new__(ChromeDriverManager)
        self.manager.driver = None

    def test_collects_request_urls_and_response_metadata(self):
        driver = make_fake_driver([
            perf_entry("Network.requestWillBeSent", {
                "request": {"url": "https://example.com/app.js"}
            }),
            perf_entry("Network.responseReceived", {
                "requestId": "req-1",
                "type": "Script",
                "response": {
                    "url": "https://example.com/app.js",
                    "status": 200,
                    "headers": {"Content-Type": "text/javascript"},
                    "mimeType": "text/javascript",
                },
            }),
        ])

        urls, responses = self.manager.harvest_network(driver)

        assert urls == {"https://example.com/app.js"}
        meta = responses["https://example.com/app.js"]
        assert meta["request_id"] == "req-1"
        assert meta["status"] == 200
        assert meta["mime_type"] == "text/javascript"
        assert meta["resource_type"] == "Script"

    def test_ignores_non_http_responses_and_malformed_entries(self):
        driver = make_fake_driver([
            perf_entry("Network.responseReceived", {
                "requestId": "req-2",
                "response": {"url": "data:text/css,body{}", "status": 200},
            }),
            {"message": "not-json"},
            perf_entry("Page.loadEventFired", {}),
        ])

        urls, responses = self.manager.harvest_network(driver)

        assert urls == set()
        assert responses == {}

    def test_no_driver_returns_empty(self):
        urls, responses = self.manager.harvest_network(None)
        assert urls == set()
        assert responses == {}


class TestGetResponseBody:
    """CDP body retrieval with base64 and eviction handling"""

    def setup_method(self):
        self.manager = ChromeDriverManager.__new__(ChromeDriverManager)
        self.manager.driver = None

    def test_plain_text_body(self):
        driver = MagicMock()
        driver.execute_cdp_cmd.return_value = {"body": "hello", "base64Encoded": False}

        assert self.manager.get_response_body("req-1", driver) == b"hello"
        driver.execute_cdp_cmd.assert_called_once_with(
            "Network.getResponseBody", {"requestId": "req-1"}
        )

    def test_base64_body_is_decoded(self):
        driver = MagicMock()
        raw = b"\x89PNG\r\n"
        driver.execute_cdp_cmd.return_value = {
            "body": base64.b64encode(raw).decode(),
            "base64Encoded": True,
        }

        assert self.manager.get_response_body("req-1", driver) == raw

    def test_evicted_body_returns_none(self):
        driver = MagicMock()
        driver.execute_cdp_cmd.side_effect = Exception("No data found for resource")

        assert self.manager.get_response_body("req-1", driver) is None

    def test_missing_request_id_returns_none(self):
        assert self.manager.get_response_body(None, MagicMock()) is None


class TestHarvestCapturedResources:
    """End-to-end harvest: responses -> CapturedResource dict with eviction fallback"""

    def test_captures_2xx_bodies_and_skips_evicted_and_errors(self):
        manager = MagicMock()
        manager.harvest_network.return_value = (
            {"https://example.com/a.js", "https://example.com/b.css",
             "https://example.com/missing.png", "https://example.com/404.html"},
            {
                "https://example.com/a.js": {
                    "request_id": "r1", "status": 200, "headers": {},
                    "mime_type": "text/javascript", "resource_type": "Script",
                },
                "https://example.com/b.css": {
                    "request_id": "r2", "status": 200, "headers": {},
                    "mime_type": "text/css", "resource_type": "Stylesheet",
                },
                "https://example.com/404.html": {
                    "request_id": "r3", "status": 404, "headers": {},
                    "mime_type": "text/html", "resource_type": "Document",
                },
            },
        )
        # a.js has a body; b.css was evicted
        manager.get_response_body.side_effect = lambda rid, d=None: (
            b"console.log(1)" if rid == "r1" else None
        )

        urls, captured = harvest_captured_resources(manager)

        assert len(urls) == 4
        assert set(captured) == {"https://example.com/a.js"}
        resource = captured["https://example.com/a.js"]
        assert resource.content == b"console.log(1)"
        assert resource.mime_type == "text/javascript"


class TestCdpFirstDownload:
    """ResourceDownloader must prefer CDP-captured bytes over re-fetching"""

    def test_captured_resource_used_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            captured = {
                "https://example.com/app.js": CapturedResource(
                    url="https://example.com/app.js",
                    content=b"captured-bytes",
                    mime_type="text/javascript",
                )
            }
            downloader = ResourceDownloader(
                FileManager(project), captured_resources=captured
            )

            with patch.object(downloader, "download_with_requests") as refetch:
                local = downloader.download_file(
                    "https://example.com", "https://example.com/app.js", project
                )

            refetch.assert_not_called()
            assert downloader.successful_downloads[0]["method"] == "cdp"
            assert (project / Path(local)).read_bytes() == b"captured-bytes"

    def test_uncaptured_url_falls_back_to_refetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            downloader = ResourceDownloader(FileManager(project), captured_resources={})
            response = MagicMock(content=b"refetched")

            with patch.object(downloader, "download_with_requests", return_value=response):
                downloader.download_file(
                    "https://example.com", "https://example.com/other.js", project
                )

            assert downloader.successful_downloads[0]["method"] == "requests"

    def test_capture_method_stats_breakdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            captured = {
                "https://example.com/a.js": CapturedResource(
                    url="https://example.com/a.js", content=b"a"
                )
            }
            downloader = ResourceDownloader(
                FileManager(project), captured_resources=captured
            )
            response = MagicMock(content=b"b")

            with patch.object(downloader, "download_with_requests", return_value=response):
                downloader.download_file("https://example.com", "https://example.com/a.js", project)
                downloader.download_file("https://example.com", "https://example.com/b.js", project)

            assert downloader.capture_method_stats == {"cdp": 1, "requests": 1}
