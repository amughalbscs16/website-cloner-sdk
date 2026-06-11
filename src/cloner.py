"""Main website cloner module"""

import json
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional
from .config import config
from .utils.logger import logger
from .utils.url_utils import URLUtils
from .utils.file_utils import FileManager
from .drivers.chrome_driver import ChromeDriverManager
from .drivers.cdp_capture import harvest_captured_resources
from .downloaders.resource_downloader import ResourceDownloader
from .downloaders.css_downloader import CSSAssetDownloader
from .parsers.html_parser import HTMLParser
from .monitors.screenshot_monitor import ScreenshotMonitor
from .events import EventEmitter, ClonerEvents
from .events.event_emitter import (
    CloneStartData, CloneCompleteData, CloneErrorData,
    ProgressData, StatsData, FrameworkData
)


class WebsiteCloner:
    """Main class for cloning websites"""

    def __init__(self, headless: bool = None, event_emitter: Optional[EventEmitter] = None):
        """
        Initialize website cloner

        Args:
            headless: Run browser in headless mode (default from config)
            event_emitter: Optional event emitter for progress updates
        """
        self.headless = headless if headless is not None else config.HEADLESS
        self.driver_manager: Optional[ChromeDriverManager] = None
        self.event_emitter = event_emitter or EventEmitter()
        self._start_time: Optional[datetime] = None
        self._cancel_requested: bool = False

    def cancel(self) -> None:
        """Request cancellation of the current clone operation"""
        self._cancel_requested = True
        logger.warning("Clone cancellation requested")

    def _check_cancellation(self) -> None:
        """Check if cancellation was requested and raise exception if so"""
        if self._cancel_requested:
            raise InterruptedError("Clone operation was cancelled by user")

    def _extract_content(self, driver, selector: str) -> tuple[str, str]:
        """
        Extract content from a specific element using CSS or XPath selector

        Args:
            driver: Selenium WebDriver instance
            selector: CSS or XPath selector

        Returns:
            Tuple of (element_html, selector_type) where selector_type is 'css' or 'xpath'
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        element = None
        selector_type = None

        # Try CSS selector first
        try:
            logger.info(f"Trying CSS selector: {selector}")
            wait = WebDriverWait(driver, 10)
            element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            selector_type = 'css'
            logger.info(f"✓ Found element with CSS selector")
        except Exception as e:
            logger.debug(f"CSS selector failed: {e}")

            # Try XPath if CSS fails
            try:
                logger.info(f"Trying XPath selector: {selector}")
                wait = WebDriverWait(driver, 10)
                element = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                selector_type = 'xpath'
                logger.info(f"✓ Found element with XPath selector")
            except Exception as xpath_error:
                logger.error(f"XPath selector also failed: {xpath_error}")
                raise ValueError(
                    f"Could not find element with selector '{selector}'. "
                    f"Tried both CSS and XPath. Please check your selector."
                )

        # Get the outer HTML of the element
        element_html = element.get_attribute('outerHTML')
        logger.info(f"Extracted {len(element_html)} characters of HTML content")

        return element_html, selector_type

    def clone(self, url: str, content_selector: Optional[str] = None) -> Path:
        """
        Clone a website

        Args:
            url: Website URL to clone
            content_selector: Optional CSS or XPath selector to extract specific content only

        Returns:
            Path to cloned website directory
        """
        # Reset cancellation flag
        self._cancel_requested = False

        # Clean URL
        url = URLUtils.clean_url(url)
        self._start_time = datetime.now()

        # Emit clone start event
        self.event_emitter.emit(ClonerEvents.CLONE_START, CloneStartData(
            url=url,
            headless=self.headless
        ))
        self.event_emitter.emit(ClonerEvents.PROGRESS_UPDATE, ProgressData(
            stage="initialization",
            message=f"Starting clone of: {url}",
            percentage=0.0
        ))

        logger.info(f"Starting clone of: {url}")

        # Setup file manager
        file_manager = FileManager(config.PROJECT_DIR)
        project_path = file_manager.create_project_directory(url, fresh=True)

        # Initialize driver
        self.driver_manager = ChromeDriverManager(self.headless)
        driver = self.driver_manager.create_driver()

        try:
            # Load the page
            self._check_cancellation()
            self.event_emitter.emit(ClonerEvents.PROGRESS_UPDATE, ProgressData(
                stage="loading",
                message="Loading page...",
                percentage=10.0
            ))
            logger.info("Loading page...")
            driver.get(url)

            # Enlarge the resource-timing buffer so idle detection keeps
            # counting on resource-heavy pages (default caps at 250 entries)
            try:
                driver.execute_script("performance.setResourceTimingBufferSize(10000)")
            except Exception:
                pass

            went_idle = self.driver_manager.wait_for_page_idle(
                driver,
                idle_ms=config.NETWORK_IDLE_MS,
                timeout=config.PAGE_IDLE_TIMEOUT,
            )
            if not went_idle:
                # Idle detection unavailable or page never settled: fixed wait
                time.sleep(config.PAGE_LOAD_WAIT)

            # Trigger lazy-loaded content (images, infinite scroll segments)
            if config.AUTO_SCROLL and not content_selector:
                self.event_emitter.emit(ClonerEvents.PROGRESS_UPDATE, ProgressData(
                    stage="auto_scroll",
                    message="Scrolling to trigger lazy-loaded content...",
                    percentage=15.0
                ))
                logger.info("Auto-scrolling to trigger lazy-loaded content...")
                self.driver_manager.auto_scroll(driver)
                self.driver_manager.wait_for_page_idle(
                    driver, idle_ms=config.NETWORK_IDLE_MS, timeout=5.0
                )

            # Get page source (extract specific content if selector provided)
            self._check_cancellation()
            if content_selector:
                logger.info(f"Extracting content with selector: {content_selector}")
                self.event_emitter.emit(ClonerEvents.PROGRESS_UPDATE, ProgressData(
                    stage="content_extraction",
                    message=f"Extracting content using selector...",
                    percentage=15.0
                ))
                content_html, selector_type = self._extract_content(driver, content_selector)
                # Wrap extracted content in minimal HTML structure
                page_source = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Extracted Content</title>
    <style>
        body {{ max-width: 1200px; margin: 0 auto; padding: 20px; font-family: system-ui, -apple-system, sans-serif; }}
        img {{ max-width: 100%; height: auto; }}
    </style>
</head>
<body>
{content_html}
</body>
</html>"""
                logger.info(f"Content extracted successfully using {selector_type} selector")
            else:
                # Serialize CSS-in-JS rules (styled-components/emotion/styled-jsx)
                # from the CSSOM into their <style> elements before snapshotting,
                # otherwise page_source captures them empty and the clone is unstyled
                self.driver_manager.inline_runtime_styles(driver)
                page_source = driver.page_source

                # Static-snapshot mode: drop scripts so re-hydration can't wipe
                # the captured, styled DOM when the clone is reopened
                if config.STATIC_SNAPSHOT:
                    page_source = self.driver_manager.neutralize_scripts(page_source)

            self.event_emitter.emit(ClonerEvents.PAGE_LOADED, ProgressData(
                stage="loaded",
                message="Page loaded successfully",
                percentage=20.0
            ))

            # Detect the site's frameworks from the live page (markup + JS globals)
            detected_frameworks = []
            if not content_selector:
                try:
                    from .discovery import FrameworkDetector
                    detector = FrameworkDetector()
                    matches = detector.detect(
                        driver.page_source, url, js_eval=driver.execute_script
                    )
                    detected_frameworks = [m.to_dict() for m in matches]
                    self.event_emitter.emit(ClonerEvents.FRAMEWORK_DETECTED, FrameworkData(
                        frameworks=detected_frameworks,
                        primary=matches[0].name if matches else None,
                    ))
                except Exception as e:
                    logger.debug(f"Framework detection failed: {e}")

            # Capture screenshot if enabled (only when NOT using selective content mode)
            if config.ENABLE_SCREENSHOTS and not content_selector:
                self.event_emitter.emit(ClonerEvents.PROGRESS_UPDATE, ProgressData(
                    stage="screenshot",
                    message="Capturing screenshot...",
                    percentage=22.0
                ))
                screenshot_monitor = ScreenshotMonitor(driver, project_path, enable_screenshots=True)

                if config.SCREENSHOT_FULLPAGE:
                    screenshot_monitor.capture_fullpage(url, "main")

                if config.SCREENSHOT_VIEWPORTS:
                    screenshot_monitor.capture_multiple_viewports(url, "main", config.SCREENSHOT_VIEWPORTS)

                logger.info("Screenshots captured successfully")
            elif content_selector:
                logger.info("Selective content mode: skipping full page screenshot")

            # Harvest network activity and response bodies via CDP
            # (skip if using selective content mode - we'll parse from HTML instead)
            self._check_cancellation()
            captured_resources = {}
            if not content_selector:
                self.event_emitter.emit(ClonerEvents.PROGRESS_UPDATE, ProgressData(
                    stage="network_extraction",
                    message="Harvesting browser network capture...",
                    percentage=25.0
                ))
                logger.info("Harvesting network activity and response bodies via CDP...")
                network_urls, captured_resources = harvest_captured_resources(
                    self.driver_manager, driver
                )
                logger.info(
                    f"Found {len(network_urls)} network requests, "
                    f"{len(captured_resources)} bodies captured in-browser"
                )
            else:
                # In selective content mode, we'll extract resources from the HTML directly
                logger.info("Selective content mode: skipping network log extraction (will parse from HTML)")
                network_urls = set()

            self.event_emitter.emit(ClonerEvents.NETWORK_LOGS_EXTRACTED, StatsData(
                total_resources=len(network_urls),
                successful_downloads=0,
                failed_downloads=0,
                skipped_downloads=0,
                in_progress=0
            ))
            self.event_emitter.emit(ClonerEvents.CDP_CAPTURE_COMPLETE, StatsData(
                total_resources=len(captured_resources),
                successful_downloads=0,
                failed_downloads=0,
                skipped_downloads=0,
                in_progress=0
            ))

            # Initialize downloaders with parallel download support
            self._check_cancellation()
            logger.info(f"Using {config.MAX_WORKERS} parallel download threads")
            resource_downloader = ResourceDownloader(
                file_manager,
                network_urls,
                max_workers=config.MAX_WORKERS,
                event_emitter=self.event_emitter,
                cancel_check=self._check_cancellation,
                captured_resources=captured_resources
            )
            css_downloader = CSSAssetDownloader(file_manager, resource_downloader)
            html_parser = HTMLParser(resource_downloader)

            # Process HTML
            self._check_cancellation()
            self.event_emitter.emit(ClonerEvents.HTML_PROCESSING_START, ProgressData(
                stage="html_processing",
                message="Processing HTML and downloading assets...",
                percentage=30.0
            ))
            logger.info("Processing HTML and downloading assets...")
            processed_html = html_parser.process_html(page_source, url, project_path)

            # Save index.html
            index_path = project_path / "index.html"
            index_path.write_text(processed_html, encoding='utf-8')
            logger.info(f"Saved index.html: {index_path}")

            self.event_emitter.emit(ClonerEvents.HTML_PROCESSING_COMPLETE, ProgressData(
                stage="html_complete",
                message="HTML processing complete",
                percentage=70.0
            ))

            # Process CSS files for internal assets
            self.event_emitter.emit(ClonerEvents.CSS_PROCESSING_START, ProgressData(
                stage="css_processing",
                message="Processing CSS files for internal assets...",
                percentage=75.0
            ))
            logger.info("Processing CSS files for internal assets...")
            self._process_css_files(project_path, css_downloader, file_manager, url)

            self.event_emitter.emit(ClonerEvents.CSS_PROCESSING_COMPLETE, ProgressData(
                stage="css_complete",
                message="CSS processing complete",
                percentage=90.0
            ))

            # Log download statistics
            stats = resource_downloader.download_stats
            logger.success(f"Successfully cloned: {url}")
            logger.info(f"Output directory: {project_path}")
            logger.info(f"Download statistics: {stats['success']} succeeded | {stats['failed']} failed | {stats['skipped']} skipped")

            # Export standards-compliant WARC from the browser-captured bodies
            if config.EXPORT_WARC and captured_resources:
                self.event_emitter.emit(ClonerEvents.PROGRESS_UPDATE, ProgressData(
                    stage="warc_export",
                    message="Writing WARC archive...",
                    percentage=92.0
                ))
                from .exporters.warc_exporter import WarcExporter
                warc_path = WarcExporter().export(project_path, url, captured_resources)

                if warc_path and config.EXPORT_WACZ:
                    self.event_emitter.emit(ClonerEvents.PROGRESS_UPDATE, ProgressData(
                        stage="wacz_export",
                        message="Packaging WACZ archive...",
                        percentage=94.0
                    ))
                    from .exporters.wacz_exporter import WaczExporter
                    WaczExporter().export(warc_path, url)

            # Generate download manifest
            self._generate_manifest(project_path, url, resource_downloader, detected_frameworks)

            # Calculate duration
            duration = (datetime.now() - self._start_time).total_seconds()

            # Emit completion event
            self.event_emitter.emit(ClonerEvents.CLONE_COMPLETE, CloneCompleteData(
                url=url,
                output_path=str(project_path),
                duration_seconds=duration,
                total_resources=stats['success'] + stats['failed'] + stats['skipped'],
                successful_downloads=stats['success'],
                failed_downloads=stats['failed'],
                skipped_downloads=stats['skipped']
            ))
            self.event_emitter.emit(ClonerEvents.PROGRESS_UPDATE, ProgressData(
                stage="complete",
                message="Clone complete!",
                percentage=100.0
            ))

            return project_path

        except Exception as e:
            logger.error(f"Failed to clone website: {e}")

            # Emit error event
            self.event_emitter.emit(ClonerEvents.CLONE_ERROR, CloneErrorData(
                url=url,
                error=str(e),
                traceback=traceback.format_exc()
            ))

            raise

        finally:
            # Cleanup
            if self.driver_manager:
                self.driver_manager.close()

    def _process_css_files(
        self,
        project_path: Path,
        css_downloader: CSSAssetDownloader,
        file_manager: FileManager,
        page_url: str,
    ) -> None:
        """
        Process all CSS files in project to extract url() assets

        Args:
            project_path: Project directory
            css_downloader: CSSAssetDownloader instance
            file_manager: FileManager holding the URL -> local path download cache
            page_url: URL of the cloned page (fallback base for unmatched files)
        """
        css_files = list(project_path.rglob("*.css"))
        logger.info(f"Found {len(css_files)} CSS files to process")

        # Recover each CSS file's original URL so url() references inside it
        # resolve against the real host, not a local file path
        url_by_local_path = {
            local: original for original, local in file_manager.link_file.items()
        }

        for css_file in css_files:
            try:
                relative_path = str(css_file.relative_to(project_path)).replace("\\", "/")
                css_url = url_by_local_path.get(relative_path)
                if not css_url:
                    css_url = URLUtils.normalize_url(page_url, relative_path)
                    logger.debug(f"No origin URL tracked for {relative_path}, assuming {css_url}")

                logger.debug(f"Processing CSS: {css_file} (origin: {css_url})")
                css_downloader.extract_and_download_css_assets(
                    project_path, css_file, css_url
                )
            except Exception as e:
                logger.warning(f"Error processing CSS file {css_file}: {e}")

    def _generate_manifest(self, project_path: Path, url: str, resource_downloader: ResourceDownloader, frameworks: list = None) -> None:
        """
        Generate download manifest with success/failure tracking

        Args:
            project_path: Project directory
            url: Original website URL
            resource_downloader: ResourceDownloader instance with tracking data
        """
        try:
            manifest_path = project_path / "download_manifest.json"

            manifest_data = {
                "timestamp": datetime.now().isoformat(),
                "url": url,
                "frameworks": frameworks or [],
                "statistics": resource_downloader.download_stats,
                "capture_methods": resource_downloader.capture_method_stats,
                "successful_downloads": resource_downloader.successful_downloads,
                "failed_downloads": resource_downloader.failed_downloads
            }

            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Generated download manifest: {manifest_path}")

        except Exception as e:
            logger.warning(f"Failed to generate manifest: {e}")


def clone_website(url: str, headless: bool = None) -> Path:
    """
    Convenience function to clone a website

    Args:
        url: Website URL to clone
        headless: Run in headless mode

    Returns:
        Path to cloned website
    """
    cloner = WebsiteCloner(headless=headless)
    return cloner.clone(url)
