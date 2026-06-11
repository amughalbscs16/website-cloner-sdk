"""Tests for network-idle detection and auto-scroll"""

from unittest.mock import MagicMock

from src.drivers.chrome_driver import ChromeDriverManager


def make_manager():
    manager = ChromeDriverManager.__new__(ChromeDriverManager)
    manager.driver = None
    return manager


class TestWaitForPageIdle:

    def test_idle_when_complete_and_resource_count_stable(self):
        driver = MagicMock()
        # readyState then resource count, alternating per poll: stays at 5 resources
        driver.execute_script.side_effect = ["complete", 5, "complete", 5, "complete", 5]

        result = make_manager().wait_for_page_idle(
            driver, idle_ms=100, timeout=5.0, poll_interval=0.06
        )

        assert result is True

    def test_timeout_when_resources_keep_arriving(self):
        driver = MagicMock()
        counter = {"n": 0}

        def script(js):
            if "readyState" in js:
                return "complete"
            counter["n"] += 1  # resource count grows every poll
            return counter["n"]

        driver.execute_script.side_effect = script

        result = make_manager().wait_for_page_idle(
            driver, idle_ms=200, timeout=0.5, poll_interval=0.05
        )

        assert result is False

    def test_script_failure_returns_false_for_fixed_wait_fallback(self):
        driver = MagicMock()
        driver.execute_script.side_effect = Exception("tab crashed")

        result = make_manager().wait_for_page_idle(driver, timeout=2.0)

        assert result is False


class TestAutoScroll:

    def test_scrolls_until_bottom_and_returns_to_top(self):
        driver = MagicMock()
        # scrollHeight 2000; position reaches 2000 on second step
        responses = {
            "scrollHeight": [2000, 2000, 2000],
            "scrollY": [1000, 2000, 2000],
        }

        def script(js):
            if "scrollHeight" in js:
                return responses["scrollHeight"].pop(0)
            if "scrollY" in js and "innerHeight" in js and "return" in js:
                return responses["scrollY"].pop(0)
            return None  # scrollBy / scrollTo

        driver.execute_script.side_effect = script

        make_manager().auto_scroll(driver, step_delay=0.01)

        calls = [c.args[0] for c in driver.execute_script.call_args_list]
        assert any("scrollTo(0, 0)" in c for c in calls)

    def test_scroll_errors_are_swallowed(self):
        driver = MagicMock()
        driver.execute_script.side_effect = Exception("page gone")

        make_manager().auto_scroll(driver, step_delay=0.01)  # must not raise
