"""Tests for CSS-in-JS inlining and script neutralization"""

from unittest.mock import MagicMock

from src.drivers.chrome_driver import ChromeDriverManager


def make_manager():
    m = ChromeDriverManager.__new__(ChromeDriverManager)
    m.driver = None
    return m


class TestInlineRuntimeStyles:

    def test_returns_count_from_browser_script(self):
        driver = MagicMock()
        driver.execute_script.return_value = 7
        assert make_manager().inline_runtime_styles(driver) == 7

    def test_handles_script_failure_gracefully(self):
        driver = MagicMock()
        driver.execute_script.side_effect = Exception("CSSOM unavailable")
        assert make_manager().inline_runtime_styles(driver) == 0

    def test_none_result_normalized_to_zero(self):
        driver = MagicMock()
        driver.execute_script.return_value = None
        assert make_manager().inline_runtime_styles(driver) == 0


class TestNeutralizeScripts:

    def test_removes_all_script_tags(self):
        html = ('<html><head><script src="a.js"></script>'
                '<style>.x{color:red}</style></head>'
                '<body><p>hi</p><script>console.log(1)</script></body></html>')
        out = make_manager().neutralize_scripts(html)
        assert "<script" not in out
        # Non-script content is preserved
        assert "color:red" in out
        assert "<p>hi</p>" in out

    def test_no_scripts_is_noop(self):
        html = "<html><body><h1>title</h1></body></html>"
        out = make_manager().neutralize_scripts(html)
        assert "title" in out
        assert "<script" not in out
