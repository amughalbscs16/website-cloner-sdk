"""Tests for URL utilities"""

import pytest
from src.utils.url_utils import URLUtils


class TestURLUtils:
    """Test URL utility functions"""

    def test_clean_url_removes_whitespace(self):
        """Test that clean_url removes leading/trailing whitespace"""
        assert URLUtils.clean_url("  https://example.com  ") == "https://example.com"

    def test_clean_url_adds_https(self):
        """Test that clean_url adds https:// if missing"""
        assert URLUtils.clean_url("example.com").startswith("https://")

    def test_normalize_url_absolute(self):
        """Test normalizing an absolute URL"""
        base = "https://example.com"
        url = "https://example.com/image.jpg"
        assert URLUtils.normalize_url(base, url) == url

    def test_normalize_url_relative(self):
        """Test normalizing a relative URL"""
        base = "https://example.com/page"
        url = "/image.jpg"
        result = URLUtils.normalize_url(base, url)
        assert result == "https://example.com/image.jpg"

    def test_normalize_url_protocol_relative(self):
        """Test normalizing a protocol-relative URL"""
        base = "https://example.com"
        url = "//cdn.example.com/script.js"
        result = URLUtils.normalize_url(base, url)
        assert result == "https://cdn.example.com/script.js"

    def test_get_domain(self):
        """Test extracting domain from URL"""
        url = "https://example.com/path/to/page"
        assert URLUtils.get_domain(url) == "https://example.com"

    def test_is_external_url_same_domain(self):
        """Test that same domain is not external"""
        base = "https://example.com"
        url = "https://example.com/page"
        assert not URLUtils.is_external_url(base, url)

    def test_is_external_url_different_domain(self):
        """Test that different domain is external"""
        base = "https://example.com"
        url = "https://other.com/page"
        assert URLUtils.is_external_url(base, url)
