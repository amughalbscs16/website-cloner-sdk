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
from .downloaders.resource_downloader import ResourceDownloader
from .downloaders.css_downloader import CSSAssetDownloader
from .parsers.html_parser import HTMLParser
from .events import EventEmitter, ClonerEvents
from .events.event_emitter import (
    CloneStartData, CloneCompleteData, CloneErrorData,
    ProgressData, StatsData
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

    def clone(self, url: str) -> Path:
        """
        Clone a website

        Args:
            url: Website URL to clone

        Returns:
            Path to cloned website directory
        """
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
        project_path = file_manager.create_project_directory(url)

        # Initialize driver
        self.driver_manager = ChromeDriverManager(self.headless)
        driver = self.driver_manager.create_driver()

        try:
            # Load the page
            self.event_emitter.emit(ClonerEvents.PROGRESS_UPDATE, ProgressData(
                stage="loading",
                message="Loading page...",
                percentage=10.0
            ))
            logger.info("Loading page...")
            driver.get(url)
            time.sleep(config.PAGE_LOAD_WAIT)

            # Get page source
            page_source = driver.page_source
            self.event_emitter.emit(ClonerEvents.PAGE_LOADED, ProgressData(
                stage="loaded",
                message="Page loaded successfully",
                percentage=20.0
            ))

            # Extract network URLs
            self.event_emitter.emit(ClonerEvents.PROGRESS_UPDATE, ProgressData(
                stage="network_extraction",
                message="Extracting network logs...",
                percentage=25.0
            ))
            logger.info("Extracting network logs...")
            network_urls = set(self.driver_manager.get_network_logs(driver))
            logger.info(f"Found {len(network_urls)} network requests")

            self.event_emitter.emit(ClonerEvents.NETWORK_LOGS_EXTRACTED, StatsData(
                total_resources=len(network_urls),
                successful_downloads=0,
                failed_downloads=0,
                skipped_downloads=0,
                in_progress=0
            ))

            # Initialize downloaders with parallel download support
            logger.info(f"Using {config.MAX_WORKERS} parallel download threads")
            resource_downloader = ResourceDownloader(
                file_manager,
                network_urls,
                max_workers=config.MAX_WORKERS,
                event_emitter=self.event_emitter
            )
            css_downloader = CSSAssetDownloader(file_manager, resource_downloader)
            html_parser = HTMLParser(resource_downloader)

            # Process HTML
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
            self._process_css_files(project_path, css_downloader)

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

            # Generate download manifest
            self._generate_manifest(project_path, url, resource_downloader)

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

    def _process_css_files(self, project_path: Path, css_downloader: CSSAssetDownloader) -> None:
        """
        Process all CSS files in project to extract url() assets

        Args:
            project_path: Project directory
            css_downloader: CSSAssetDownloader instance
        """
        css_files = list(project_path.rglob("*.css"))
        logger.info(f"Found {len(css_files)} CSS files to process")

        for css_file in css_files:
            try:
                # Construct the original URL for this CSS file
                relative_path = css_file.relative_to(project_path)
                # This is a simplified approach - in production, you'd track the original URL
                css_url = str(relative_path)

                logger.debug(f"Processing CSS: {css_file}")
                css_downloader.extract_and_download_css_assets(
                    project_path, css_file, css_url
                )
            except Exception as e:
                logger.warning(f"Error processing CSS file {css_file}: {e}")

    def _generate_manifest(self, project_path: Path, url: str, resource_downloader: ResourceDownloader) -> None:
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
                "statistics": resource_downloader.download_stats,
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
