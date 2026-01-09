"""Sitemap and robots.txt parser"""

import re
import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, urlparse
from loguru import logger
from concurrent.futures import ThreadPoolExecutor, as_completed


class SitemapParser:
    """Parse robots.txt and sitemaps to discover URLs"""

    def __init__(self, timeout: int = 10, max_workers: int = 10):
        self.timeout = timeout
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def get_robots_txt(self, url: str) -> Optional[str]:
        """Fetch robots.txt content"""
        robots_url = urljoin(url, '/robots.txt')

        try:
            logger.info(f"Fetching robots.txt from: {robots_url}")
            response = self.session.get(robots_url, timeout=self.timeout)

            if response.status_code == 200:
                logger.success(f"✓ Found robots.txt")
                return response.text

            logger.warning(f"robots.txt not found (status: {response.status_code})")
            return None

        except requests.RequestException as e:
            logger.error(f"Error fetching robots.txt: {e}")
            return None

    def parse_robots_txt(self, robots_content: str) -> Dict[str, List[str]]:
        """
        Parse robots.txt content

        Returns:
            Dict with keys:
                - sitemaps: List[str] - Sitemap URLs
                - disallowed: List[str] - Disallowed paths
                - allowed: List[str] - Allowed paths
        """
        result = {
            "sitemaps": [],
            "disallowed": [],
            "allowed": [],
        }

        if not robots_content:
            return result

        for line in robots_content.split('\n'):
            line = line.strip()

            # Sitemap directive
            if line.lower().startswith('sitemap:'):
                sitemap_url = line.split(':', 1)[1].strip()
                result["sitemaps"].append(sitemap_url)

            # Disallow directive
            elif line.lower().startswith('disallow:'):
                path = line.split(':', 1)[1].strip()
                if path:
                    result["disallowed"].append(path)

            # Allow directive
            elif line.lower().startswith('allow:'):
                path = line.split(':', 1)[1].strip()
                if path:
                    result["allowed"].append(path)

        logger.info(f"Found {len(result['sitemaps'])} sitemaps in robots.txt")
        return result

    def fetch_sitemap(self, sitemap_url: str) -> Optional[str]:
        """Fetch sitemap XML content"""
        try:
            logger.info(f"Fetching sitemap: {sitemap_url}")
            response = self.session.get(sitemap_url, timeout=self.timeout)

            if response.status_code == 200:
                return response.text

            logger.warning(f"Sitemap not found: {sitemap_url} (status: {response.status_code})")
            return None

        except requests.RequestException as e:
            logger.error(f"Error fetching sitemap: {e}")
            return None

    def parse_sitemap(self, sitemap_content: str) -> List[Dict]:
        """
        Parse sitemap XML and extract URLs

        Returns:
            List of dicts with keys:
                - url: str
                - title: Optional[str]
                - lastmod: Optional[str]
                - changefreq: Optional[str]
                - priority: Optional[str]
        """
        urls = []

        if not sitemap_content:
            return urls

        try:
            # Remove namespace for easier parsing
            sitemap_content = re.sub(r'xmlns="[^"]+"', '', sitemap_content)

            root = ET.fromstring(sitemap_content)

            # Check if this is a sitemap index
            sitemaps = root.findall('.//sitemap')
            if sitemaps:
                logger.info(f"Found sitemap index with {len(sitemaps)} sub-sitemaps")
                # Return sub-sitemap URLs
                for sitemap in sitemaps:
                    loc = sitemap.find('loc')
                    if loc is not None and loc.text:
                        urls.append({
                            "url": loc.text,
                            "type": "sitemap",
                        })
                return urls

            # Check if this is an RSS/Atom feed
            items = root.findall('.//item')
            if items:
                logger.info(f"Found RSS feed with {len(items)} items")
                return self._parse_rss_feed(root)

            entries = root.findall('.//entry')
            if entries:
                logger.info(f"Found Atom feed with {len(entries)} entries")
                return self._parse_atom_feed(root)

            # Parse regular sitemap URLs
            url_elements = root.findall('.//url')

            for url_elem in url_elements:
                loc = url_elem.find('loc')
                if loc is not None and loc.text:
                    url_data = {"url": loc.text}

                    # Optional fields
                    lastmod = url_elem.find('lastmod')
                    if lastmod is not None and lastmod.text:
                        url_data["lastmod"] = lastmod.text

                    changefreq = url_elem.find('changefreq')
                    if changefreq is not None and changefreq.text:
                        url_data["changefreq"] = changefreq.text

                    priority = url_elem.find('priority')
                    if priority is not None and priority.text:
                        url_data["priority"] = priority.text

                    urls.append(url_data)

            logger.success(f"✓ Parsed {len(urls)} URLs from sitemap")

        except ET.ParseError as e:
            logger.error(f"Error parsing sitemap XML: {e}")

        return urls

    def _parse_rss_feed(self, root: ET.Element) -> List[Dict]:
        """Parse RSS feed and extract URLs with titles"""
        urls = []
        items = root.findall('.//item')

        for item in items:
            link = item.find('link')
            title = item.find('title')
            pub_date = item.find('pubDate')

            if link is not None and link.text:
                url_data = {"url": link.text}

                if title is not None and title.text:
                    url_data["title"] = title.text

                if pub_date is not None and pub_date.text:
                    url_data["lastmod"] = pub_date.text

                urls.append(url_data)

        logger.success(f"✓ Parsed {len(urls)} URLs from RSS feed")
        return urls

    def _parse_atom_feed(self, root: ET.Element) -> List[Dict]:
        """Parse Atom feed and extract URLs with titles"""
        urls = []
        entries = root.findall('.//entry')

        for entry in entries:
            link = entry.find('link')
            title = entry.find('title')
            updated = entry.find('updated')

            if link is not None and link.get('href'):
                url_data = {"url": link.get('href')}

                if title is not None and title.text:
                    url_data["title"] = title.text

                if updated is not None and updated.text:
                    url_data["lastmod"] = updated.text

                urls.append(url_data)

        logger.success(f"✓ Parsed {len(urls)} URLs from Atom feed")
        return urls

    def discover_all_urls(self, base_url: str) -> List[Dict]:
        """
        Discover all URLs from robots.txt and sitemaps

        Returns:
            List of URL dicts with metadata
        """
        all_urls = []
        processed_sitemaps: Set[str] = set()

        # Ensure base URL has scheme
        if not base_url.startswith(('http://', 'https://')):
            base_url = f'https://{base_url}'

        # Step 1: Get robots.txt
        robots_content = self.get_robots_txt(base_url)

        if robots_content:
            robots_data = self.parse_robots_txt(robots_content)
            sitemap_urls = robots_data["sitemaps"]
            logger.info(f"Found {len(sitemap_urls)} sitemaps in robots.txt")
        else:
            # Try common sitemap locations in parallel
            sitemap_urls = self._discover_sitemaps_parallel(base_url)

        if not sitemap_urls:
            logger.warning("No sitemaps found")
            return all_urls

        # Step 2: Process all sitemaps (including nested ones) in parallel
        all_urls = self._process_sitemaps_parallel(sitemap_urls, processed_sitemaps)

        logger.success(f"✓ Total URLs discovered: {len(all_urls)}")
        return all_urls

    def _parse_html_for_sitemaps(self, base_url: str) -> List[str]:
        """Parse HTML homepage for sitemap references in link tags"""
        found_sitemaps = []
        try:
            logger.info(f"Parsing HTML at {base_url} for sitemap references...")
            response = self.session.get(base_url, timeout=self.timeout)
            if response.status_code == 200:
                # Look for <link rel="sitemap"> tags
                sitemap_links = re.findall(
                    r'<link[^>]*rel=["\']sitemap["\'][^>]*href=["\']([^"\']+)["\']',
                    response.text,
                    re.IGNORECASE
                )
                sitemap_links += re.findall(
                    r'<link[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\']sitemap["\']',
                    response.text,
                    re.IGNORECASE
                )

                for link in sitemap_links:
                    full_url = urljoin(base_url, link)
                    if full_url not in found_sitemaps:
                        found_sitemaps.append(full_url)
                        logger.info(f"  Found sitemap in HTML: {full_url}")
        except Exception as e:
            logger.debug(f"Could not parse HTML for sitemaps: {e}")

        return found_sitemaps

    def _discover_sitemaps_parallel(self, base_url: str) -> List[str]:
        """Try common sitemap locations in parallel"""
        candidate_urls = [
            # Standard sitemap locations
            urljoin(base_url, '/sitemap.xml'),
            urljoin(base_url, '/sitemap_index.xml'),
            urljoin(base_url, '/sitemap-index.xml'),
            urljoin(base_url, '/sitemap.xml.gz'),
            urljoin(base_url, '/sitemap1.xml'),
            urljoin(base_url, '/sitemaps.xml'),
            urljoin(base_url, '/sitemap/sitemap.xml'),
            urljoin(base_url, '/sitemap/index.xml'),

            # WordPress-specific sitemaps
            urljoin(base_url, '/wp-sitemap.xml'),
            urljoin(base_url, '/wp-sitemap-posts-post-1.xml'),
            urljoin(base_url, '/wp-sitemap-pages-1.xml'),

            # Yoast SEO plugin
            urljoin(base_url, '/sitemap_index.xml'),
            urljoin(base_url, '/post-sitemap.xml'),
            urljoin(base_url, '/page-sitemap.xml'),
            urljoin(base_url, '/category-sitemap.xml'),
            urljoin(base_url, '/tag-sitemap.xml'),
            urljoin(base_url, '/author-sitemap.xml'),

            # All in One SEO plugin
            urljoin(base_url, '/sitemap.rss'),
            urljoin(base_url, '/sitemap.html'),

            # Rank Math plugin
            urljoin(base_url, '/sitemap_index.xml'),

            # Google News Sitemap
            urljoin(base_url, '/news-sitemap.xml'),
            urljoin(base_url, '/sitemap-news.xml'),

            # Video Sitemap
            urljoin(base_url, '/video-sitemap.xml'),
            urljoin(base_url, '/sitemap-video.xml'),

            # Image Sitemap
            urljoin(base_url, '/image-sitemap.xml'),
            urljoin(base_url, '/sitemap-image.xml'),

            # Localized sitemaps
            urljoin(base_url, '/sitemap-en.xml'),
            urljoin(base_url, '/sitemap-us.xml'),

            # RSS/Atom feeds
            urljoin(base_url, '/feed/'),
            urljoin(base_url, '/rss.xml'),
            urljoin(base_url, '/atom.xml'),
            urljoin(base_url, '/rss/'),
            urljoin(base_url, '/index.xml'),
        ]

        # First, try to parse HTML for sitemap references
        html_sitemaps = self._parse_html_for_sitemaps(base_url)

        logger.info(f"Checking {len(candidate_urls)} common sitemap/feed locations in parallel...")

        found_sitemaps = []

        def check_url(url):
            try:
                response = self.session.head(url, timeout=5, allow_redirects=True)
                if response.status_code == 200:
                    logger.info(f"✓ Found: {url}")
                    return url
            except:
                pass
            return None

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(check_url, url): url for url in candidate_urls}

            for future in as_completed(futures):
                result = future.result()
                if result:
                    found_sitemaps.append(result)

        # Combine HTML-found sitemaps with discovered ones
        all_sitemaps = list(set(html_sitemaps + found_sitemaps))

        logger.success(f"✓ Found {len(all_sitemaps)} sitemaps/feeds ({len(html_sitemaps)} from HTML, {len(found_sitemaps)} from common locations)")
        return all_sitemaps

    def _process_sitemaps_parallel(self, sitemap_urls: List[str], processed: Set[str]) -> List[Dict]:
        """Process multiple sitemaps in parallel with source tracking"""
        all_urls = []
        sitemaps_to_process = sitemap_urls.copy()
        depth = 0

        while sitemaps_to_process:
            depth += 1
            logger.info(f"Processing level {depth} sitemaps ({len(sitemaps_to_process)} to process)...")

            # Process batch in parallel
            batch = []
            for sitemap_url in sitemaps_to_process[:]:
                if sitemap_url not in processed:
                    batch.append(sitemap_url)
                    processed.add(sitemap_url)
                    sitemaps_to_process.remove(sitemap_url)

            if not batch:
                logger.info(f"No more sitemaps to process at level {depth}")
                break

            logger.info(f"Level {depth}: Processing {len(batch)} sitemaps in parallel...")

            def fetch_and_parse(sitemap_url):
                """Fetch and parse with source tracking"""
                content = self.fetch_sitemap(sitemap_url)
                if content:
                    urls = self.parse_sitemap(content)
                    # Add source information to each URL
                    for url_data in urls:
                        url_data["source"] = sitemap_url
                    return urls
                return []

            nested_sitemaps = []

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(fetch_and_parse, url): url for url in batch}

                for future in as_completed(futures):
                    source_url = futures[future]
                    try:
                        urls = future.result()
                        logger.info(f"  ✓ {source_url}: Found {len(urls)} URLs")

                        for url_data in urls:
                            if url_data.get("type") == "sitemap":
                                # Found nested sitemap
                                nested_url = url_data["url"]
                                if nested_url not in processed and nested_url not in nested_sitemaps:
                                    nested_sitemaps.append(nested_url)
                                    logger.info(f"  → Found nested sitemap: {nested_url}")
                            else:
                                all_urls.append(url_data)
                    except Exception as e:
                        logger.error(f"  ✗ {source_url}: Error - {e}")

            # Add nested sitemaps to queue for next iteration
            if nested_sitemaps:
                logger.info(f"Level {depth}: Found {len(nested_sitemaps)} nested sitemaps to process next")
                sitemaps_to_process.extend(nested_sitemaps)
            else:
                logger.info(f"Level {depth}: No more nested sitemaps found")

        logger.success(f"✓ Completed {depth} levels of sitemap processing")
        logger.success(f"✓ Processed {len(processed)} total sitemaps")
        return all_urls

    def enrich_urls_with_titles(self, urls: List[Dict], max_urls: int = 50) -> List[Dict]:
        """Fetch titles for URLs that don't have them (limited to avoid overload)"""
        urls_without_titles = [url for url in urls if not url.get("title")]

        if not urls_without_titles:
            return urls

        # Limit to avoid too many requests
        to_fetch = urls_without_titles[:max_urls]
        logger.info(f"Fetching titles for {len(to_fetch)} URLs (out of {len(urls_without_titles)} without titles)...")

        def fetch_title(url_data):
            """Fetch title from HTML"""
            try:
                response = self.session.get(url_data["url"], timeout=5)
                if response.status_code == 200:
                    # Quick regex to extract title
                    match = re.search(r'<title[^>]*>([^<]+)</title>', response.text, re.IGNORECASE)
                    if match:
                        title = match.group(1).strip()
                        url_data["title"] = title
                        logger.info(f"  ✓ {url_data['url'][:60]}: {title[:50]}")
                        return url_data
            except:
                pass
            return url_data

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(fetch_title, url) for url in to_fetch]
            for future in as_completed(futures):
                future.result()  # Update happens in place

        return urls

    def categorize_wordpress_urls(self, urls: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Categorize WordPress URLs by type

        Returns:
            Dict with categories:
                - posts: Blog posts
                - pages: Static pages
                - categories: Category archives
                - tags: Tag archives
                - authors: Author archives
                - other: Other URLs
        """
        categories = {
            "posts": [],
            "pages": [],
            "categories": [],
            "tags": [],
            "authors": [],
            "media": [],
            "other": [],
        }

        for url_data in urls:
            url = url_data["url"]
            path = urlparse(url).path.lower()

            # Categorize based on URL patterns
            if '/category/' in path or '/categories/' in path:
                categories["categories"].append(url_data)
            elif '/tag/' in path or '/tags/' in path:
                categories["tags"].append(url_data)
            elif '/author/' in path or '/authors/' in path:
                categories["authors"].append(url_data)
            elif '/wp-content/uploads/' in path or path.endswith(('.jpg', '.png', '.pdf', '.zip')):
                categories["media"].append(url_data)
            elif re.search(r'/\d{4}/\d{2}/', path):  # Date-based URLs (posts)
                categories["posts"].append(url_data)
            elif path.count('/') <= 2 and not path.endswith('/'):  # Likely pages
                categories["pages"].append(url_data)
            else:
                # Try to distinguish posts from pages
                # Posts often have longer paths or date patterns
                if path.count('/') >= 3 or re.search(r'\d{4}', path):
                    categories["posts"].append(url_data)
                else:
                    categories["pages"].append(url_data)

        # Log summary
        logger.info("URL categorization:")
        for category, urls in categories.items():
            if urls:
                logger.info(f"  {category}: {len(urls)}")

        return categories
