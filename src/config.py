"""Configuration management for Website Cloner"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class Config:
    """Application configuration"""

    # Directories
    BASE_DIR: Path = Path(__file__).parent.parent
    PROJECT_DIR: Path = BASE_DIR / "project"

    # Browser settings
    HEADLESS: bool = True
    BROWSER_TIMEOUT: int = 30
    PAGE_LOAD_WAIT: int = 5          # Fallback fixed wait if idle detection fails
    NETWORK_IDLE_MS: int = 1500      # Page is "idle" after this long with no new resources
    PAGE_IDLE_TIMEOUT: int = 20      # Max seconds to wait for idle before proceeding
    AUTO_SCROLL: bool = True         # Scroll through page to trigger lazy-loaded content
    STATIC_SNAPSHOT: bool = True     # Remove scripts so re-hydration can't break the saved DOM

    # Download settings
    REQUEST_TIMEOUT: int = 7
    MAX_RETRIES: int = 3
    MAX_WORKERS: int = 10  # Number of parallel download threads

    # Bulk clone settings
    MAX_CONCURRENT_CLONES: int = 2  # Number of pages to clone in parallel

    # Archive export settings
    EXPORT_WARC: bool = True         # Write capture.warc.gz alongside the file tree
    EXPORT_WACZ: bool = True         # Package WARC into capture.wacz (needs py-wacz)

    # Screenshot settings
    ENABLE_SCREENSHOTS: bool = True
    SCREENSHOT_FULLPAGE: bool = True
    SCREENSHOT_VIEWPORTS: list = None  # e.g., ["mobile", "desktop"]

    # User Agent
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    # File extensions to download
    ALLOWED_EXTENSIONS: tuple = (
        'css', 'js', 'jpeg', 'jpg', 'ico', 'png', 'img', 'bmp',
        'svg', 'gif', 'javascript', 'json', 'map', 'xml', 'woff',
        'woff2', 'ttf', 'eot', 'webp'
    )

    # Flask settings
    FLASK_HOST: str = "localhost"
    FLASK_PORT: int = 5000
    FLASK_DEBUG: bool = False

    def __post_init__(self):
        """Ensure project directory exists"""
        self.PROJECT_DIR.mkdir(exist_ok=True, parents=True)

    @classmethod
    def from_env(cls, env_file: Optional[Path] = None) -> "Config":
        """Create config from environment variables"""
        if env_file and env_file.exists():
            from dotenv import load_dotenv
            load_dotenv(env_file)

        # Parse screenshot viewports
        viewports_str = os.getenv("SCREENSHOT_VIEWPORTS", "")
        viewports = [v.strip() for v in viewports_str.split(",") if v.strip()] if viewports_str else None

        return cls(
            HEADLESS=os.getenv("HEADLESS", "true").lower() == "true",
            BROWSER_TIMEOUT=int(os.getenv("BROWSER_TIMEOUT", "30")),
            PAGE_LOAD_WAIT=int(os.getenv("PAGE_LOAD_WAIT", "5")),
            NETWORK_IDLE_MS=int(os.getenv("NETWORK_IDLE_MS", "1500")),
            PAGE_IDLE_TIMEOUT=int(os.getenv("PAGE_IDLE_TIMEOUT", "20")),
            AUTO_SCROLL=os.getenv("AUTO_SCROLL", "true").lower() == "true",
            STATIC_SNAPSHOT=os.getenv("STATIC_SNAPSHOT", "true").lower() == "true",
            EXPORT_WARC=os.getenv("EXPORT_WARC", "true").lower() == "true",
            EXPORT_WACZ=os.getenv("EXPORT_WACZ", "true").lower() == "true",
            REQUEST_TIMEOUT=int(os.getenv("REQUEST_TIMEOUT", "7")),
            MAX_WORKERS=int(os.getenv("MAX_WORKERS", "10")),
            MAX_CONCURRENT_CLONES=int(os.getenv("MAX_CONCURRENT_CLONES", "3")),
            ENABLE_SCREENSHOTS=os.getenv("ENABLE_SCREENSHOTS", "true").lower() == "true",
            SCREENSHOT_FULLPAGE=os.getenv("SCREENSHOT_FULLPAGE", "true").lower() == "true",
            SCREENSHOT_VIEWPORTS=viewports,
            FLASK_HOST=os.getenv("FLASK_HOST", "localhost"),
            FLASK_PORT=int(os.getenv("FLASK_PORT", "5000")),
            FLASK_DEBUG=os.getenv("FLASK_DEBUG", "false").lower() == "true",
        )


# Global config instance
config = Config()
