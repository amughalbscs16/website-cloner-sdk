"""Tests for the event emitter at the core of the SDK API"""

import pytest
from src.events import EventEmitter, ClonerEvents
from src.events.event_emitter import ProgressData


class TestEventEmitter:
    """Test event subscription, emission, and removal"""

    def test_on_and_emit_delivers_data(self):
        emitter = EventEmitter()
        received = []

        emitter.on(ClonerEvents.PROGRESS_UPDATE, received.append)
        data = ProgressData(stage="loading", message="test", percentage=10.0)
        emitter.emit(ClonerEvents.PROGRESS_UPDATE, data)

        assert received == [data]

    def test_emit_without_listeners_is_noop(self):
        emitter = EventEmitter()
        emitter.emit(ClonerEvents.CLONE_COMPLETE, None)  # must not raise

    def test_multiple_listeners_all_called(self):
        emitter = EventEmitter()
        calls = []

        emitter.on(ClonerEvents.PAGE_LOADED, lambda d: calls.append("a"))
        emitter.on(ClonerEvents.PAGE_LOADED, lambda d: calls.append("b"))
        emitter.emit(ClonerEvents.PAGE_LOADED, None)

        assert calls == ["a", "b"]

    def test_off_removes_specific_callback(self):
        emitter = EventEmitter()
        calls = []
        cb = lambda d: calls.append("x")

        emitter.on(ClonerEvents.PAGE_LOADED, cb)
        emitter.off(ClonerEvents.PAGE_LOADED, cb)
        emitter.emit(ClonerEvents.PAGE_LOADED, None)

        assert calls == []

    def test_off_without_callback_removes_all(self):
        emitter = EventEmitter()
        calls = []

        emitter.on(ClonerEvents.PAGE_LOADED, lambda d: calls.append("a"))
        emitter.on(ClonerEvents.PAGE_LOADED, lambda d: calls.append("b"))
        emitter.off(ClonerEvents.PAGE_LOADED)
        emitter.emit(ClonerEvents.PAGE_LOADED, None)

        assert calls == []

    def test_once_fires_exactly_once(self):
        emitter = EventEmitter()
        calls = []

        emitter.once(ClonerEvents.PAGE_LOADED, lambda d: calls.append("x"))
        emitter.emit(ClonerEvents.PAGE_LOADED, None)
        emitter.emit(ClonerEvents.PAGE_LOADED, None)

        assert calls == ["x"]

    def test_callback_exception_does_not_break_other_listeners(self):
        emitter = EventEmitter()
        calls = []

        def bad_callback(d):
            raise RuntimeError("boom")

        emitter.on(ClonerEvents.PAGE_LOADED, bad_callback)
        emitter.on(ClonerEvents.PAGE_LOADED, lambda d: calls.append("survived"))
        emitter.emit(ClonerEvents.PAGE_LOADED, None)

        assert calls == ["survived"]

    def test_remove_all_listeners(self):
        emitter = EventEmitter()
        emitter.on(ClonerEvents.PAGE_LOADED, lambda d: None)
        emitter.on(ClonerEvents.CLONE_COMPLETE, lambda d: None)

        emitter.remove_all_listeners()

        assert emitter.listener_count(ClonerEvents.PAGE_LOADED) == 0
        assert emitter.listener_count(ClonerEvents.CLONE_COMPLETE) == 0

    def test_listener_count(self):
        emitter = EventEmitter()
        assert emitter.listener_count(ClonerEvents.PAGE_LOADED) == 0

        emitter.on(ClonerEvents.PAGE_LOADED, lambda d: None)
        emitter.on(ClonerEvents.PAGE_LOADED, lambda d: None)

        assert emitter.listener_count(ClonerEvents.PAGE_LOADED) == 2
