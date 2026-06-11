"""CDP response-body harvesting.

Captures the bytes the browser actually received instead of re-fetching
resources out-of-band. Re-fetching breaks session-gated resources (cookies,
CSRF state) and can return different bytes than the page saw; in-browser CDP
capture is the architecture Browsertrix Crawler adopted for the same reason
(browsertrix-crawler PR #424).
"""

from dataclasses import dataclass, field
from typing import Dict, Set, Tuple

from ..utils.logger import logger


@dataclass
class CapturedResource:
    """A resource body captured from the browser via CDP"""
    url: str
    content: bytes
    status: int = 200
    mime_type: str = ""
    resource_type: str = ""
    headers: Dict[str, str] = field(default_factory=dict)


def harvest_captured_resources(
    driver_manager,
    driver=None,
) -> Tuple[Set[str], Dict[str, CapturedResource]]:
    """
    Harvest all response bodies still buffered in the browser.

    Must run while the page is still loaded — navigating away evicts bodies.

    Args:
        driver_manager: ChromeDriverManager instance
        driver: WebDriver (defaults to driver_manager.driver)

    Returns:
        Tuple of:
        - set of every URL the page requested (for discovery/recall accounting)
        - dict url -> CapturedResource for bodies successfully pulled via CDP
    """
    urls, responses = driver_manager.harvest_network(driver)
    captured: Dict[str, CapturedResource] = {}
    evicted = 0

    for url, meta in responses.items():
        status = meta.get("status") or 0
        if not (200 <= status < 300):
            continue

        body = driver_manager.get_response_body(meta.get("request_id"), driver)
        if body is None:
            evicted += 1
            continue

        captured[url] = CapturedResource(
            url=url,
            content=body,
            status=status,
            mime_type=meta.get("mime_type", ""),
            resource_type=meta.get("resource_type", ""),
            headers=meta.get("headers", {}),
        )

    logger.info(
        f"CDP capture: {len(captured)} bodies captured in-browser, "
        f"{evicted} evicted (will re-fetch), {len(urls)} URLs requested"
    )
    return urls, captured
