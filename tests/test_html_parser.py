"""Tests for HTML asset extraction coverage (mocked downloader)"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from src.parsers.html_parser import HTMLParser


def make_parser():
    downloader = MagicMock()
    # Pretend every URL downloads to local/<basename>
    downloader.download_file.side_effect = (
        lambda base, url, path: f"local/{url.split('/')[-1].split('?')[0]}"
    )
    return HTMLParser(downloader), downloader


def run(parser, html):
    with tempfile.TemporaryDirectory() as tmp:
        return parser.process_html(html, "https://example.com", Path(tmp))


class TestLinkRelFiltering:

    def test_stylesheet_and_icon_links_are_rewritten(self):
        parser, dl = make_parser()
        out = run(parser, '<link rel="stylesheet" href="https://example.com/a.css">'
                          '<link rel="icon" href="/favicon.png">')
        assert 'local/a.css' in out
        assert 'local/favicon.png' in out

    def test_page_level_links_keep_their_urls(self):
        parser, dl = make_parser()
        html = ('<link rel="canonical" href="https://example.com/page">'
                '<link rel="alternate" hreflang="fr" href="https://example.com/fr">'
                '<link rel="preconnect" href="https://cdn.example.com">'
                '<link rel="dns-prefetch" href="https://cdn.example.com">')
        out = run(parser, html)
        assert 'https://example.com/page' in out
        assert 'https://example.com/fr' in out
        # No downloads attempted for any of them (favicon call uses download_favicon)
        assert dl.download_file.call_count == 0


class TestMediaElements:

    def test_picture_source_srcset_rewritten(self):
        parser, _ = make_parser()
        out = run(parser, '<picture><source srcset="https://example.com/img-800.webp 800w, '
                          'https://example.com/img-400.webp 400w"><img src="/img.jpg"></picture>')
        assert 'local/img-800.webp 800w' in out
        assert 'local/img-400.webp 400w' in out
        assert 'local/img.jpg' in out

    def test_video_src_and_poster_rewritten(self):
        parser, _ = make_parser()
        out = run(parser, '<video src="https://example.com/clip.mp4" '
                          'poster="https://example.com/poster.jpg"></video>')
        assert 'local/clip.mp4' in out
        assert 'local/poster.jpg' in out

    def test_lazy_data_src_rewritten_and_promoted(self):
        parser, _ = make_parser()
        out = run(parser, '<img data-src="https://example.com/lazy.png">')
        assert 'data-src="local/lazy.png"' in out
        assert 'src="local/lazy.png"' in out


class TestInlineCss:

    def test_style_attribute_url_rewritten(self):
        parser, _ = make_parser()
        out = run(parser, '<div style="background-image:url(https://example.com/bg.png)"></div>')
        assert 'url(local/bg.png)' in out

    def test_style_block_url_rewritten(self):
        parser, _ = make_parser()
        out = run(parser, '<style>.hero{background:url("https://example.com/hero.jpg")}</style>')
        assert 'url(local/hero.jpg)' in out

    def test_data_uri_and_fragment_left_alone(self):
        parser, dl = make_parser()
        html = '<div style="background:url(data:image/png;base64,AAA) url(#frag)"></div>'
        out = run(parser, html)
        assert 'data:image/png;base64,AAA' in out
        assert dl.download_file.call_count == 0
