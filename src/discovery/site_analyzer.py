"""Complete site analysis combining detection and discovery"""

from typing import Dict, List, Optional
from loguru import logger

from .wordpress_detector import WordPressDetector
from .sitemap_parser import SitemapParser


class SiteAnalyzer:
    """Analyzes a website for WordPress and discovers all pages"""

    def __init__(self, timeout: int = 10):
        self.detector = WordPressDetector(timeout=timeout)
        self.parser = SitemapParser(timeout=timeout)

    def analyze(self, url: str, discover_pages: bool = True, fetch_titles: bool = False) -> Dict:
        """
        Perform complete site analysis

        Args:
            url: Website URL
            discover_pages: Whether to discover all pages

        Returns:
            Dict with complete analysis including:
                - wordpress_info: WordPress detection results
                - robots_txt: robots.txt content
                - urls: Discovered URLs
                - categories: Categorized URLs
                - statistics: Summary statistics
        """
        logger.info(f"Starting site analysis for: {url}")

        result = {
            "url": url,
            "wordpress_info": {},
            "robots_txt": None,
            "urls": [],
            "categories": {},
            "statistics": {},
        }

        # Step 1: Detect WordPress
        logger.info("Step 1: WordPress detection")
        wordpress_info = self.detector.is_wordpress(url)
        result["wordpress_info"] = wordpress_info

        if not wordpress_info["is_wordpress"]:
            logger.warning("Site is not WordPress, but continuing with discovery...")

        # Step 2: Get robots.txt
        if discover_pages:
            logger.info("Step 2: Fetching robots.txt")
            robots_content = self.parser.get_robots_txt(url)
            result["robots_txt"] = robots_content

            # Step 3: Discover all URLs
            logger.info("Step 3: Discovering URLs from sitemaps")
            urls = self.parser.discover_all_urls(url)
            result["urls"] = urls

            # Step 4: Enrich with titles (optional)
            if fetch_titles and urls:
                logger.info("Step 4: Fetching page titles")
                urls = self.parser.enrich_urls_with_titles(urls, max_urls=50)
                result["urls"] = urls

            # Step 5: Categorize URLs (if WordPress)
            if wordpress_info["is_wordpress"]:
                logger.info(f"Step {5 if fetch_titles else 4}: Categorizing URLs")
                categories = self.parser.categorize_wordpress_urls(urls)
                result["categories"] = categories
            else:
                # Basic categorization for non-WordPress sites
                result["categories"] = {"all": urls}

            # Step 6: Generate statistics
            result["statistics"] = self._generate_statistics(result)

        logger.success(f"✓ Analysis complete for {url}")
        return result

    def _generate_statistics(self, analysis: Dict) -> Dict:
        """Generate summary statistics from analysis"""
        stats = {
            "is_wordpress": analysis["wordpress_info"]["is_wordpress"],
            "confidence": analysis["wordpress_info"]["confidence"],
            "total_urls": len(analysis["urls"]),
        }

        if analysis["wordpress_info"]["is_wordpress"]:
            stats["version"] = analysis["wordpress_info"].get("version")
            stats["theme"] = analysis["wordpress_info"].get("theme")
            stats["plugins_count"] = len(analysis["wordpress_info"].get("plugins", []))
            stats["api_available"] = analysis["wordpress_info"].get("api_available", False)

            # Category counts
            categories = analysis["categories"]
            stats["posts_count"] = len(categories.get("posts", []))
            stats["pages_count"] = len(categories.get("pages", []))
            stats["categories_count"] = len(categories.get("categories", []))
            stats["tags_count"] = len(categories.get("tags", []))
            stats["authors_count"] = len(categories.get("authors", []))
            stats["media_count"] = len(categories.get("media", []))
            stats["other_count"] = len(categories.get("other", []))

        return stats

    def get_analysis_summary(self, analysis: Dict) -> str:
        """Generate a human-readable summary of the analysis"""
        lines = []
        stats = analysis["statistics"]

        lines.append(f"Analysis Summary for: {analysis['url']}")
        lines.append("=" * 60)

        if stats.get("is_wordpress"):
            lines.append(f"✓ WordPress Site Detected ({stats['confidence']:.0%} confidence)")

            if stats.get("version"):
                lines.append(f"  Version: {stats['version']}")
            if stats.get("theme"):
                lines.append(f"  Theme: {stats['theme']}")
            if stats.get("plugins_count"):
                lines.append(f"  Plugins: {stats['plugins_count']} detected")
            if stats.get("api_available"):
                lines.append(f"  REST API: Available")

            lines.append("")
            lines.append(f"Total URLs Found: {stats['total_urls']}")
            lines.append("")
            lines.append("Content Breakdown:")
            lines.append(f"  Posts: {stats.get('posts_count', 0)}")
            lines.append(f"  Pages: {stats.get('pages_count', 0)}")
            lines.append(f"  Categories: {stats.get('categories_count', 0)}")
            lines.append(f"  Tags: {stats.get('tags_count', 0)}")
            lines.append(f"  Authors: {stats.get('authors_count', 0)}")
            lines.append(f"  Media: {stats.get('media_count', 0)}")
            lines.append(f"  Other: {stats.get('other_count', 0)}")
        else:
            lines.append(f"✗ Not a WordPress site (confidence: {stats['confidence']:.0%})")
            lines.append(f"Total URLs Found: {stats['total_urls']}")

        return "\n".join(lines)
