"""Screenshot scheduler for continuous monitoring"""

import asyncio
import signal
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Callable
from selenium.webdriver.remote.webdriver import WebDriver
from ..utils.logger import logger
from .screenshot_monitor import ScreenshotMonitor


class SchedulerStats:
    """Statistics for monitoring session"""

    def __init__(self):
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.total_captures: int = 0
        self.successful_captures: int = 0
        self.failed_captures: int = 0
        self.last_capture_time: Optional[datetime] = None
        self.errors: list = []

    def to_dict(self) -> Dict:
        """Convert stats to dictionary"""
        return {
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else None,
            "total_captures": self.total_captures,
            "successful_captures": self.successful_captures,
            "failed_captures": self.failed_captures,
            "success_rate": (self.successful_captures / self.total_captures * 100) if self.total_captures > 0 else 0,
            "last_capture_time": self.last_capture_time.isoformat() if self.last_capture_time else None,
            "errors": self.errors[-10:]  # Last 10 errors
        }


class ScreenshotScheduler:
    """Manages scheduled screenshot captures"""

    def __init__(
        self,
        driver: WebDriver,
        output_dir: Path,
        interval_seconds: int = 300,  # 5 minutes default
        max_captures: Optional[int] = None,
        max_duration_seconds: Optional[int] = None
    ):
        """
        Initialize screenshot scheduler

        Args:
            driver: Selenium WebDriver instance
            output_dir: Project output directory
            interval_seconds: Time between captures (default: 300s = 5min)
            max_captures: Maximum number of captures (None = unlimited)
            max_duration_seconds: Maximum monitoring duration in seconds (None = unlimited)
        """
        self.driver = driver
        self.output_dir = Path(output_dir)
        self.interval_seconds = interval_seconds
        self.max_captures = max_captures
        self.max_duration_seconds = max_duration_seconds

        self.monitor = ScreenshotMonitor(driver, output_dir, enable_screenshots=True)
        self.stats = SchedulerStats()
        self.running = False
        self._stop_requested = False
        self._on_capture_callback: Optional[Callable] = None

    def on_capture(self, callback: Callable):
        """
        Register callback to be called after each capture

        Args:
            callback: Function to call with (screenshot_path, capture_number)
        """
        self._on_capture_callback = callback
        return callback

    async def start_monitoring(
        self,
        url: str,
        page_name: str = "main",
        fullpage: bool = True,
        viewports: Optional[list] = None
    ):
        """
        Start continuous monitoring

        Args:
            url: URL to monitor
            page_name: Identifier for this page
            fullpage: Whether to capture full page
            viewports: Optional list of viewport names to capture

        Returns:
            Statistics dictionary
        """
        self.running = True
        self._stop_requested = False
        self.stats = SchedulerStats()
        self.stats.start_time = datetime.now()

        logger.info(f"Starting screenshot monitoring: {url}")
        logger.info(f"Interval: {self.interval_seconds}s, Max captures: {self.max_captures or 'unlimited'}")

        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()

        try:
            capture_count = 0

            while self.running and not self._stop_requested:
                # Check if we've reached max captures
                if self.max_captures and capture_count >= self.max_captures:
                    logger.info(f"Reached maximum captures: {self.max_captures}")
                    break

                # Check if we've exceeded max duration
                if self.max_duration_seconds:
                    elapsed = (datetime.now() - self.stats.start_time).total_seconds()
                    if elapsed >= self.max_duration_seconds:
                        logger.info(f"Reached maximum duration: {self.max_duration_seconds}s")
                        break

                # Perform capture
                try:
                    logger.info(f"Capture #{capture_count + 1} starting...")
                    self.stats.total_captures += 1

                    # Capture screenshot(s)
                    if fullpage:
                        screenshot_path = self.monitor.capture_fullpage(url, page_name)
                    else:
                        screenshot_path = self.monitor.capture_viewport(url, page_name)

                    # Capture additional viewports if specified
                    if viewports:
                        self.monitor.capture_multiple_viewports(url, page_name, viewports)

                    self.stats.successful_captures += 1
                    self.stats.last_capture_time = datetime.now()
                    capture_count += 1

                    logger.success(f"Capture #{capture_count} completed: {screenshot_path}")

                    # Call callback if registered
                    if self._on_capture_callback:
                        try:
                            self._on_capture_callback(screenshot_path, capture_count)
                        except Exception as e:
                            logger.warning(f"Callback error: {e}")

                except Exception as e:
                    self.stats.failed_captures += 1
                    error_msg = f"Capture failed: {str(e)}"
                    self.stats.errors.append({
                        "timestamp": datetime.now().isoformat(),
                        "error": error_msg,
                        "capture_number": capture_count + 1
                    })
                    logger.error(error_msg)

                # Wait for next interval (unless we're stopping)
                if not self._stop_requested:
                    logger.info(f"Waiting {self.interval_seconds}s until next capture...")
                    await self._interruptible_sleep(self.interval_seconds)

        except asyncio.CancelledError:
            logger.warning("Monitoring cancelled")
        except KeyboardInterrupt:
            logger.warning("Monitoring interrupted by user")
        finally:
            self.running = False
            self.stats.end_time = datetime.now()

            # Log final statistics
            logger.info("Monitoring session ended")
            logger.info(f"Total captures: {self.stats.total_captures}")
            logger.info(f"Successful: {self.stats.successful_captures}")
            logger.info(f"Failed: {self.stats.failed_captures}")
            logger.info(f"Duration: {self.stats.end_time - self.stats.start_time}")

        return self.stats.to_dict()

    async def _interruptible_sleep(self, seconds: int):
        """
        Sleep that can be interrupted by stop request

        Args:
            seconds: Number of seconds to sleep
        """
        for _ in range(seconds):
            if self._stop_requested:
                break
            await asyncio.sleep(1)

    def stop_monitoring(self):
        """Stop the monitoring process"""
        logger.info("Stop requested for screenshot monitoring")
        self._stop_requested = True
        self.running = False

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.warning(f"Received signal {signum}, stopping monitoring...")
            self.stop_monitoring()

        # Only setup signal handlers if available (not on Windows in some cases)
        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        except (AttributeError, ValueError):
            # Signals might not be available on all platforms
            pass

    def get_statistics(self) -> Dict:
        """
        Get current monitoring statistics

        Returns:
            Dictionary with statistics
        """
        stats = self.stats.to_dict()
        stats["running"] = self.running
        stats["interval_seconds"] = self.interval_seconds
        stats["max_captures"] = self.max_captures
        stats["max_duration_seconds"] = self.max_duration_seconds

        # Add storage stats
        storage_stats = self.monitor.get_statistics()
        stats["storage"] = storage_stats

        return stats


async def monitor_website(
    url: str,
    output_dir: Path,
    interval_minutes: int = 5,
    max_captures: Optional[int] = None,
    duration_hours: Optional[int] = None,
    viewports: Optional[list] = None,
    headless: bool = True
) -> Dict:
    """
    Convenience function to monitor a website

    Args:
        url: URL to monitor
        output_dir: Output directory for screenshots
        interval_minutes: Minutes between captures (default: 5)
        max_captures: Maximum captures (None = unlimited)
        duration_hours: Maximum duration in hours (None = unlimited)
        viewports: Optional list of viewport names
        headless: Run browser in headless mode

    Returns:
        Statistics dictionary
    """
    from ..drivers.chrome_driver import ChromeDriverManager

    driver_manager = ChromeDriverManager(headless=headless)
    driver = driver_manager.create_driver()

    try:
        # Navigate to URL
        driver.get(url)
        await asyncio.sleep(3)  # Wait for page load

        # Create scheduler
        scheduler = ScreenshotScheduler(
            driver,
            output_dir,
            interval_seconds=interval_minutes * 60,
            max_captures=max_captures,
            max_duration_seconds=duration_hours * 3600 if duration_hours else None
        )

        # Start monitoring
        stats = await scheduler.start_monitoring(
            url,
            page_name="main",
            fullpage=True,
            viewports=viewports
        )

        return stats

    finally:
        driver_manager.close()
