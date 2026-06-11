"""WACZ packaging round-trip test (skipped when py-wacz is unavailable)"""

import importlib.util
import tempfile
import zipfile
from pathlib import Path

import pytest

from src.drivers.cdp_capture import CapturedResource
from src.exporters.warc_exporter import WarcExporter
from src.exporters.wacz_exporter import WaczExporter

wacz_available = importlib.util.find_spec("wacz") is not None


@pytest.mark.skipif(not wacz_available, reason="py-wacz not installed")
def test_warc_packages_into_valid_wacz():
    resources = {
        "https://example.com/": CapturedResource(
            url="https://example.com/",
            content=b"<html><body>hello</body></html>",
            status=200,
            mime_type="text/html",
            headers={"Content-Type": "text/html"},
        )
    }

    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        warc_path = WarcExporter().export(project, "https://example.com/", resources)
        assert warc_path is not None

        wacz_path = WaczExporter().export(warc_path, "https://example.com/")
        assert wacz_path is not None and wacz_path.exists()

        with zipfile.ZipFile(wacz_path) as z:
            names = z.namelist()
            assert "datapackage.json" in names
            assert any(n.startswith("archive/") for n in names)
            assert any(n.startswith("indexes/") for n in names)
