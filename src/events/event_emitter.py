"""Event emitter for real-time progress updates during website cloning"""

from enum import Enum
from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


class ClonerEvents(str, Enum):
    """Events emitted during the cloning process"""

    # Lifecycle events
    CLONE_START = "clone_start"
    CLONE_COMPLETE = "clone_complete"
    CLONE_ERROR = "clone_error"

    # Progress events
    PAGE_LOADED = "page_loaded"
    NETWORK_LOGS_EXTRACTED = "network_logs_extracted"
    HTML_PROCESSING_START = "html_processing_start"
    HTML_PROCESSING_COMPLETE = "html_processing_complete"
    CSS_PROCESSING_START = "css_processing_start"
    CSS_PROCESSING_COMPLETE = "css_processing_complete"

    # Download events
    RESOURCE_DISCOVERED = "resource_discovered"
    RESOURCE_DOWNLOAD_START = "resource_download_start"
    RESOURCE_DOWNLOAD_SUCCESS = "resource_download_success"
    RESOURCE_DOWNLOAD_FAILED = "resource_download_failed"
    RESOURCE_DOWNLOAD_SKIPPED = "resource_download_skipped"

    # Statistics events
    STATS_UPDATE = "stats_update"
    FILE_TYPE_STATS_UPDATE = "file_type_stats_update"

    # General progress
    PROGRESS_UPDATE = "progress_update"
    LOG_MESSAGE = "log_message"


@dataclass
class EventData:
    """Base class for event data"""
    timestamp: datetime = field(default_factory=datetime.now)
    event_type: str = ""


@dataclass
class CloneStartData(EventData):
    """Data for clone start event"""
    url: str = ""
    headless: bool = True


@dataclass
class CloneCompleteData(EventData):
    """Data for clone complete event"""
    url: str = ""
    output_path: str = ""
    duration_seconds: float = 0.0
    total_resources: int = 0
    successful_downloads: int = 0
    failed_downloads: int = 0
    skipped_downloads: int = 0


@dataclass
class CloneErrorData(EventData):
    """Data for clone error event"""
    url: str = ""
    error: str = ""
    traceback: Optional[str] = None


@dataclass
class ResourceData(EventData):
    """Data for resource-related events"""
    url: str = ""
    file_path: Optional[str] = None
    file_type: Optional[str] = None
    file_category: Optional[str] = None
    size_bytes: Optional[int] = None
    error: Optional[str] = None


@dataclass
class StatsData(EventData):
    """Data for statistics update events"""
    total_resources: int = 0
    successful_downloads: int = 0
    failed_downloads: int = 0
    skipped_downloads: int = 0
    in_progress: int = 0


@dataclass
class FileTypeStatsData(EventData):
    """Data for file type statistics"""
    file_type_breakdown: Dict[str, Dict[str, int]] = field(default_factory=dict)
    # Example: {"images": {"total": 10, "success": 8, "failed": 2}, ...}


@dataclass
class ProgressData(EventData):
    """Data for progress update events"""
    stage: str = ""
    message: str = ""
    percentage: float = 0.0


@dataclass
class LogData(EventData):
    """Data for log message events"""
    level: str = ""  # INFO, WARNING, ERROR, DEBUG, SUCCESS
    message: str = ""


class EventEmitter:
    """Event emitter for subscribing to cloning progress updates"""

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}

    def on(self, event: str, callback: Callable[[Any], None]) -> None:
        """
        Subscribe to an event

        Args:
            event: Event name (use ClonerEvents enum)
            callback: Function to call when event is emitted
        """
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)

    def off(self, event: str, callback: Optional[Callable] = None) -> None:
        """
        Unsubscribe from an event

        Args:
            event: Event name
            callback: Specific callback to remove (or None to remove all)
        """
        if event not in self._listeners:
            return

        if callback is None:
            # Remove all listeners for this event
            self._listeners[event] = []
        else:
            # Remove specific callback
            self._listeners[event] = [
                cb for cb in self._listeners[event] if cb != callback
            ]

    def emit(self, event: str, data: Any = None) -> None:
        """
        Emit an event to all subscribers

        Args:
            event: Event name
            data: Event data to pass to callbacks
        """
        if event not in self._listeners:
            return

        for callback in self._listeners[event]:
            try:
                callback(data)
            except Exception as e:
                # Don't let callback errors break the emitter
                print(f"Error in event callback for {event}: {e}")

    def once(self, event: str, callback: Callable[[Any], None]) -> None:
        """
        Subscribe to an event only once

        Args:
            event: Event name
            callback: Function to call when event is emitted
        """
        def wrapper(data):
            callback(data)
            self.off(event, wrapper)

        self.on(event, wrapper)

    def remove_all_listeners(self, event: Optional[str] = None) -> None:
        """
        Remove all listeners for a specific event or all events

        Args:
            event: Event name (or None to remove all listeners)
        """
        if event is None:
            self._listeners = {}
        else:
            self._listeners[event] = []

    def listener_count(self, event: str) -> int:
        """
        Get the number of listeners for an event

        Args:
            event: Event name

        Returns:
            Number of listeners
        """
        return len(self._listeners.get(event, []))
