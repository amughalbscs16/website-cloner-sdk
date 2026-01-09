"""Modern Chrome driver setup with automatic driver management"""

import json
import tempfile
import uuid
from pathlib import Path
from typing import List, Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager as WDM
from ..config import config
from ..utils.logger import logger


class ChromeDriverManager:
    """Manages Chrome WebDriver with modern Selenium 4.x syntax"""

    def __init__(self, headless: bool = None):
        """
        Initialize Chrome driver manager

        Args:
            headless: Run in headless mode (default from config)
        """
        self.headless = headless if headless is not None else config.HEADLESS
        self.driver: Optional[webdriver.Chrome] = None
        # Create unique user data directory for this instance
        self.user_data_dir = Path(tempfile.mkdtemp(prefix=f"chrome_{uuid.uuid4().hex[:8]}_"))

    def _create_options(self) -> Options:
        """Create Chrome options with recommended settings"""
        options = Options()

        if self.headless:
            options.add_argument("--headless=new")  # Modern headless mode
            options.add_argument("--disable-gpu")

        # Use unique user data directory to avoid conflicts
        options.add_argument(f"--user-data-dir={str(self.user_data_dir)}")

        # Performance and stability options
        options.add_argument("--start-maximized")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")

        # Memory optimization options
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-breakpad")
        options.add_argument("--disable-component-extensions-with-background-pages")
        options.add_argument("--disable-features=TranslateUI,BlinkGenPropertyTrees")
        options.add_argument("--disable-ipc-flooding-protection")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--enable-features=NetworkService,NetworkServiceInProcess")
        options.add_argument("--force-color-profile=srgb")
        options.add_argument("--metrics-recording-only")
        options.add_argument("--mute-audio")

        # Reduce memory footprint
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-sync")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")

        # Set process limits
        options.add_argument("--renderer-process-limit=1")
        options.add_argument("--single-process")  # Use single process mode to reduce memory

        # Set user agent
        options.add_argument(f"user-agent={config.USER_AGENT}")

        # Enable performance logging for network capture
        options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

        # Suppress automation detection
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        return options

    def create_driver(self) -> webdriver.Chrome:
        """
        Create and return a Chrome WebDriver instance

        Returns:
            Configured Chrome WebDriver
        """
        try:
            options = self._create_options()

            # Auto-download and install ChromeDriver using webdriver-manager
            service = Service(WDM().install())
            driver = webdriver.Chrome(service=service, options=options)

            # Set timeouts
            driver.set_page_load_timeout(config.BROWSER_TIMEOUT)
            driver.implicitly_wait(5)

            # Additional stealth
            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        })
                    """
                },
            )

            self.driver = driver
            logger.info("Chrome driver initialized successfully")
            return driver

        except Exception as e:
            logger.error(f"Failed to create Chrome driver: {e}")
            raise

    def get_network_logs(self, driver: webdriver.Chrome = None) -> List[str]:
        """
        Extract URLs from browser performance logs

        Args:
            driver: WebDriver instance (uses self.driver if not provided)

        Returns:
            List of URLs from network requests
        """
        driver = driver or self.driver
        if not driver:
            logger.warning("No driver available for log extraction")
            return []

        try:
            browser_log = driver.get_log("performance")
            urls = set()

            for entry in browser_log:
                try:
                    message = json.loads(entry["message"])["message"]
                    if "params" in message and "request" in message["params"]:
                        url = message["params"]["request"].get("url")
                        if url:
                            urls.add(url)
                except (json.JSONDecodeError, KeyError):
                    continue

            logger.debug(f"Extracted {len(urls)} URLs from network logs")
            return list(urls)

        except Exception as e:
            logger.error(f"Failed to extract network logs: {e}")
            return []

    def close(self):
        """Close the driver safely and ensure all processes are terminated"""
        if self.driver:
            try:
                # Try to close all windows first
                try:
                    for handle in self.driver.window_handles:
                        self.driver.switch_to.window(handle)
                        self.driver.close()
                except:
                    pass

                # Quit the driver
                self.driver.quit()
                logger.info("Chrome driver closed")
            except Exception as e:
                logger.error(f"Error closing driver: {e}")
            finally:
                self.driver = None

        # Give processes time to terminate
        import time
        time.sleep(0.5)

        # Clean up user data directory
        if self.user_data_dir and self.user_data_dir.exists():
            try:
                import shutil
                # Wait a bit for Chrome to release file handles
                time.sleep(0.5)
                shutil.rmtree(self.user_data_dir, ignore_errors=True)
                logger.debug(f"Cleaned up user data directory: {self.user_data_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up user data directory: {e}")

    def __enter__(self):
        """Context manager entry"""
        return self.create_driver()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# Singleton instance for backward compatibility
_driver_manager: Optional[ChromeDriverManager] = None


def get_driver(headless: bool = None) -> webdriver.Chrome:
    """
    Get or create a Chrome driver instance

    Args:
        headless: Run in headless mode (default from config)

    Returns:
        Chrome WebDriver instance
    """
    global _driver_manager

    if _driver_manager is None or _driver_manager.driver is None:
        _driver_manager = ChromeDriverManager(headless=headless)
        return _driver_manager.create_driver()

    return _driver_manager.driver
