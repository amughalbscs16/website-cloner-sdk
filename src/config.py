"""Configuration management for WordPress Cloner"""

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
    PAGE_LOAD_WAIT: int = 5

    # Download settings
    REQUEST_TIMEOUT: int = 7
    MAX_RETRIES: int = 3
    MAX_WORKERS: int = 10  # Number of parallel download threads

    # Bulk clone settings
    MAX_CONCURRENT_CLONES: int = 2  # Number of pages to clone in parallel

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
