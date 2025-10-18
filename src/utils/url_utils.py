"""URL manipulation utilities"""

from typing import Optional
from urllib.parse import urljoin, urlparse


class URLUtils:
    """Utilities for URL manipulation"""

    @staticmethod
    def clean_url(url: str) -> str:
        """Remove trailing slashes from URL"""
        while url.endswith('/'):
            url = url[:-1]
        return url

    @staticmethod
    def normalize_url(base_url: str, resource_url: str) -> str:
        """
        Normalize a resource URL relative to base URL

        Args:
            base_url: The base website URL
            resource_url: The resource URL (may be relative or absolute)

        Returns:
            Normalized absolute URL
        """
        if not resource_url or resource_url.strip() in ("", " "):
            return resource_url

        # Handle protocol-relative URLs
        if resource_url.startswith("//"):
            return f"http:{resource_url}"

        # Already absolute URL
        if resource_url.startswith(('http://', 'https://')):
            return resource_url

        # Data URIs
        if resource_url.startswith('data:'):
            return resource_url

        # Relative URLs
        if resource_url.startswith('/'):
            # Absolute path
            parsed = urlparse(base_url)
            return f"{parsed.scheme}://{parsed.netloc}{resource_url}"
        elif resource_url.startswith('.'):
            # Relative path with dots
            return urljoin(base_url + '/', resource_url)
        else:
            # Simple relative path
            return urljoin(base_url + '/', resource_url)

    @staticmethod
    def get_domain(url: str) -> str:
        """Extract domain from URL"""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    @staticmethod
    def is_valid_resource_url(url: str, allowed_extensions: tuple) -> bool:
        """Check if URL points to a downloadable resource"""
        if not url or url.startswith('data:'):
            return False

        # Check if URL contains any allowed extension
        url_lower = url.lower().split('?')[0]
        return any(url_lower.endswith(f'.{ext}') for ext in allowed_extensions)
