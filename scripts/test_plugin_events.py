"""Diagnostic script testing PluginEventBus publish/subscribe event dispatching."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, ".")

from app.plugins.events import PluginEventBus
from app.plugins.models import PluginEvent


def main() -> None:
    print("==================================================")
    print("Testing Plugin Event Bus Diagnostics")
    print("==================================================")

    bus = PluginEventBus()
    received_events = []

    def on_custom_event(event: PluginEvent) -> None:
        received_events.append(event)

    bus.subscribe("custom_test_event", on_custom_event)

    event = PluginEvent(event_type="custom_test_event", payload={"data": 123}, source_plugin_id="test_plugin")
    bus.emit(event)

    print(f"Events Received: {len(received_events)}")
    assert len(received_events) == 1
    assert received_events[0].payload["data"] == 123
    print("PASS: Event Bus publish/subscribe verified.")

    print("\nALL PLUGIN EVENT DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
