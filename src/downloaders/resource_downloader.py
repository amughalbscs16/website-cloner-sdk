"""Resource downloader with retry logic and parallel downloading"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, Dict, Set, List, Tuple, TYPE_CHECKING
import requests
import urllib3
import httpx
from ..config import config
from ..utils.logger import logger
from ..utils.url_utils import URLUtils
from ..events import ClonerEvents
from ..events.event_emitter import ResourceData, StatsData
from ..utils.file_utils import FileManager

if TYPE_CHECKING:
    from ..events import EventEmitter


class ResourceDownloader:
    """Handles downloading of web resources"""

    def __init__(self, file_manager: FileManager, network_urls: Set[str] = None, max_workers: int = 10, event_emitter: Optional['EventEmitter'] = None, cancel_check=None, captured_resources: Optional[Dict] = None):
        """
        Initialize resource downloader

        Args:
            file_manager: FileManager instance
            network_urls: Set of URLs captured from network logs
            max_workers: Number of parallel download threads (default: 10)
            event_emitter: Optional event emitter for progress updates
            cancel_check: Optional callable to check for cancellation
            captured_resources: Optional dict url -> CapturedResource of bodies
                already captured in-browser via CDP. These are used as the
                primary source; HTTP re-fetch is the fallback.
        """
        self.file_manager = file_manager
        self.network_urls = network_urls or set()
        self.captured_resources = captured_resources or {}
        self.http = urllib3.PoolManager()
        self.httpx_client = httpx.Client(timeout=30.0, follow_redirects=True)
        # Shared session: connection pooling amortizes TLS handshakes, which
        # dominate per-resource cost on slow or TLS-inspected connections
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.USER_AGENT})
        self.max_workers = max_workers
        self.download_stats = {"success": 0, "failed": 0, "skipped": 0}
        self.successful_downloads = []  # List of successfully downloaded URLs
        self.failed_downloads = []  # List of failed downloads with reasons
        self.event_emitter = event_emitter
        self.cancel_check = cancel_check

    def download_with_requests(self, url: str, timeout: int = None) -> Optional[requests.Response]:
        """
        Download using requests library

        Args:
            url: URL to download
            timeout: Request timeout

        Returns:
            Response object or None
        """
        timeout = timeout or config.REQUEST_TIMEOUT

        try:
            response = self.session.get(url, timeout=timeout)
            if response.status_code in (200, 201, 202, 203, 204, 206):
                return response
            logger.debug(f"Requests failed with status {response.status_code}: {url}")
            return None
        except Exception as e:
            logger.debug(f"Requests failed for {url}: {e}")
            return None

    def download_with_urllib(self, url: str) -> Optional[urllib3.response.HTTPResponse]:
        """
        Download using urllib3 as fallback

        Args:
            url: URL to download

        Returns:
            Response object or None
        """
        try:
            response = self.http.request("GET", url)
            if 200 <= response.status < 300:
                return response
            logger.debug(f"Urllib3 failed with status {response.status}: {url}")
            return None
        except Exception as e:
            logger.debug(f"Urllib3 failed for {url}: {e}")
            return None

    def download_with_httpx(self, url: str) -> Optional[httpx.Response]:
        """
        Download using httpx as third fallback

        Args:
            url: URL to download

        Returns:
            Response object or None
        """
        try:
            response = self.httpx_client.get(url)
            if 200 <= response.status_code < 300:
                return response
            logger.debug(f"Httpx failed with status {response.status_code}: {url}")
            return None
        except Exception as e:
            logger.debug(f"Httpx failed for {url}: {e}")
            return None

    def download_resource(self, url: str, max_retries: int = 3) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Get a resource's bytes: CDP-captured body first, HTTP re-fetch as fallback

        Args:
            url: URL to download
            max_retries: Maximum number of retry attempts per method (default: 3)

        Returns:
            Tuple of (Binary content or None, method name or None)
        """
        # Primary source: the body the browser actually received (CDP capture).
        # Re-fetching can fail or return different bytes for session-gated URLs.
        captured = self.captured_resources.get(url)
        if captured is not None:
            return captured.content, "cdp"

        # Fallback: re-fetch over HTTP with all three methods in order with retries
        methods = [
            ("requests", self.download_with_requests, lambda r: r.content),
            ("urllib3", self.download_with_urllib, lambda r: r.data),
            ("httpx", self.download_with_httpx, lambda r: r.content),
        ]

        for method_name, method_func, content_getter in methods:
            for attempt in range(max_retries):
                try:
                    response = method_func(url)
                    if response:
                        if attempt > 0:
                            logger.debug(f"Downloaded via {method_name} (attempt {attempt + 1}): {url}")
                        else:
                            logger.debug(f"Downloaded via {method_name}: {url}")
                        return content_getter(response), method_name
                except Exception as e:
                    if attempt < max_retries - 1:
                        # Exponential backoff: 0.5s, 1s, 2s
                        wait_time = 0.5 * (2 ** attempt)
                        logger.debug(f"{method_name} attempt {attempt + 1} failed for {url}, retrying in {wait_time}s: {e}")
                        time.sleep(wait_time)
                    else:
                        logger.debug(f"{method_name} failed after {max_retries} attempts for {url}: {e}")
                    continue

        # All methods and retries failed
        logger.warning(f"Failed to download (tried all methods with {max_retries} retries each): {url}")
        return None, None

    def is_html_content(self, response) -> bool:
        """Check if response contains HTML content"""
        try:
            if isinstance(response, requests.Response):
                content_type = response.headers.get("Content-Type", "")
            else:  # urllib3 response
                content_type = response.headers.get("Content-Type", "")

            return "html" in content_type.lower()
        except:
            return False

    def should_download_from_network(self, filename: str, url: str) -> bool:
        """
        Check if file should be downloaded based on network logs

        Args:
            filename: The filename extracted from URL
            url: The full URL

        Returns:
            True if file should be downloaded
        """
        # If no network logs available, download everything
        if not self.network_urls:
            return True

        # Check if URL or filename is in network logs
        if url in self.network_urls:
            return True

        # Check if filename appears in any network URL
        return any(filename in network_url for network_url in self.network_urls)

    def download_file(
        self,
        base_url: str,
        file_url: str,
        project_path: Path,
    ) -> str:
        """
        Download a file and return its local path

        Args:
            base_url: Base website URL
            file_url: File URL (may be relative)
            project_path: Project directory path

        Returns:
            Local file path relative to project directory
        """
        # Check for cancellation
        if self.cancel_check:
            self.cancel_check()

        # Skip empty or invalid URLs
        if not file_url or file_url.strip() in ("", " "):
            return file_url

        # Skip data URIs
        if file_url.startswith("data:"):
            return file_url

        # Normalize URL
        absolute_url = URLUtils.normalize_url(base_url, file_url)

        # Check if already downloaded
        if absolute_url in self.file_manager.link_file:
            self.download_stats["skipped"] += 1
            return self.file_manager.link_file[absolute_url]

        self._emit(ClonerEvents.RESOURCE_DISCOVERED, ResourceData(url=absolute_url))

        try:
            # Download the resource
            content, method_name = self.download_resource(absolute_url)
            if not content:
                logger.warning(f"Could not download: {absolute_url}")
                self.download_stats["failed"] += 1
                self.failed_downloads.append({
                    "url": absolute_url,
                    "reason": "All download methods failed"
                })
                self._emit(ClonerEvents.RESOURCE_DOWNLOAD_FAILED,
                           ResourceData(url=absolute_url, error="All download methods failed"))
                self._emit(ClonerEvents.STATS_UPDATE, self._stats_data())
                return file_url

            # Create directory structure
            save_directory, html_directory = self.file_manager.make_directory_structure(
                absolute_url, project_path
            )

            # Get filename
            filename = Path(absolute_url.split("?")[0].split("#")[0]).name
            if not filename:
                filename = "index.html"

            # Generate unique filename
            file_path = self.file_manager.get_unique_filename(
                save_directory, filename, config.ALLOWED_EXTENSIONS
            )

            # Save file
            self.file_manager.save_file(file_path, content)

            # Generate HTML-relative path
            html_path = str(Path(html_directory) / file_path.name).replace("\\", "/")

            # Cache the mapping
            self.file_manager.link_file[absolute_url] = html_path

            # Track successful download
            self.download_stats["success"] += 1
            self.successful_downloads.append({
                "url": absolute_url,
                "local_path": html_path,
                "method": method_name,
                "size": len(content)
            })
            self._emit(ClonerEvents.RESOURCE_DOWNLOAD_SUCCESS, ResourceData(
                url=absolute_url, file_path=html_path,
                file_type=(file_path.suffix.lstrip(".") or None), size_bytes=len(content)))
            self._emit(ClonerEvents.STATS_UPDATE, self._stats_data())
            logger.info(f"Downloaded: {absolute_url} -> {html_path}")
            return html_path

        except Exception as e:
            self.download_stats["failed"] += 1
            self.failed_downloads.append({
                "url": absolute_url,
                "reason": f"Exception: {str(e)}"
            })
            self._emit(ClonerEvents.RESOURCE_DOWNLOAD_FAILED,
                       ResourceData(url=absolute_url, error=str(e)))
            self._emit(ClonerEvents.STATS_UPDATE, self._stats_data())
            logger.error(f"Error downloading {absolute_url}: {e}")
            return file_url

    def _emit(self, event, data):
        """Emit an event if an emitter is attached; never let it break a download."""
        if not self.event_emitter:
            return
        try:
            self.event_emitter.emit(event, data)
        except Exception:
            pass

    def _stats_data(self) -> StatsData:
        s = self.download_stats
        return StatsData(
            total_resources=s["success"] + s["failed"] + s["skipped"],
            successful_downloads=s["success"],
            failed_downloads=s["failed"],
            skipped_downloads=s["skipped"],
        )

    def download_favicon(self, base_url: str, project_path: Path) -> None:
        """
        Download website favicon

        Args:
            base_url: Base website URL
            project_path: Project directory path
        """
        try:
            domain = URLUtils.get_domain(base_url)
            favicon_url = f"{domain}/favicon.ico"

            content, method_name = self.download_resource(favicon_url)
            if content:
                favicon_path = project_path / "favicon.ico"
                self.file_manager.save_file(favicon_path, content)
                self.successful_downloads.append({
                    "url": favicon_url,
                    "local_path": "favicon.ico",
                    "method": method_name,
                    "size": len(content)
                })
                logger.info(f"Downloaded favicon: {favicon_url}")
        except Exception as e:
            logger.warning(f"Could not download favicon: {e}")

    @property
    def capture_method_stats(self) -> Dict[str, int]:
        """Count of successful downloads per acquisition method (cdp/requests/urllib3/httpx)"""
        counts: Dict[str, int] = {}
        for item in self.successful_downloads:
            method = item.get("method") or "unknown"
            counts[method] = counts.get(method, 0) + 1
        return counts

    def close(self):
        """Close HTTP clients"""
        try:
            self.httpx_client.close()
        except:
            pass
        try:
            self.session.close()
        except:
            pass
