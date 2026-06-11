"""Tests for framework/technology detection"""

from src.discovery import FrameworkDetector


def names(matches):
    return {m.name for m in matches}


class TestHtmlDetection:

    def test_nextjs_from_markup(self):
        html = '<html><body><script id="__NEXT_DATA__">{}</script>' \
               '<link href="/_next/static/chunks/main.css"></body></html>'
        d = FrameworkDetector().detect_from_html(html)
        assert "Next.js" in names(d)
        assert d[0].category == "meta-framework"

    def test_wordpress_with_version(self):
        html = '<meta name="generator" content="WordPress 6.5.2">' \
               '<link href="/wp-content/themes/x/style.css">'
        d = FrameworkDetector().detect_from_html(html)
        wp = next(m for m in d if m.name == "WordPress")
        assert wp.version == "6.5.2"
        assert wp.confidence >= 0.5

    def test_angular_version_attribute(self):
        html = '<app-root ng-version="17.1.0"></app-root>'
        d = FrameworkDetector().detect_from_html(html)
        ng = next(m for m in d if m.name == "Angular")
        assert ng.version == "17.1.0"

    def test_shopify_ecommerce(self):
        html = '<script src="https://cdn.shopify.com/s/files/x.js"></script>'
        d = FrameworkDetector().detect_from_html(html)
        assert "Shopify" in names(d)

    def test_multi_label_detection(self):
        html = ('<script id="__NEXT_DATA__">{}</script>'
                '<div class="flex px-4 text-sm bg-gray-900">'
                '<script src="https://www.googletagmanager.com/gtag/js"></script>')
        d = FrameworkDetector().detect_from_html(html)
        got = names(d)
        assert "Next.js" in got
        assert "Tailwind CSS" in got
        assert "Google Analytics" in got

    def test_plain_html_detects_nothing(self):
        d = FrameworkDetector().detect_from_html("<html><body><h1>Hi</h1></body></html>")
        assert d == []

    def test_image_paths_do_not_false_positive_magento(self):
        # Regression: 'mage/' used to match the 'mage/' inside 'image/'
        html = '<img src="/assets/image/logo.png"><img src="image/hero.jpg">'
        d = FrameworkDetector().detect_from_html(html)
        assert "Magento" not in names(d)

    def test_real_magento_still_detected(self):
        html = '<script>require(["mage/requirejs/mixins"])</script>' \
               '<div data-mage-init="{}"></div>'
        d = FrameworkDetector().detect_from_html(html)
        assert "Magento" in names(d)

    def test_nextjs_implies_react_even_without_react_markers(self):
        # React 18 streaming SSR leaves no data-reactroot / window.React
        html = '<script id="__NEXT_DATA__">{}</script>'
        d = FrameworkDetector().detect_from_html(html)
        got = names(d)
        assert "Next.js" in got
        assert "React" in got  # implied

    def test_nuxt_implies_vue(self):
        html = '<script id="__NUXT_DATA__">{}</script><div id="__nuxt"></div>'
        d = FrameworkDetector().detect_from_html(html)
        assert "Vue.js" in names(d)


class TestJsProbeDetection:

    def test_js_global_boosts_and_adds(self):
        # Markup has nothing; JS globals report React + jQuery present
        def js_eval(expr):
            if "React" in expr and "!!" in expr:
                return True
            if "jQuery" in expr and "!!" in expr:
                return True
            if "fn.jquery" in expr:
                return "3.7.1"
            return False

        d = FrameworkDetector().detect("<html></html>", js_eval=js_eval)
        got = {m.name: m for m in d}
        assert "React" in got
        assert "jQuery" in got
        assert got["jQuery"].version == "3.7.1"

    def test_js_eval_errors_are_safe(self):
        def js_eval(expr):
            raise RuntimeError("page navigated")

        d = FrameworkDetector().detect('<script id="__NEXT_DATA__">{}</script>', js_eval=js_eval)
        assert "Next.js" in names(d)  # falls back to HTML detection
