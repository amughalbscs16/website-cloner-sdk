"""WordPress Website Cloner - Modern Implementation"""

__version__ = "2.0.0"
__author__ = "Modernized Codebase"

# Export main SDK classes for easy import
from .sdk import ClonerSDK, clone_website
from .events import EventEmitter, ClonerEvents
from .events.event_emitter import (
    CloneStartData,
    CloneCompleteData,
    CloneErrorData,
    ResourceData,
    StatsData,
    FileTypeStatsData,
    ProgressData,
    LogData
)

__all__ = [
    # Main SDK
    'ClonerSDK',
    'clone_website',

    # Events
    'EventEmitter',
    'ClonerEvents',

    # Event data classes
    'CloneStartData',
    'CloneCompleteData',
    'CloneErrorData',
    'ResourceData',
    'StatsData',
    'FileTypeStatsData',
    'ProgressData',
    'LogData',
]
