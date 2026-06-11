"""Round-trip tests for WARC export: write records, read them back, verify"""

import tempfile
from pathlib import Path

from warcio.archiveiterator import ArchiveIterator

from src.drivers.cdp_capture import CapturedResource
from src.exporters.warc_exporter import WarcExporter


def sample_resources():
    return {
        "https://example.com/": CapturedResource(
            url="https://example.com/",
            content=b"<html><body>hi</body></html>",
            status=200,
            mime_type="text/html",
            headers={
                "Content-Type": "text/html; charset=utf-8",
                # CDP returns DECODED bodies; these must be stripped on write
                "Content-Encoding": "gzip",
                "Content-Length": "9999",
            },
        ),
        "https://example.com/app.js": CapturedResource(
            url="https://example.com/app.js",
            content=b"console.log(1)",
            status=200,
            mime_type="text/javascript",
            headers={"Content-Type": "text/javascript"},
        ),
    }


class TestWarcExporter:

    def test_round_trip_records_and_payloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            warc_path = WarcExporter().export(
                project, "https://example.com", sample_resources()
            )

            assert warc_path is not None and warc_path.exists()

            records = {}
            with open(warc_path, "rb") as stream:
                for record in ArchiveIterator(stream):
                    if record.rec_type == "warcinfo":
                        records["warcinfo"] = True
                    elif record.rec_type == "response":
                        uri = record.rec_headers.get_header("WARC-Target-URI")
                        records[uri] = record.content_stream().read()

            assert records.get("warcinfo")
            assert records["https://example.com/"] == b"<html><body>hi</body></html>"
            assert records["https://example.com/app.js"] == b"console.log(1)"

    def test_stale_encoding_headers_are_stripped(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            warc_path = WarcExporter().export(
                project, "https://example.com", sample_resources()
            )

            with open(warc_path, "rb") as stream:
                for record in ArchiveIterator(stream):
                    if record.rec_type != "response":
                        continue
                    http = record.http_headers
                    assert http.get_header("Content-Encoding") is None
                    assert http.get_header("Transfer-Encoding") is None
                    # Content-Length must match the actual decoded payload
                    body = record.content_stream().read()
                    assert int(http.get_header("Content-Length")) == len(body)

    def test_empty_capture_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            assert WarcExporter().export(Path(tmp), "https://example.com", {}) is None
