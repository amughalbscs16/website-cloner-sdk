"""HTML parsing and asset extraction"""

import re
from pathlib import Path
from typing import Set
from bs4 import BeautifulSoup
from ..utils.logger import logger
from ..downloaders.resource_downloader import ResourceDownloader


class HTMLParser:
    """Parses HTML and downloads all assets"""

    # link rel values that reference downloadable assets. Other rels
    # (canonical, alternate, preconnect, dns-prefetch, next/prev, ...) point
    # at pages or hosts and must keep their original URLs.
    ASSET_LINK_RELS = {
        "stylesheet", "icon", "shortcut", "apple-touch-icon",
        "apple-touch-icon-precomposed", "mask-icon", "manifest",
        "preload", "modulepreload", "prefetch",
    }

    # Lazy-loader attribute names commonly used in place of src/srcset
    LAZY_ATTRS = ("data-src", "data-lazy-src", "data-original")
    LAZY_SRCSET_ATTRS = ("data-srcset", "data-lazy-srcset")

    CSS_URL_PATTERN = re.compile(r'url\(["\']?([^"\')]+)["\']?\)', re.IGNORECASE)

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
        self._process_media(soup, base_url, project_path)
        self._process_scripts(soup, base_url, project_path)
        self._process_meta(soup, base_url, project_path)
        self._process_style_attributes(soup, base_url, project_path)
        self._process_style_blocks(soup, base_url, project_path)

        logger.info("Processed all HTML assets")
        return soup.encode('utf-8').decode('utf-8')

    def _is_asset_link(self, link) -> bool:
        """True when a <link> tag's rel references a downloadable asset"""
        rels = link.get('rel') or []
        if isinstance(rels, str):
            rels = rels.split()
        return any(r.lower() in self.ASSET_LINK_RELS for r in rels)

    def _process_links(self, soup: BeautifulSoup, base_url: str, project_path: Path) -> None:
        """Process <link> tags that reference assets (CSS, icons, fonts, ...)"""
        links = soup.find_all('link', href=True)
        logger.debug(f"Processing {len(links)} link tags")

        for link in links:
            try:
                if not self._is_asset_link(link):
                    continue  # canonical/alternate/preconnect keep their URL
                original_href = link['href']
                local_path = self.downloader.download_file(
                    base_url, original_href, project_path
                )
                link['href'] = local_path
            except Exception as e:
                logger.debug(f"Error processing link {link.get('href')}: {e}")

    def _process_images(self, soup: BeautifulSoup, base_url: str, project_path: Path) -> None:
        """Process <img> tags including srcset and lazy-loading attributes"""
        images = soup.find_all('img')
        logger.debug(f"Processing {len(images)} image tags")

        for img in images:
            try:
                if img.get('src'):
                    img['src'] = self.downloader.download_file(
                        base_url, img['src'], project_path
                    )

                if img.get('srcset'):
                    img['srcset'] = self._process_srcset(
                        img['srcset'], base_url, project_path
                    )

                # Lazy loaders keep the real URL in data-* attributes
                for attr in self.LAZY_ATTRS:
                    if img.get(attr):
                        local = self.downloader.download_file(
                            base_url, img[attr], project_path
                        )
                        img[attr] = local
                        if not img.get('src'):
                            img['src'] = local
                for attr in self.LAZY_SRCSET_ATTRS:
                    if img.get(attr):
                        img[attr] = self._process_srcset(
                            img[attr], base_url, project_path
                        )
            except Exception as e:
                logger.debug(f"Error processing image {img.get('src')}: {e}")

    def _process_media(self, soup: BeautifulSoup, base_url: str, project_path: Path) -> None:
        """Process <source>, <video>, <audio> elements"""
        sources = soup.find_all('source')
        for source in sources:
            try:
                if source.get('src'):
                    source['src'] = self.downloader.download_file(
                        base_url, source['src'], project_path
                    )
                if source.get('srcset'):
                    source['srcset'] = self._process_srcset(
                        source['srcset'], base_url, project_path
                    )
            except Exception as e:
                logger.debug(f"Error processing source element: {e}")

        for media in soup.find_all(['video', 'audio']):
            try:
                if media.get('src'):
                    media['src'] = self.downloader.download_file(
                        base_url, media['src'], project_path
                    )
                if media.get('poster'):
                    media['poster'] = self.downloader.download_file(
                        base_url, media['poster'], project_path
                    )
            except Exception as e:
                logger.debug(f"Error processing media element: {e}")

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

    def _rewrite_css_urls(self, css_text: str, base_url: str, project_path: Path) -> str:
        """Download url(...) references in CSS text and rewrite them locally"""
        modified = css_text
        for match in self.CSS_URL_PATTERN.finditer(css_text):
            resource_url = match.group(1).strip()
            if not resource_url or resource_url.startswith(('data:', '#')):
                continue
            local_path = self.downloader.download_file(
                base_url, resource_url, project_path
            )
            if local_path != resource_url:
                modified = modified.replace(match.group(0), f'url({local_path})')
        return modified

    def _process_style_attributes(self, soup: BeautifulSoup, base_url: str, project_path: Path) -> None:
        """Process inline style="...url(...)" attributes (background images)"""
        styled = [el for el in soup.find_all(style=True) if 'url(' in el['style']]
        logger.debug(f"Processing {len(styled)} inline style attributes")

        for el in styled:
            try:
                el['style'] = self._rewrite_css_urls(el['style'], base_url, project_path)
            except Exception as e:
                logger.debug(f"Error processing style attribute: {e}")

    def _process_style_blocks(self, soup: BeautifulSoup, base_url: str, project_path: Path) -> None:
        """Process <style> blocks embedded in the page"""
        blocks = [st for st in soup.find_all('style') if st.string and 'url(' in st.string]
        logger.debug(f"Processing {len(blocks)} style blocks")

        for st in blocks:
            try:
                st.string.replace_with(
                    self._rewrite_css_urls(st.string, base_url, project_path)
                )
            except Exception as e:
                logger.debug(f"Error processing style block: {e}")

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
