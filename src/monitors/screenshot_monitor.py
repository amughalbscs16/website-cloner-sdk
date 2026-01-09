"""Screenshot capture monitor"""

import time
from pathlib import Path
from typing import Optional, List, Tuple
from selenium.webdriver.remote.webdriver import WebDriver
from ..utils.logger import logger
from .storage_manager import StorageManager


class ScreenshotMonitor:
    """Handles screenshot capture and storage"""

    # Common viewport sizes
    VIEWPORTS = {
        "mobile": (375, 667),      # iPhone SE
        "tablet": (768, 1024),     # iPad
        "desktop": (1920, 1080),   # Full HD
        "desktop_4k": (3840, 2160) # 4K
    }

    def __init__(
        self,
        driver: WebDriver,
        output_dir: Path,
        enable_screenshots: bool = True
    ):
        """
        Initialize screenshot monitor

        Args:
            driver: Selenium WebDriver instance
            output_dir: Project output directory
            enable_screenshots: Whether screenshots are enabled
        """
        self.driver = driver
        self.output_dir = Path(output_dir)
        self.enabled = enable_screenshots
        self.storage = StorageManager(output_dir)

    def capture_screenshot(
        self,
        url: str,
        page_name: str = "main",
        fullpage: bool = True
    ) -> Optional[Path]:
        """
        Capture a single screenshot

        Args:
            url: URL being captured
            page_name: Identifier for this page
            fullpage: Whether to capture full page or viewport only

        Returns:
            Path to saved screenshot or None if disabled
        """
        if not self.enabled:
            return None

        try:
            if fullpage:
                return self.capture_fullpage(url, page_name)
            else:
                return self.capture_viewport(url, page_name)
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return None

    def capture_fullpage(self, url: str, page_name: str = "main") -> Path:
        """
        Capture full scrollable page

        Args:
            url: URL being captured
            page_name: Identifier for this page

        Returns:
            Path to saved screenshot
        """
        try:
            # Get full page screenshot
            screenshot_bytes = self.driver.get_screenshot_as_png()

            # Save with metadata
            file_path = self.storage.save_screenshot(
                image_data=screenshot_bytes,
                page_name=page_name,
                url=url,
                viewport=None,  # fullpage
                additional_metadata={
                    "type": "fullpage",
                    "browser": self.driver.capabilities.get("browserName", "unknown"),
                    "browser_version": self.driver.capabilities.get("browserVersion", "unknown")
                }
            )

            logger.info(f"Full-page screenshot captured: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Full-page screenshot failed: {e}")
            raise

    def capture_viewport(
        self,
        url: str,
        page_name: str = "main",
        viewport: Optional[Tuple[int, int]] = None
    ) -> Path:
        """
        Capture visible viewport only

        Args:
            url: URL being captured
            page_name: Identifier for this page
            viewport: Optional (width, height) to set before capture

        Returns:
            Path to saved screenshot
        """
        try:
            # Set viewport size if specified
            if viewport:
                self.driver.set_window_size(viewport[0], viewport[1])
                time.sleep(0.5)  # Wait for resize

            # Get current window size
            size = self.driver.get_window_size()
            current_viewport = (size['width'], size['height'])

            # Capture screenshot
            screenshot_bytes = self.driver.get_screenshot_as_png()

            # Save with metadata
            file_path = self.storage.save_screenshot(
                image_data=screenshot_bytes,
                page_name=page_name,
                url=url,
                viewport=current_viewport,
                additional_metadata={
                    "type": "viewport",
                    "browser": self.driver.capabilities.get("browserName", "unknown"),
                    "browser_version": self.driver.capabilities.get("browserVersion", "unknown")
                }
            )

            logger.info(f"Viewport screenshot captured: {file_path} ({current_viewport[0]}x{current_viewport[1]})")
            return file_path

        except Exception as e:
            logger.error(f"Viewport screenshot failed: {e}")
            raise

    def capture_multiple_viewports(
        self,
        url: str,
        page_name: str = "main",
        viewports: Optional[List[str]] = None
    ) -> List[Path]:
        """
        Capture at multiple viewport sizes

        Args:
            url: URL being captured
            page_name: Identifier for this page
            viewports: List of viewport names (mobile, tablet, desktop, desktop_4k)

        Returns:
            List of paths to saved screenshots
        """
        if not viewports:
            viewports = ["mobile", "desktop"]

        screenshots = []

        for viewport_name in viewports:
            if viewport_name not in self.VIEWPORTS:
                logger.warning(f"Unknown viewport: {viewport_name}, skipping")
                continue

            viewport_size = self.VIEWPORTS[viewport_name]
            logger.info(f"Capturing {viewport_name} viewport ({viewport_size[0]}x{viewport_size[1]})...")

            try:
                path = self.capture_viewport(url, f"{page_name}_{viewport_name}", viewport_size)
                screenshots.append(path)
            except Exception as e:
                logger.error(f"Failed to capture {viewport_name} viewport: {e}")

        return screenshots

    def get_statistics(self) -> dict:
        """
        Get screenshot statistics

        Returns:
            Dictionary with screenshot stats
        """
        return self.storage.get_statistics()
