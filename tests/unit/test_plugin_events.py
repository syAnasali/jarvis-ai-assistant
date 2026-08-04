"""Unit tests for PluginEventBus."""

import pytest
from app.plugins.events import PluginEventBus
from app.plugins.models import PluginEvent


def test_event_bus_subscribe_and_emit():
    bus = PluginEventBus()
    received = []

    def handler(event: PluginEvent):
        received.append(event)

    bus.subscribe("test_event", handler)

    event = PluginEvent(event_type="test_event", payload={"val": 42})
    bus.emit(event)

    assert len(received) == 1
    assert received[0].payload["val"] == 42


def test_event_bus_unsubscribe():
    bus = PluginEventBus()
    received = []

    def handler(event: PluginEvent):
        received.append(event)

    bus.subscribe("test_event", handler)
    bus.unsubscribe("test_event", handler)

    event = PluginEvent(event_type="test_event", payload={"val": 42})
    bus.emit(event)

    assert len(received) == 0
