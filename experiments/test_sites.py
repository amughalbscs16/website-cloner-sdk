"""
Centralized Test Sites Database for Experiments

This file contains all websites used for benchmarking and testing.
Organized by complexity tier for systematic evaluation.
"""

from dataclasses import dataclass
from typing import List, Dict
from enum import Enum


class SiteCategory(str, Enum):
    """Website architecture categories"""
    STATIC = "static"
    SSR = "server-rendered"
    SPA = "single-page-app"
    HYBRID = "hybrid"
    HEAVY_JS = "heavy-javascript"
    SPECIAL = "special-case"


@dataclass
class TestSite:
    """A website to test"""
    name: str
    url: str
    category: SiteCategory
    description: str
    expected_assets: int = None  # Approximate count
    difficulty: str = "medium"  # easy, medium, hard
    notes: str = ""


# =============================================================================
# TIER 1: STATIC BASELINES
# =============================================================================

TIER_1_STATIC = [
    TestSite(
        name="Example.com",
        url="https://example.com",
        category=SiteCategory.STATIC,
        description="Simplest possible website, pure HTML",
        expected_assets=5,
        difficulty="easy",
        notes="Perfect for baseline testing, minimal assets"
    ),
    TestSite(
        name="Motherfucking Website",
        url="http://motherfuckingwebsite.com/",
        category=SiteCategory.STATIC,
        description="Ultra-minimal static site",
        expected_assets=3,
        difficulty="easy",
        notes="No CSS, no JS, just HTML. Good for testing HTML-only cloning"
    ),
    TestSite(
        name="Python Docs",
        url="https://docs.python.org/3/tutorial/",
        category=SiteCategory.STATIC,
        description="Static documentation site with minimal JS",
        expected_assets=50,
        difficulty="easy",
        notes="Good for testing documentation cloning"
    ),
]

# =============================================================================
# TIER 2: SERVER-RENDERED (Traditional)
# =============================================================================

TIER_2_SSR = [
    TestSite(
        name="WordPress.org News",
        url="https://wordpress.org/news/",
        category=SiteCategory.SSR,
        description="WordPress blog with server-side rendering",
        expected_assets=150,
        difficulty="medium",
        notes="Common CMS, good for real-world testing"
    ),
    TestSite(
        name="Django Project",
        url="https://www.djangoproject.com/",
        category=SiteCategory.SSR,
        description="Django framework website",
        expected_assets=100,
        difficulty="medium",
        notes="Python web framework site"
    ),
    TestSite(
        name="Ruby on Rails",
        url="https://rubyonrails.org/",
        category=SiteCategory.SSR,
        description="Rails framework website",
        expected_assets=120,
        difficulty="medium",
        notes="Classic server-rendered site"
    ),
    TestSite(
        name="Wikipedia Article",
        url="https://en.wikipedia.org/wiki/Web_archiving",
        category=SiteCategory.SSR,
        description="Wikipedia article page",
        expected_assets=80,
        difficulty="medium",
        notes="MediaWiki platform, good for testing wikis"
    ),
]

# =============================================================================
# TIER 3: CLIENT-RENDERED (SPAs)
# =============================================================================

TIER_3_SPA = [
    TestSite(
        name="React.dev",
        url="https://react.dev/",
        category=SiteCategory.SPA,
        description="React documentation site (SPA)",
        expected_assets=200,
        difficulty="hard",
        notes="Modern SPA, heavily JS-dependent. Critical test case!"
    ),
    TestSite(
        name="Vue.js",
        url="https://vuejs.org/",
        category=SiteCategory.SPA,
        description="Vue.js documentation site (SPA)",
        expected_assets=180,
        difficulty="hard",
        notes="Progressive framework, tests SPA cloning"
    ),
    TestSite(
        name="Angular.io",
        url="https://angular.io/",
        category=SiteCategory.SPA,
        description="Angular documentation site (SPA)",
        expected_assets=250,
        difficulty="hard",
        notes="Full SPA framework, complex JS"
    ),
]

# =============================================================================
# TIER 4: HYBRID (Modern Frameworks)
# =============================================================================

TIER_4_HYBRID = [
    TestSite(
        name="Next.js",
        url="https://nextjs.org/",
        category=SiteCategory.HYBRID,
        description="Next.js website (React + SSR)",
        expected_assets=220,
        difficulty="hard",
        notes="Tests hybrid SSR+SPA architecture"
    ),
    TestSite(
        name="Nuxt",
        url="https://nuxt.com/",
        category=SiteCategory.HYBRID,
        description="Nuxt website (Vue + SSR)",
        expected_assets=200,
        difficulty="hard",
        notes="Vue-based hybrid framework"
    ),
    TestSite(
        name="Remix",
        url="https://remix.run/",
        category=SiteCategory.HYBRID,
        description="Remix website (modern hybrid)",
        expected_assets=180,
        difficulty="hard",
        notes="Edge-first React framework"
    ),
]

# =============================================================================
# TIER 5: HEAVY JAVASCRIPT / INTERACTIVE
# =============================================================================

TIER_5_HEAVY_JS = [
    TestSite(
        name="Figma Blog",
        url="https://www.figma.com/blog/",
        category=SiteCategory.HEAVY_JS,
        description="Figma blog with heavy animations",
        expected_assets=300,
        difficulty="very hard",
        notes="Lots of animations and interactive elements"
    ),
    TestSite(
        name="Notion Features",
        url="https://www.notion.so/product",
        category=SiteCategory.HEAVY_JS,
        description="Notion product page",
        expected_assets=250,
        difficulty="very hard",
        notes="Complex interactive components"
    ),
    TestSite(
        name="Linear Features",
        url="https://linear.app/",
        category=SiteCategory.HEAVY_JS,
        description="Linear homepage",
        expected_assets=280,
        difficulty="very hard",
        notes="Smooth animations, heavy JS"
    ),
]

# =============================================================================
# TIER 6: SPECIAL CASES
# =============================================================================

TIER_6_SPECIAL = [
    TestSite(
        name="Tailwind CSS",
        url="https://tailwindcss.com/",
        category=SiteCategory.SPECIAL,
        description="CSS framework docs with CDN assets",
        expected_assets=150,
        difficulty="medium",
        notes="Tests CDN asset handling"
    ),
    TestSite(
        name="Google Fonts",
        url="https://fonts.google.com/",
        category=SiteCategory.SPECIAL,
        description="Font showcase with many embedded fonts",
        expected_assets=500,
        difficulty="very hard",
        notes="Tests font file handling, may be slow"
    ),
    TestSite(
        name="Unsplash",
        url="https://unsplash.com/",
        category=SiteCategory.SPECIAL,
        description="Photo site with lazy loading",
        expected_assets=200,
        difficulty="very hard",
        notes="Tests lazy loading and infinite scroll"
    ),
    TestSite(
        name="MDN Web Docs",
        url="https://developer.mozilla.org/en-US/",
        category=SiteCategory.SPECIAL,
        description="Large documentation site",
        expected_assets=180,
        difficulty="medium",
        notes="Good for testing documentation sites"
    ),
]

# =============================================================================
# QUICK DEMO SET (3 sites for fast testing)
# =============================================================================

QUICK_DEMO_SET = [
    TestSite(
        name="Example.com",
        url="https://example.com",
        category=SiteCategory.STATIC,
        description="Static HTML baseline",
        expected_assets=5,
        difficulty="easy"
    ),
    TestSite(
        name="React.dev",
        url="https://react.dev/",
        category=SiteCategory.SPA,
        description="React SPA",
        expected_assets=200,
        difficulty="hard"
    ),
    TestSite(
        name="WordPress.org",
        url="https://wordpress.org/news/",
        category=SiteCategory.SSR,
        description="WordPress SSR",
        expected_assets=150,
        difficulty="medium"
    ),
]

# =============================================================================
# FULL BENCHMARK SET (All tiers)
# =============================================================================

FULL_BENCHMARK_SET = (
    TIER_1_STATIC +
    TIER_2_SSR +
    TIER_3_SPA +
    TIER_4_HYBRID +
    TIER_5_HEAVY_JS +
    TIER_6_SPECIAL
)

# =============================================================================
# COMPETITIVE COMPARISON SET (vs HTTrack, Wget, etc.)
# =============================================================================

COMPETITIVE_SET = [
    # Static (everyone should handle this)
    TIER_1_STATIC[0],  # Example.com

    # SSR (traditional tools should handle)
    TIER_2_SSR[0],  # WordPress

    # SPA (where we should win)
    TIER_3_SPA[0],  # React.dev
    TIER_3_SPA[1],  # Vue.js

    # Special cases
    TIER_6_SPECIAL[0],  # Tailwind (CDN)
]

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_sites_by_category(category: SiteCategory) -> List[TestSite]:
    """Get all sites in a specific category"""
    return [site for site in FULL_BENCHMARK_SET if site.category == category]


def get_sites_by_difficulty(difficulty: str) -> List[TestSite]:
    """Get all sites of a specific difficulty"""
    return [site for site in FULL_BENCHMARK_SET if site.difficulty == difficulty]


def get_site_by_name(name: str) -> TestSite:
    """Get a specific site by name"""
    for site in FULL_BENCHMARK_SET:
        if site.name.lower() == name.lower():
            return site
    raise ValueError(f"Site '{name}' not found in test database")


def get_custom_set(site_names: List[str]) -> List[TestSite]:
    """Create custom test set by site names"""
    return [get_site_by_name(name) for name in site_names]


def export_to_dict() -> Dict:
    """Export all test sites as dictionary for JSON/API"""
    return {
        "quick_demo": [s.__dict__ for s in QUICK_DEMO_SET],
        "tier_1_static": [s.__dict__ for s in TIER_1_STATIC],
        "tier_2_ssr": [s.__dict__ for s in TIER_2_SSR],
        "tier_3_spa": [s.__dict__ for s in TIER_3_SPA],
        "tier_4_hybrid": [s.__dict__ for s in TIER_4_HYBRID],
        "tier_5_heavy_js": [s.__dict__ for s in TIER_5_HEAVY_JS],
        "tier_6_special": [s.__dict__ for s in TIER_6_SPECIAL],
        "competitive_set": [s.__dict__ for s in COMPETITIVE_SET],
        "full_benchmark": [s.__dict__ for s in FULL_BENCHMARK_SET],
    }


# =============================================================================
# SUMMARY STATS
# =============================================================================

def print_summary():
    """Print summary of test database"""
    print("=" * 70)
    print("TEST SITES DATABASE SUMMARY")
    print("=" * 70)
    print(f"\nTotal Sites: {len(FULL_BENCHMARK_SET)}")
    print(f"\nBy Tier:")
    print(f"  Tier 1 (Static):      {len(TIER_1_STATIC)} sites")
    print(f"  Tier 2 (SSR):         {len(TIER_2_SSR)} sites")
    print(f"  Tier 3 (SPA):         {len(TIER_3_SPA)} sites")
    print(f"  Tier 4 (Hybrid):      {len(TIER_4_HYBRID)} sites")
    print(f"  Tier 5 (Heavy JS):    {len(TIER_5_HEAVY_JS)} sites")
    print(f"  Tier 6 (Special):     {len(TIER_6_SPECIAL)} sites")

    print(f"\nBy Difficulty:")
    for diff in ["easy", "medium", "hard", "very hard"]:
        count = len(get_sites_by_difficulty(diff))
        print(f"  {diff.title():<15} {count} sites")

    print(f"\nPre-configured Sets:")
    print(f"  Quick Demo:           {len(QUICK_DEMO_SET)} sites (fast testing)")
    print(f"  Competitive:          {len(COMPETITIVE_SET)} sites (vs HTTrack)")
    print(f"  Full Benchmark:       {len(FULL_BENCHMARK_SET)} sites (complete)")
    print("=" * 70)


if __name__ == "__main__":
    # Print summary when run directly
    print_summary()

    print("\n\nQuick Demo Set:")
    print("-" * 70)
    for site in QUICK_DEMO_SET:
        print(f"  {site.name:<20} {site.url}")
