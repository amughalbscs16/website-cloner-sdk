"""CSS asset downloader for extracting and downloading url() resources"""

import re
from pathlib import Path
from typing import List, Set
from ..config import config
from ..utils.logger import logger
from ..utils.url_utils import URLUtils
from ..utils.file_utils import FileManager
from .resource_downloader import ResourceDownloader


class CSSAssetDownloader:
    """Extracts and downloads assets from CSS files"""

    # Regex to find url(...) in CSS
    URL_PATTERN = re.compile(r'url\(["\']?([^"\')]+)["\']?\)', re.IGNORECASE)

    def __init__(self, file_manager: FileManager, resource_downloader: ResourceDownloader):
        """
        Initialize CSS asset downloader

        Args:
            file_manager: FileManager instance
            resource_downloader: ResourceDownloader instance
        """
        self.file_manager = file_manager
        self.resource_downloader = resource_downloader

    def extract_and_download_css_assets(
        self,
        project_path: Path,
        css_file_path: Path,
        css_url: str,
    ) -> str:
        """
        Extract and download assets from CSS file

        Args:
            project_path: Project root directory
            css_file_path: Path to CSS file on disk
            css_url: Original URL of the CSS file

        Returns:
            Modified CSS content
        """
        try:
            # Read CSS content
            content = self.file_manager.read_file(css_file_path)
            if not content:
                return content

            # Get base URL for relative paths
            base_url = "/".join(css_url.split("/")[:-1])

            # Find all url() declarations
            modified_content = content

            for match in self.URL_PATTERN.finditer(content):
                resource_url = match.group(1).strip()

                # Skip data URIs and empty urls
                if not resource_url or resource_url.startswith("data:"):
                    continue

                # Normalize URL
                absolute_url = URLUtils.normalize_url(base_url, resource_url)

                # Download the resource
                local_path = self.resource_downloader.download_file(
                    base_url, absolute_url, project_path
                )

                # Replace in CSS content
                if local_path != absolute_url:
                    modified_content = modified_content.replace(
                        match.group(0), f'url({local_path})'
                    )

            # Save modified CSS
            if modified_content != content:
                css_file_path.write_text(modified_content, encoding='utf-8')
                logger.debug(f"Updated CSS file: {css_file_path}")

            return modified_content

        except Exception as e:
            logger.error(f"Error processing CSS file {css_file_path}: {e}")
            return ""

    def process_inline_css(
        self,
        project_path: Path,
        html_content: str,
        base_url: str,
    ) -> str:
        """
        Process inline CSS in HTML content

        Args:
            project_path: Project root directory
            html_content: HTML content as string
            base_url: Base URL of the page

        Returns:
            Modified HTML content
        """
        try:
            modified_content = html_content

            # Find style tags
            style_pattern = re.compile(
                r'<style[^>]*>(.*?)</style>',
                re.IGNORECASE | re.DOTALL
            )

            for match in style_pattern.finditer(html_content):
                css_content = match.group(1)
                modified_css = self._process_css_urls(
                    css_content, base_url, project_path
                )

                if modified_css != css_content:
                    modified_content = modified_content.replace(
                        match.group(0),
                        match.group(0).replace(css_content, modified_css)
                    )

            return modified_content

        except Exception as e:
            logger.error(f"Error processing inline CSS: {e}")
            return html_content

    def _process_css_urls(
        self,
        css_content: str,
        base_url: str,
        project_path: Path
    ) -> str:
        """Process url() declarations in CSS content"""
        modified_content = css_content

        for match in self.URL_PATTERN.finditer(css_content):
            resource_url = match.group(1).strip()

            if not resource_url or resource_url.startswith("data:"):
                continue

            absolute_url = URLUtils.normalize_url(base_url, resource_url)
            local_path = self.resource_downloader.download_file(
                base_url, absolute_url, project_path
            )

            if local_path != absolute_url:
                modified_content = modified_content.replace(
                    match.group(0), f'url({local_path})'
                )

        return modified_content
