"""WordPress Website Cloner SDK for developers"""

from pathlib import Path
from typing import Optional, Callable, Dict, Any
from .cloner import WebsiteCloner
from .events import EventEmitter, ClonerEvents
from .events.event_emitter import (
    CloneStartData, CloneCompleteData, CloneErrorData,
    ResourceData, StatsData, FileTypeStatsData, ProgressData, LogData
)


class ClonerSDK:
    """
    High-level SDK for WordPress Website Cloner

    This class provides a clean, developer-friendly interface for cloning websites
    with real-time progress updates and statistics tracking.

    Example:
        ```python
        from website_cloner import ClonerSDK

        # Create SDK instance
        cloner = ClonerSDK()

        # Subscribe to progress events
        @cloner.on_progress
        def handle_progress(data):
            print(f"Progress: {data.percentage}% - {data.message}")

        @cloner.on_resource_downloaded
        def handle_download(data):
            print(f"Downloaded: {data.url}")

        @cloner.on_complete
        def handle_complete(data):
            print(f"Clone complete! Total time: {data.duration_seconds}s")
            print(f"Downloaded: {data.successful_downloads} files")

        # Clone a website
        output_path = cloner.clone("https://example.com")
        print(f"Cloned to: {output_path}")
        ```
    """

    def __init__(self, headless: bool = True):
        """
        Initialize the cloner SDK

        Args:
            headless: Run browser in headless mode (default: True)
        """
        self.headless = headless
        self.event_emitter = EventEmitter()
        self._stats = {"total": 0, "success": 0, "failed": 0, "skipped": 0}

    def clone(self, url: str) -> Path:
        """
        Clone a website

        Args:
            url: Website URL to clone

        Returns:
            Path to cloned website directory
        """
        cloner = WebsiteCloner(headless=self.headless, event_emitter=self.event_emitter)
        return cloner.clone(url)

    # Event subscription decorators for clean API

    def on_start(self, callback: Callable[[CloneStartData], None]) -> Callable:
        """
        Decorator: Subscribe to clone start event

        Args:
            callback: Function to call when cloning starts

        Returns:
            The callback function (for chaining)
        """
        self.event_emitter.on(ClonerEvents.CLONE_START, callback)
        return callback

    def on_complete(self, callback: Callable[[CloneCompleteData], None]) -> Callable:
        """
        Decorator: Subscribe to clone complete event

        Args:
            callback: Function to call when cloning completes

        Returns:
            The callback function (for chaining)
        """
        self.event_emitter.on(ClonerEvents.CLONE_COMPLETE, callback)
        return callback

    def on_error(self, callback: Callable[[CloneErrorData], None]) -> Callable:
        """
        Decorator: Subscribe to clone error event

        Args:
            callback: Function to call when an error occurs

        Returns:
            The callback function (for chaining)
        """
        self.event_emitter.on(ClonerEvents.CLONE_ERROR, callback)
        return callback

    def on_progress(self, callback: Callable[[ProgressData], None]) -> Callable:
        """
        Decorator: Subscribe to progress update events

        Args:
            callback: Function to call on progress updates

        Returns:
            The callback function (for chaining)
        """
        self.event_emitter.on(ClonerEvents.PROGRESS_UPDATE, callback)
        return callback

    def on_resource_discovered(self, callback: Callable[[ResourceData], None]) -> Callable:
        """
        Decorator: Subscribe to resource discovered events

        Args:
            callback: Function to call when a resource is discovered

        Returns:
            The callback function (for chaining)
        """
        self.event_emitter.on(ClonerEvents.RESOURCE_DISCOVERED, callback)
        return callback

    def on_resource_downloaded(self, callback: Callable[[ResourceData], None]) -> Callable:
        """
        Decorator: Subscribe to resource download success events

        Args:
            callback: Function to call when a resource is downloaded

        Returns:
            The callback function (for chaining)
        """
        self.event_emitter.on(ClonerEvents.RESOURCE_DOWNLOAD_SUCCESS, callback)
        return callback

    def on_resource_failed(self, callback: Callable[[ResourceData], None]) -> Callable:
        """
        Decorator: Subscribe to resource download failed events

        Args:
            callback: Function to call when a resource download fails

        Returns:
            The callback function (for chaining)
        """
        self.event_emitter.on(ClonerEvents.RESOURCE_DOWNLOAD_FAILED, callback)
        return callback

    def on_stats_update(self, callback: Callable[[StatsData], None]) -> Callable:
        """
        Decorator: Subscribe to statistics update events

        Args:
            callback: Function to call when stats are updated

        Returns:
            The callback function (for chaining)
        """
        self.event_emitter.on(ClonerEvents.STATS_UPDATE, callback)
        return callback

    def on_page_loaded(self, callback: Callable[[ProgressData], None]) -> Callable:
        """
        Decorator: Subscribe to page loaded event

        Args:
            callback: Function to call when page is loaded

        Returns:
            The callback function (for chaining)
        """
        self.event_emitter.on(ClonerEvents.PAGE_LOADED, callback)
        return callback

    def on_network_logs_extracted(self, callback: Callable[[StatsData], None]) -> Callable:
        """
        Decorator: Subscribe to network logs extracted event

        Args:
            callback: Function to call when network logs are extracted

        Returns:
            The callback function (for chaining)
        """
        self.event_emitter.on(ClonerEvents.NETWORK_LOGS_EXTRACTED, callback)
        return callback

    def on_html_processing_start(self, callback: Callable[[ProgressData], None]) -> Callable:
        """
        Decorator: Subscribe to HTML processing start event

        Args:
            callback: Function to call when HTML processing starts

        Returns:
            The callback function (for chaining)
        """
        self.event_emitter.on(ClonerEvents.HTML_PROCESSING_START, callback)
        return callback

    def on_html_processing_complete(self, callback: Callable[[ProgressData], None]) -> Callable:
        """
        Decorator: Subscribe to HTML processing complete event

        Args:
            callback: Function to call when HTML processing completes

        Returns:
            The callback function (for chaining)
        """
        self.event_emitter.on(ClonerEvents.HTML_PROCESSING_COMPLETE, callback)
        return callback

    def on_css_processing_start(self, callback: Callable[[ProgressData], None]) -> Callable:
        """
        Decorator: Subscribe to CSS processing start event

        Args:
            callback: Function to call when CSS processing starts

        Returns:
            The callback function (for chaining)
        """
        self.event_emitter.on(ClonerEvents.CSS_PROCESSING_START, callback)
        return callback

    def on_css_processing_complete(self, callback: Callable[[ProgressData], None]) -> Callable:
        """
        Decorator: Subscribe to CSS processing complete event

        Args:
            callback: Function to call when CSS processing completes

        Returns:
            The callback function (for chaining)
        """
        self.event_emitter.on(ClonerEvents.CSS_PROCESSING_COMPLETE, callback)
        return callback

    # Alternative non-decorator API

    def add_listener(self, event: str, callback: Callable[[Any], None]) -> None:
        """
        Add an event listener

        Args:
            event: Event name (use ClonerEvents enum)
            callback: Callback function
        """
        self.event_emitter.on(event, callback)

    def remove_listener(self, event: str, callback: Optional[Callable] = None) -> None:
        """
        Remove an event listener

        Args:
            event: Event name
            callback: Callback function (or None to remove all)
        """
        self.event_emitter.off(event, callback)

    def remove_all_listeners(self, event: Optional[str] = None) -> None:
        """
        Remove all event listeners

        Args:
            event: Event name (or None to remove all)
        """
        self.event_emitter.remove_all_listeners(event)

    @property
    def stats(self) -> Dict[str, int]:
        """Get current statistics"""
        return self._stats.copy()


# Convenience function for simple usage
def clone_website(
    url: str,
    headless: bool = True,
    on_progress: Optional[Callable[[ProgressData], None]] = None,
    on_complete: Optional[Callable[[CloneCompleteData], None]] = None,
    on_error: Optional[Callable[[CloneErrorData], None]] = None
) -> Path:
    """
    Convenience function to clone a website with optional callbacks

    Args:
        url: Website URL to clone
        headless: Run in headless mode
        on_progress: Optional progress callback
        on_complete: Optional completion callback
        on_error: Optional error callback

    Returns:
        Path to cloned website directory

    Example:
        ```python
        from website_cloner import clone_website

        def progress(data):
            print(f"{data.percentage}% - {data.message}")

        def complete(data):
            print(f"Done! Downloaded {data.successful_downloads} files")

        output = clone_website(
            "https://example.com",
            on_progress=progress,
            on_complete=complete
        )
        ```
    """
    cloner = ClonerSDK(headless=headless)

    if on_progress:
        cloner.add_listener(ClonerEvents.PROGRESS_UPDATE, on_progress)
    if on_complete:
        cloner.add_listener(ClonerEvents.CLONE_COMPLETE, on_complete)
    if on_error:
        cloner.add_listener(ClonerEvents.CLONE_ERROR, on_error)

    return cloner.clone(url)
