"""WordPress detection module"""

import re
import requests
from typing import Dict, Optional, List
from urllib.parse import urljoin, urlparse
from loguru import logger


class WordPressDetector:
    """Detects if a website is running WordPress"""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def is_wordpress(self, url: str) -> Dict:
        """
        Detect if a site is WordPress and gather information

        Returns:
            Dict with keys:
                - is_wordpress: bool
                - confidence: float (0-1)
                - indicators: List[str]
                - version: Optional[str]
                - theme: Optional[str]
                - plugins: List[str]
        """
        logger.info(f"Detecting WordPress for: {url}")

        result = {
            "is_wordpress": False,
            "confidence": 0.0,
            "indicators": [],
            "version": None,
            "theme": None,
            "plugins": [],
            "api_available": False,
            "rest_api_url": None,
        }

        # Ensure URL has scheme
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'

        try:
            # Check main page
            response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            html = response.text

            # Check various WordPress indicators
            indicators = []
            confidence = 0.0

            # 1. Check for wp-content in HTML
            if '/wp-content/' in html:
                indicators.append("wp-content directory found")
                confidence += 0.3

            # 2. Check for wp-includes
            if '/wp-includes/' in html:
                indicators.append("wp-includes directory found")
                confidence += 0.3

            # 3. Check meta generator
            generator_match = re.search(r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']WordPress[^"\']*["\']', html, re.IGNORECASE)
            if generator_match:
                indicators.append("WordPress meta generator tag found")
                confidence += 0.4

                # Extract version
                version_match = re.search(r'WordPress\s+([\d.]+)', generator_match.group(), re.IGNORECASE)
                if version_match:
                    result["version"] = version_match.group(1)

            # 4. Check for WordPress REST API
            rest_api_url = urljoin(url, '/wp-json/')
            try:
                api_response = self.session.get(rest_api_url, timeout=5)
                if api_response.status_code == 200:
                    api_data = api_response.json()
                    if 'namespaces' in api_data or 'routes' in api_data:
                        indicators.append("WordPress REST API detected")
                        confidence += 0.5
                        result["api_available"] = True
                        result["rest_api_url"] = rest_api_url
            except:
                pass

            # 5. Check for common WordPress files
            wp_files = [
                '/wp-login.php',
                '/wp-admin/',
                '/xmlrpc.php',
            ]

            for wp_file in wp_files:
                try:
                    file_url = urljoin(url, wp_file)
                    file_response = self.session.head(file_url, timeout=3, allow_redirects=True)
                    if file_response.status_code in [200, 302, 403]:
                        indicators.append(f"{wp_file} accessible")
                        confidence += 0.2
                        break  # One is enough
                except:
                    pass

            # 6. Check for theme
            theme_match = re.search(r'/wp-content/themes/([^/\'"]+)', html)
            if theme_match:
                result["theme"] = theme_match.group(1)
                indicators.append(f"Theme detected: {result['theme']}")

            # 7. Check for plugins
            plugin_matches = re.findall(r'/wp-content/plugins/([^/\'"]+)', html)
            if plugin_matches:
                result["plugins"] = list(set(plugin_matches))[:10]  # Limit to 10
                indicators.append(f"{len(result['plugins'])} plugins detected")

            # Cap confidence at 1.0
            confidence = min(confidence, 1.0)

            # Determine if WordPress (confidence > 0.5)
            result["is_wordpress"] = confidence >= 0.5
            result["confidence"] = round(confidence, 2)
            result["indicators"] = indicators

            if result["is_wordpress"]:
                logger.success(f"✓ WordPress detected with {confidence:.0%} confidence")
            else:
                logger.info(f"✗ Not WordPress (confidence: {confidence:.0%})")

            return result

        except requests.RequestException as e:
            logger.error(f"Error detecting WordPress: {e}")
            return result

    def get_rest_api_info(self, url: str) -> Optional[Dict]:
        """Get WordPress REST API information"""
        rest_api_url = urljoin(url, '/wp-json/')

        try:
            response = self.session.get(rest_api_url, timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
        except:
            pass

        return None
