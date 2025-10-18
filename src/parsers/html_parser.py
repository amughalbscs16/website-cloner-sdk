"""HTML parsing and asset extraction"""

from pathlib import Path
from typing import Set
from bs4 import BeautifulSoup
from ..utils.logger import logger
from ..downloaders.resource_downloader import ResourceDownloader


class HTMLParser:
    """Parses HTML and downloads all assets"""

    def __init__(self, resource_downloader: ResourceDownloader):
        """
        Initialize HTML parser

        Args:
            resource_downloader: ResourceDownloader instance
        """
        self.downloader = resource_downloader

    def process_html(
        self,
        html_content: str,
        base_url: str,
        project_path: Path,
    ) -> str:
        """
        Process HTML content and download all assets

        Args:
            html_content: Raw HTML content
            base_url: Base URL of the page
            project_path: Project directory path

        Returns:
            Modified HTML with local asset paths
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        # Download favicon first
        self.downloader.download_favicon(base_url, project_path)

        # Process different asset types
        self._process_links(soup, base_url, project_path)
        self._process_images(soup, base_url, project_path)
        self._process_scripts(soup, base_url, project_path)
        self._process_meta(soup, base_url, project_path)

        logger.info("Processed all HTML assets")
        return soup.encode('utf-8').decode('utf-8')

    def _process_links(self, soup: BeautifulSoup, base_url: str, project_path: Path) -> None:
        """Process <link> tags (CSS, icons, etc.)"""
        links = soup.find_all('link', href=True)
        logger.debug(f"Processing {len(links)} link tags")

        for link in links:
            try:
                original_href = link['href']
                local_path = self.downloader.download_file(
                    base_url, original_href, project_path
                )
                link['href'] = local_path
            except Exception as e:
                logger.debug(f"Error processing link {link.get('href')}: {e}")

    def _process_images(self, soup: BeautifulSoup, base_url: str, project_path: Path) -> None:
        """Process <img> tags"""
        images = soup.find_all('img', src=True)
        logger.debug(f"Processing {len(images)} image tags")

        for img in images:
            try:
                original_src = img['src']
                local_path = self.downloader.download_file(
                    base_url, original_src, project_path
                )
                img['src'] = local_path

                # Also process srcset if present
                if img.get('srcset'):
                    img['srcset'] = self._process_srcset(
                        img['srcset'], base_url, project_path
                    )
            except Exception as e:
                logger.debug(f"Error processing image {img.get('src')}: {e}")

    def _process_scripts(self, soup: BeautifulSoup, base_url: str, project_path: Path) -> None:
        """Process <script> tags with src attribute"""
        scripts = soup.find_all('script', src=True)
        logger.debug(f"Processing {len(scripts)} script tags")

        for script in scripts:
            try:
                original_src = script['src']
                local_path = self.downloader.download_file(
                    base_url, original_src, project_path
                )
                script['src'] = local_path
            except Exception as e:
                logger.debug(f"Error processing script {script.get('src')}: {e}")

    def _process_meta(self, soup: BeautifulSoup, base_url: str, project_path: Path) -> None:
        """Process <meta> tags with content URLs"""
        meta_tags = soup.find_all('meta', content=True)
        logger.debug(f"Processing {len(meta_tags)} meta tags")

        for meta in meta_tags:
            try:
                content = meta['content']
                # Check if content looks like a URL
                if content.startswith(('http://', 'https://', '//', '/')):
                    local_path = self.downloader.download_file(
                        base_url, content, project_path
                    )
                    meta['content'] = local_path
            except Exception as e:
                logger.debug(f"Error processing meta tag: {e}")

    def _process_srcset(self, srcset: str, base_url: str, project_path: Path) -> str:
        """
        Process srcset attribute

        Args:
            srcset: srcset attribute value
            base_url: Base URL
            project_path: Project path

        Returns:
            Modified srcset with local paths
        """
        # srcset format: "url1 1x, url2 2x" or "url1 100w, url2 200w"
        entries = [entry.strip() for entry in srcset.split(',')]
        modified_entries = []

        for entry in entries:
            parts = entry.split()
            if len(parts) >= 1:
                url = parts[0]
                descriptor = parts[1] if len(parts) > 1 else ""

                local_path = self.downloader.download_file(base_url, url, project_path)
                modified_entry = f"{local_path} {descriptor}".strip()
                modified_entries.append(modified_entry)

        return ", ".join(modified_entries)
