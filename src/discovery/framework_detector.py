"""Web framework / technology detection.

Identifies the major site-building technologies from rendered HTML markers and,
when a Selenium driver is supplied, from runtime JavaScript globals (which are
far more reliable than markup heuristics). Detection is multi-label: a single
page can legitimately be e.g. Next.js + React + Tailwind + Google Analytics.
"""

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from ..utils.logger import logger


@dataclass
class FrameworkMatch:
    name: str
    category: str          # meta-framework | ui-library | css | cms | ecommerce | site-builder | analytics | ssg
    confidence: float      # 0..1
    version: Optional[str] = None
    indicators: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "category": self.category,
            "confidence": round(self.confidence, 2),
            "version": self.version,
            "indicators": self.indicators,
        }


class FrameworkDetector:
    """Detect web frameworks and technologies from a rendered page"""

    # Static HTML signal table: name -> (category, [(regex, weight, label)])
    # Regexes run against the rendered HTML (case-insensitive).
    HTML_SIGNALS = {
        "Next.js": ("meta-framework", [
            (r'id="__NEXT_DATA__"', 0.6, "__NEXT_DATA__ script"),
            (r'/_next/static/', 0.5, "_next/static assets"),
        ]),
        "Nuxt": ("meta-framework", [
            (r'id="__NUXT_DATA__"|window\.__NUXT__', 0.6, "__NUXT__ payload"),
            (r'/_nuxt/', 0.5, "_nuxt assets"),
        ]),
        "Gatsby": ("meta-framework", [
            (r'id="___gatsby"', 0.6, "___gatsby root"),
            (r'/page-data/app-data\.json|/page-data/index/page-data\.json', 0.4, "gatsby page-data"),
        ]),
        "Remix": ("meta-framework", [
            (r'window\.__remixContext|__remixManifest', 0.7, "__remixContext"),
        ]),
        "SvelteKit": ("meta-framework", [
            (r'__sveltekit_|/_app/immutable/', 0.7, "SvelteKit app shell"),
        ]),
        "Astro": ("meta-framework", [
            (r'<astro-island|data-astro-cid|/_astro/', 0.7, "Astro islands/assets"),
        ]),
        "Angular": ("ui-library", [
            (r'ng-version="([\d.]+)"', 0.8, "ng-version attribute"),
            (r'_nghost|_ngcontent|ng-app', 0.4, "Angular DOM bindings"),
        ]),
        "Vue.js": ("ui-library", [
            (r'data-server-rendered="true"', 0.5, "Vue SSR marker"),
            (r'data-v-[0-9a-f]{6,}', 0.4, "Vue scoped-style attrs"),
            (r'id="__nuxt"|id="q-app"', 0.3, "Vue app root"),
        ]),
        "React": ("ui-library", [
            (r'data-reactroot|data-reactid', 0.5, "React DOM markers"),
        ]),
        "Svelte": ("ui-library", [
            (r'class="[^"]*svelte-[0-9a-z]{4,}', 0.5, "Svelte scoped classes"),
        ]),
        "Ember.js": ("ui-library", [
            (r'id="ember[0-9]+"|ember-application', 0.7, "Ember app markers"),
        ]),
        "jQuery": ("ui-library", [
            (r'jquery[.-]([\d.]+)?(\.min)?\.js', 0.6, "jQuery script"),
        ]),
        "WordPress": ("cms", [
            (r'/wp-content/', 0.5, "wp-content"),
            (r'/wp-includes/', 0.4, "wp-includes"),
            (r'name="generator"\s+content="WordPress\s*([\d.]+)?', 0.5, "WordPress generator"),
        ]),
        "Drupal": ("cms", [
            (r'Drupal\.settings|drupal-settings-json|/sites/default/files', 0.7, "Drupal markers"),
            (r'name="generator"\s+content="Drupal\s*([\d.]+)?', 0.6, "Drupal generator"),
        ]),
        "Joomla": ("cms", [
            (r'/media/jui/|/media/system/js/', 0.5, "Joomla media paths"),
            (r'name="generator"\s+content="Joomla', 0.7, "Joomla generator"),
        ]),
        "Ghost": ("cms", [
            (r'name="generator"\s+content="Ghost\s*([\d.]+)?', 0.7, "Ghost generator"),
            (r'/ghost/|content/images', 0.2, "Ghost paths"),
        ]),
        "Shopify": ("ecommerce", [
            (r'cdn\.shopify\.com|/cdn/shop/|Shopify\.theme', 0.7, "Shopify CDN/theme"),
        ]),
        "WooCommerce": ("ecommerce", [
            (r'/plugins/woocommerce|woocommerce', 0.5, "WooCommerce assets"),
        ]),
        "Magento": ("ecommerce", [
            (r'/static/version\d+/frontend/|Magento_|data-mage-init|mage/requirejs', 0.7, "Magento markers"),
        ]),
        "BigCommerce": ("ecommerce", [
            (r'cdn\d*\.bigcommerce\.com', 0.7, "BigCommerce CDN"),
        ]),
        "Wix": ("site-builder", [
            (r'static\.wixstatic\.com|X-Wix-|_wixCssStates|wix\.com', 0.7, "Wix static/markers"),
        ]),
        "Squarespace": ("site-builder", [
            (r'Static\.SQUARESPACE_CONTEXT|squarespace\.com|sqsp\.net', 0.7, "Squarespace context"),
        ]),
        "Webflow": ("site-builder", [
            (r'data-wf-page|data-wf-site|website-files\.com', 0.7, "Webflow attributes"),
        ]),
        "Framer": ("site-builder", [
            (r'framerusercontent\.com|__framer', 0.7, "Framer markers"),
        ]),
        "Hugo": ("ssg", [
            (r'name="generator"\s+content="Hugo\s*([\d.]+)?', 0.8, "Hugo generator"),
        ]),
        "Jekyll": ("ssg", [
            (r'name="generator"\s+content="Jekyll\s*([\d.]+)?', 0.8, "Jekyll generator"),
        ]),
        "Eleventy": ("ssg", [
            (r'name="generator"\s+content="Eleventy', 0.8, "Eleventy generator"),
        ]),
        "Docusaurus": ("ssg", [
            (r'name="generator"\s+content="Docusaurus\s*([\d.]+)?', 0.8, "Docusaurus generator"),
        ]),
        "Tailwind CSS": ("css", [
            (r'class="[^"]*\b(?:flex|grid|px-\d|py-\d|text-(?:xs|sm|lg|xl)|bg-(?:white|black|gray)-?\d*)\b[^"]*"', 0.3, "Tailwind utility classes"),
        ]),
        "Bootstrap": ("css", [
            (r'bootstrap(?:\.min)?\.(?:css|js)|class="[^"]*\b(?:col-(?:md|lg|sm)-\d|navbar-(?:expand|toggler))\b', 0.5, "Bootstrap classes/assets"),
        ]),
        "Google Analytics": ("analytics", [
            (r'googletagmanager\.com/gtag/js|google-analytics\.com/analytics\.js|gtag\(', 0.6, "GA/gtag"),
        ]),
        "Google Tag Manager": ("analytics", [
            (r'googletagmanager\.com/gtm\.js|GTM-[A-Z0-9]+', 0.6, "GTM container"),
        ]),
    }

    # Runtime JS-global probes (evaluated in the live page). Far more reliable
    # than markup; expression must return a truthy value when present.
    JS_PROBES = {
        "Next.js": ("meta-framework", "window.__NEXT_DATA__ || window.next"),
        "Nuxt": ("meta-framework", "window.__NUXT__ || window.$nuxt"),
        "Gatsby": ("meta-framework", "window.___gatsby || window.___loader"),
        "Remix": ("meta-framework", "window.__remixContext || window.__remixManifest"),
        "SvelteKit": ("meta-framework", "window.__sveltekit_ || document.querySelector('[data-sveltekit-preload-data]')"),
        "React": ("ui-library", "window.React || document.querySelector('[data-reactroot]') || (window.__REACT_DEVTOOLS_GLOBAL_HOOK__ && window.__REACT_DEVTOOLS_GLOBAL_HOOK__.renderers && window.__REACT_DEVTOOLS_GLOBAL_HOOK__.renderers.size > 0)"),
        "Vue.js": ("ui-library", "window.Vue || window.__VUE__ || document.querySelector('[data-server-rendered],#app[data-v-app]')"),
        "Angular": ("ui-library", "window.ng || window.getAllAngularRootElements || document.querySelector('[ng-version]')"),
        "Svelte": ("ui-library", "window.__svelte || document.querySelector('[class*=svelte-]')"),
        "jQuery": ("ui-library", "window.jQuery || window.$ && window.$.fn && window.$.fn.jquery"),
        "Shopify": ("ecommerce", "window.Shopify"),
        "Google Analytics": ("analytics", "window.gtag || window.ga || window.dataLayer"),
    }

    VERSION_PROBES = {
        "jQuery": "window.jQuery ? window.jQuery.fn.jquery : null",
        "Vue.js": "window.Vue && window.Vue.version ? window.Vue.version : null",
        "Angular": "(document.querySelector('[ng-version]') || {}).getAttribute ? document.querySelector('[ng-version]').getAttribute('ng-version') : null",
    }

    def detect_from_html(self, html: str, url: str = "") -> List[FrameworkMatch]:
        """Detect frameworks from rendered HTML markers only"""
        matches: Dict[str, FrameworkMatch] = {}

        for name, (category, signals) in self.HTML_SIGNALS.items():
            confidence = 0.0
            indicators: List[str] = []
            version = None
            for pattern, weight, label in signals:
                m = re.search(pattern, html, re.IGNORECASE)
                if m:
                    confidence += weight
                    indicators.append(label)
                    if m.groups() and m.group(1):
                        version = m.group(1)
            if confidence > 0:
                matches[name] = FrameworkMatch(
                    name=name, category=category,
                    confidence=min(confidence, 1.0),
                    version=version, indicators=indicators,
                )

        return self._resolve(matches)

    def detect(self, html: str, url: str = "", js_eval: Optional[Callable] = None) -> List[FrameworkMatch]:
        """
        Detect frameworks from HTML plus, if js_eval is provided, runtime globals.

        Args:
            html: Rendered page HTML
            url: Page URL (for logging)
            js_eval: Callable taking a JS expression string and returning its
                     value (e.g. driver.execute_script with a 'return' prefix)
        """
        matches = {m.name: m for m in self.detect_from_html(html, url)}

        if js_eval is not None:
            for name, (category, expr) in self.JS_PROBES.items():
                try:
                    present = js_eval(f"return !!({expr});")
                except Exception:
                    present = False
                if not present:
                    continue
                version = None
                if name in self.VERSION_PROBES:
                    try:
                        version = js_eval(f"return ({self.VERSION_PROBES[name]});")
                    except Exception:
                        version = None
                if name in matches:
                    matches[name].confidence = min(matches[name].confidence + 0.4, 1.0)
                    matches[name].indicators.append("runtime JS global")
                    matches[name].version = matches[name].version or version
                else:
                    matches[name] = FrameworkMatch(
                        name=name, category=category, confidence=0.7,
                        version=version, indicators=["runtime JS global"],
                    )

        result = self._resolve(matches)
        if result:
            top = ", ".join(f"{m.name}" + (f" {m.version}" if m.version else "") for m in result[:5])
            logger.info(f"Detected frameworks: {top}")
        return result

    # A meta-framework is built on a UI library; that library is present even
    # when it leaves no detectable marker (e.g. React 18 streaming SSR dropped
    # data-reactroot and window.React). Inject the implied library.
    IMPLIES = {
        "Next.js": ("React", "ui-library"),
        "Remix": ("React", "ui-library"),
        "Gatsby": ("React", "ui-library"),
        "Nuxt": ("Vue.js", "ui-library"),
        "SvelteKit": ("Svelte", "ui-library"),
    }

    def _resolve(self, matches: Dict[str, FrameworkMatch]) -> List[FrameworkMatch]:
        """Add implied UI libraries and sort by confidence"""
        for meta, (lib, category) in self.IMPLIES.items():
            if meta not in matches or matches[meta].confidence < 0.5:
                continue
            if lib in matches:
                matches[lib].confidence = max(matches[lib].confidence, 0.6)
                if "implied by " + meta not in matches[lib].indicators:
                    matches[lib].indicators.append("implied by " + meta)
            else:
                matches[lib] = FrameworkMatch(
                    name=lib, category=category, confidence=0.6,
                    indicators=["implied by " + meta],
                )

        return sorted(matches.values(), key=lambda m: (-m.confidence, m.category, m.name))
