"""Tests for website cloner"""

import pytest
from src.cloner import WebsiteCloner


class TestWebsiteCloner:
    """Test WebsiteCloner functionality"""

    def test_cloner_initialization(self):
        """Test that cloner initializes correctly"""
        cloner = WebsiteCloner(headless=True)

        assert cloner.headless is True
        assert cloner._cancel_requested is False
        assert cloner.event_emitter is not None

    def test_cloner_cancellation_flag(self):
        """Test cancellation flag functionality"""
        cloner = WebsiteCloner()

        assert not cloner._cancel_requested

        cloner.cancel()

        assert cloner._cancel_requested

    def test_check_cancellation_raises_when_cancelled(self):
        """Test that cancellation check raises InterruptedError"""
        cloner = WebsiteCloner()
        cloner.cancel()

        with pytest.raises(InterruptedError, match="cancelled by user"):
            cloner._check_cancellation()

    def test_check_cancellation_passes_when_not_cancelled(self):
        """Test that cancellation check passes normally"""
        cloner = WebsiteCloner()

        # Should not raise
        cloner._check_cancellation()
