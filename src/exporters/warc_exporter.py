"""WARC export for CDP-captured resources.

Writes ISO 28500 WARC files from the response bodies captured in-browser,
making clones ingestible by standard archival tooling (pywb, ReplayWeb.page).
Only CDP-captured resources are written: those are the bytes the browser
actually received. Re-fetched resources are excluded because their bytes were
not observed in the browser session.
"""

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Dict, Optional

from warcio.statusandheaders import StatusAndHeaders
from warcio.warcwriter import WARCWriter

from ..utils.logger import logger

# CDP's Network.getResponseBody returns the DECODED body, so encoding and
# length headers from the original response would corrupt replay if kept
_STRIP_HEADERS = {"content-encoding", "content-length", "transfer-encoding"}


class WarcExporter:
    """Writes CDP-captured resources to a gzipped WARC file"""

    def __init__(self, software: str = "website-cloner-sdk/2.0.0"):
        self.software = software

    def export(
        self,
        project_path: Path,
        page_url: str,
        captured_resources: Dict,
        filename: str = "capture.warc.gz",
    ) -> Optional[Path]:
        """
        Write captured resources to a WARC file inside the project directory.

        Args:
            project_path: Clone output directory
            page_url: URL of the cloned page (recorded in warcinfo)
            captured_resources: dict url -> CapturedResource (CDP bodies)
            filename: Output WARC filename

        Returns:
            Path to the WARC file, or None if nothing was written
        """
        if not captured_resources:
            logger.info("WARC export skipped: no CDP-captured resources")
            return None

        warc_path = project_path / filename
        records = 0

        try:
            with open(warc_path, "wb") as stream:
                writer = WARCWriter(stream, gzip=True)

                info = writer.create_warcinfo_record(filename, {
                    "software": self.software,
                    "format": "WARC File Format 1.1",
                    "description": f"Single-page browser capture of {page_url}",
                    "isPartOf": page_url,
                    "datetime": datetime.now(timezone.utc).isoformat(),
                })
                writer.write_record(info)

                for url, resource in captured_resources.items():
                    try:
                        writer.write_record(self._response_record(writer, url, resource))
                        records += 1
                    except Exception as e:
                        logger.warning(f"Skipped WARC record for {url}: {e}")

            logger.success(f"WARC export: {records} records -> {warc_path}")
            return warc_path

        except Exception as e:
            logger.error(f"WARC export failed: {e}")
            return None

    def _response_record(self, writer: WARCWriter, url: str, resource):
        """Build a WARC response record from a CapturedResource"""
        headers = [
            (name, value)
            for name, value in (resource.headers or {}).items()
            if name.lower() not in _STRIP_HEADERS
        ]
        headers.append(("Content-Length", str(len(resource.content))))

        status = resource.status or 200
        http_headers = StatusAndHeaders(
            f"{status} {'OK' if status == 200 else ''}".strip(),
            headers,
            protocol="HTTP/1.1",
        )

        return writer.create_warc_record(
            url,
            "response",
            payload=BytesIO(resource.content),
            http_headers=http_headers,
        )
