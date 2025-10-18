"""Main website cloner module"""

import json
import time
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


class WebsiteCloner:
    """Main class for cloning websites"""

    def __init__(self, headless: bool = None):
        """
        Initialize website cloner

        Args:
            headless: Run browser in headless mode (default from config)
        """
        self.headless = headless if headless is not None else config.HEADLESS
        self.driver_manager: Optional[ChromeDriverManager] = None

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
        logger.info(f"Starting clone of: {url}")

        # Setup file manager
        file_manager = FileManager(config.PROJECT_DIR)
        project_path = file_manager.create_project_directory(url)

        # Initialize driver
        self.driver_manager = ChromeDriverManager(self.headless)
        driver = self.driver_manager.create_driver()

        try:
            # Load the page
            logger.info("Loading page...")
            driver.get(url)
            time.sleep(config.PAGE_LOAD_WAIT)

            # Get page source
            page_source = driver.page_source

            # Extract network URLs
            logger.info("Extracting network logs...")
            network_urls = set(self.driver_manager.get_network_logs(driver))
            logger.info(f"Found {len(network_urls)} network requests")

            # Initialize downloaders with parallel download support
            logger.info(f"Using {config.MAX_WORKERS} parallel download threads")
            resource_downloader = ResourceDownloader(
                file_manager,
                network_urls,
                max_workers=config.MAX_WORKERS
            )
            css_downloader = CSSAssetDownloader(file_manager, resource_downloader)
            html_parser = HTMLParser(resource_downloader)

            # Process HTML
            logger.info("Processing HTML and downloading assets...")
            processed_html = html_parser.process_html(page_source, url, project_path)

            # Save index.html
            index_path = project_path / "index.html"
            index_path.write_text(processed_html, encoding='utf-8')
            logger.info(f"Saved index.html: {index_path}")

            # Process CSS files for internal assets
            logger.info("Processing CSS files for internal assets...")
            self._process_css_files(project_path, css_downloader)

            # Log download statistics
            stats = resource_downloader.download_stats
            logger.success(f"Successfully cloned: {url}")
            logger.info(f"Output directory: {project_path}")
            logger.info(f"Download statistics: ✅ {stats['success']} succeeded | ❌ {stats['failed']} failed | ⏭️ {stats['skipped']} skipped")

            # Generate download manifest
            self._generate_manifest(project_path, url, resource_downloader)

            return project_path

        except Exception as e:
            logger.error(f"Failed to clone website: {e}")
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
