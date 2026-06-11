"""WACZ packaging via Webrecorder's py-wacz.

Wraps the official `wacz create` tool (subprocess, so internal API changes in
py-wacz don't break us) to package the exported WARC into a WACZ that loads
directly in ReplayWeb.page. Packaging is best-effort: if py-wacz is not
installed the clone still succeeds with file tree + WARC.
"""

import gzip
import hashlib
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Optional

from ..utils.logger import logger


class WaczExporter:
    """Packages a WARC file into a WACZ archive"""

    def export(
        self,
        warc_path: Path,
        page_url: str,
        filename: str = "capture.wacz",
    ) -> Optional[Path]:
        """
        Package a WARC into a WACZ next to it.

        Tries the official py-wacz tool first; falls back to a native
        packager because py-wacz writes backslash zip entry names on Windows,
        which Python's zipfile (3.12+) rejects as corrupt.

        Args:
            warc_path: Path to the .warc.gz produced by WarcExporter
            page_url: URL of the captured page (becomes the WACZ entry page)
            filename: Output WACZ filename

        Returns:
            Path to the WACZ, or None if packaging failed
        """
        if not warc_path or not warc_path.exists():
            return None

        wacz_path = warc_path.parent / filename

        result = self._official_package(warc_path, wacz_path, page_url)
        if result:
            return result
        return self._native_package(warc_path, wacz_path, page_url)

    def _official_package(self, warc_path: Path, wacz_path: Path, page_url: str) -> Optional[Path]:
        """Package via `python -m wacz create` (preferred when it works)"""
        cmd = [
            sys.executable, "-m", "wacz", "create",
            str(warc_path), "-o", str(wacz_path), "--url", page_url,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0 and wacz_path.exists():
                logger.success(f"WACZ packaged (py-wacz): {wacz_path}")
                return wacz_path
            logger.debug(
                f"py-wacz packaging failed (rc={result.returncode}), "
                f"falling back to native packager"
            )
            return None
        except Exception as e:
            logger.debug(f"py-wacz unavailable ({e}), falling back to native packager")
            return None

    def _native_package(self, warc_path: Path, wacz_path: Path, page_url: str) -> Optional[Path]:
        """Assemble the WACZ zip layout directly (spec 1.1.1)"""
        try:
            warc_bytes = warc_path.read_bytes()
            cdxj_bytes = self._build_cdxj(warc_path)
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            pages_lines = [
                json.dumps({"format": "json-pages-1.0", "id": "pages", "title": "All Pages"}),
                json.dumps({"id": "page-0", "url": page_url, "ts": now}),
            ]
            pages_bytes = ("\n".join(pages_lines) + "\n").encode("utf-8")

            entries = {
                f"archive/{warc_path.name}": warc_bytes,
                "indexes/index.cdx.gz": gzip.compress(cdxj_bytes),
                "pages/pages.jsonl": pages_bytes,
            }

            datapackage = {
                "profile": "data-package",
                "wacz_version": "1.1.1",
                "created": now,
                "software": "website-cloner-sdk",
                "mainPageUrl": page_url,
                "resources": [
                    {
                        "name": Path(path).name,
                        "path": path,
                        "hash": "sha256:" + hashlib.sha256(data).hexdigest(),
                        "bytes": len(data),
                    }
                    for path, data in entries.items()
                ],
            }
            dp_bytes = json.dumps(datapackage, indent=2).encode("utf-8")
            digest = {
                "path": "datapackage.json",
                "hash": "sha256:" + hashlib.sha256(dp_bytes).hexdigest(),
            }

            with zipfile.ZipFile(wacz_path, "w") as z:
                for path, data in entries.items():
                    # WARC and cdx.gz are already compressed; store them as-is
                    method = zipfile.ZIP_STORED if path.endswith(".gz") else zipfile.ZIP_DEFLATED
                    z.writestr(path, data, compress_type=method)
                z.writestr("datapackage.json", dp_bytes)
                z.writestr("datapackage-digest.json", json.dumps(digest, indent=2))

            logger.success(f"WACZ packaged (native): {wacz_path}")
            return wacz_path

        except Exception as e:
            logger.warning(f"Native WACZ packaging failed: {e}")
            return None

    def _build_cdxj(self, warc_path: Path) -> bytes:
        """Build a CDXJ index for the WARC via cdxj-indexer"""
        from cdxj_indexer.main import write_cdx_index

        out = StringIO()
        write_cdx_index(out, [str(warc_path)], {"sort": True, "compress": False})
        return out.getvalue().encode("utf-8")
