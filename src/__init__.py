"""Website Cloner SDK - Modern Implementation"""

__version__ = "2.1.0"
__author__ = "Modernized Codebase"

# Use the OS certificate store for TLS when available. Python's bundled CA
# list rejects certificates re-signed by TLS-inspecting AV/proxies that the
# OS itself trusts, which breaks every HTTP fallback download on such machines.
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

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
