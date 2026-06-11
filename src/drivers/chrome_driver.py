"""Modern Chrome driver setup with automatic driver management"""

import base64
import json
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
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

            # Enlarge the DevTools response-body buffers so bodies survive until
            # we harvest them after page load (CDP evicts bodies under memory pressure)
            self.enable_network_capture(driver)

            self.driver = driver
            logger.info("Chrome driver initialized successfully")
            return driver

        except Exception as e:
            logger.error(f"Failed to create Chrome driver: {e}")
            raise

    def wait_for_page_idle(
        self,
        driver: webdriver.Chrome = None,
        idle_ms: int = 1500,
        timeout: float = 20.0,
        poll_interval: float = 0.25,
    ) -> bool:
        """
        Wait until the page looks finished: document complete and no new
        resources for idle_ms. Polls the Resource Timing API instead of the
        performance log because get_log() drains the buffer the CDP harvest
        needs afterwards.

        Returns:
            True if the page went idle, False if the timeout was hit
        """
        import time as _time

        driver = driver or self.driver
        deadline = _time.time() + timeout
        last_count = -1
        stable_since = _time.time()

        while _time.time() < deadline:
            try:
                state = driver.execute_script("return document.readyState")
                count = driver.execute_script(
                    "return performance.getEntriesByType('resource').length"
                )
            except Exception as e:
                logger.debug(f"Idle polling failed, falling back to fixed wait: {e}")
                return False

            if count != last_count:
                last_count = count
                stable_since = _time.time()
            elif state == "complete" and (_time.time() - stable_since) * 1000 >= idle_ms:
                logger.debug(f"Page idle after {count} resources")
                return True

            _time.sleep(poll_interval)

        logger.debug(f"Page idle timeout ({timeout}s) reached with {last_count} resources")
        return False

    def auto_scroll(
        self,
        driver: webdriver.Chrome = None,
        step_delay: float = 0.3,
        max_steps: int = 30,
    ) -> None:
        """
        Scroll viewport-by-viewport to the bottom to trigger lazy loading,
        then return to the top so screenshots and layout are unaffected.
        """
        import time as _time

        driver = driver or self.driver
        last_height = -1

        try:
            for _ in range(max_steps):
                height = driver.execute_script(
                    "return document.body ? document.body.scrollHeight : 0"
                )
                position = driver.execute_script(
                    "return window.scrollY + window.innerHeight"
                )
                if position >= height and height == last_height:
                    break
                last_height = height
                driver.execute_script("window.scrollBy(0, window.innerHeight);")
                _time.sleep(step_delay)

            driver.execute_script("window.scrollTo(0, 0);")
        except Exception as e:
            logger.debug(f"Auto-scroll aborted: {e}")

    def inline_runtime_styles(self, driver: webdriver.Chrome = None) -> int:
        """
        Serialize CSS-in-JS rules from the CSSOM back into their <style> elements.

        Frameworks like styled-components, emotion and styled-jsx inject CSS via
        the CSSOM (document.styleSheets[*].insertRule), leaving the <style>
        element's text content empty. driver.page_source serializes that empty
        element, so the saved clone loses all such styling. This reads the live
        rules and writes them back as text so the static HTML renders correctly.

        Returns:
            Number of <style> elements populated.
        """
        driver = driver or self.driver
        script = r"""
        let filled = 0;
        for (const sheet of Array.from(document.styleSheets)) {
            const node = sheet.ownerNode;
            // Only target <style> elements that are empty but hold live rules
            if (!node || node.tagName !== 'STYLE') continue;
            if (node.textContent && node.textContent.trim().length > 0) continue;
            let rules;
            try { rules = sheet.cssRules; } catch (e) { continue; }  // cross-origin
            if (!rules || rules.length === 0) continue;
            let css = '';
            for (const rule of Array.from(rules)) css += rule.cssText + '\n';
            if (css) { node.textContent = css; filled++; }
        }
        return filled;
        """
        try:
            filled = driver.execute_script(script)
            if filled:
                logger.info(f"Inlined {filled} runtime (CSS-in-JS) style blocks")
            return filled or 0
        except Exception as e:
            logger.warning(f"Could not inline runtime styles: {e}")
            return 0

    def neutralize_scripts(self, html: str) -> str:
        """
        Remove <script> tags from captured HTML for a static snapshot.

        Re-running a page's JavaScript from a saved copy often re-hydrates and
        destroys the captured DOM (React/Next.js), or fails on absent APIs.
        Removing scripts preserves the rendered, styled DOM as captured. Used
        in static-snapshot mode.
        """
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        removed = 0
        for tag in soup.find_all("script"):
            tag.decompose()
            removed += 1
        logger.info(f"Neutralized {removed} script tags (static snapshot mode)")
        return str(soup)

    def enable_network_capture(
        self,
        driver: webdriver.Chrome = None,
        max_total_mb: int = 256,
        max_resource_mb: int = 64,
    ) -> None:
        """
        Enable CDP Network domain with enlarged body buffers.

        Must run before navigation so response bodies are buffered for
        get_response_body(). Defaults give 256 MB total / 64 MB per resource.
        """
        driver = driver or self.driver
        try:
            driver.execute_cdp_cmd("Network.enable", {
                "maxTotalBufferSize": max_total_mb * 1024 * 1024,
                "maxResourceBufferSize": max_resource_mb * 1024 * 1024,
            })
            logger.debug("CDP network capture enabled with enlarged buffers")
        except Exception as e:
            logger.warning(f"Could not enable CDP network capture: {e}")

    def harvest_network(self, driver: webdriver.Chrome = None) -> Tuple[Set[str], Dict[str, Dict]]:
        """
        Parse the performance log once, returning both views of network activity.

        NOTE: get_log("performance") drains the log buffer, so this and
        get_network_logs() must not both be called for the same page load.

        Returns:
            Tuple of:
            - set of all requested URLs (from Network.requestWillBeSent)
            - dict url -> response metadata {request_id, status, headers,
              mime_type, resource_type} (from Network.responseReceived)
        """
        driver = driver or self.driver
        urls: Set[str] = set()
        responses: Dict[str, Dict] = {}

        if not driver:
            logger.warning("No driver available for network harvest")
            return urls, responses

        try:
            browser_log = driver.get_log("performance")
        except Exception as e:
            logger.error(f"Failed to read performance log: {e}")
            return urls, responses

        for entry in browser_log:
            try:
                message = json.loads(entry["message"])["message"]
                method = message.get("method", "")
                params = message.get("params", {})

                if method == "Network.requestWillBeSent":
                    url = params.get("request", {}).get("url")
                    if url:
                        urls.add(url)
                elif method == "Network.responseReceived":
                    response = params.get("response", {})
                    url = response.get("url")
                    if url and url.startswith(("http://", "https://")):
                        responses[url] = {
                            "request_id": params.get("requestId"),
                            "status": response.get("status"),
                            "headers": response.get("headers", {}),
                            "mime_type": response.get("mimeType", ""),
                            "resource_type": params.get("type", ""),
                        }
            except (json.JSONDecodeError, KeyError):
                continue

        logger.debug(f"Harvested {len(urls)} request URLs, {len(responses)} responses")
        return urls, responses

    def get_response_body(self, request_id: str, driver: webdriver.Chrome = None) -> Optional[bytes]:
        """
        Fetch the body the browser actually received for a request via CDP.

        Returns None when the body was evicted from the DevTools buffer or the
        request had no body (redirects, 204s, preflights) — callers fall back
        to re-fetching over HTTP.
        """
        driver = driver or self.driver
        if not driver or not request_id:
            return None

        try:
            result = driver.execute_cdp_cmd(
                "Network.getResponseBody", {"requestId": request_id}
            )
            body = result.get("body", "")
            if result.get("base64Encoded"):
                return base64.b64decode(body)
            return body.encode("utf-8")
        except Exception:
            return None

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
