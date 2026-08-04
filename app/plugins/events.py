"""Plugin Event Bus providing thread-safe publish/subscribe event dispatching."""

import threading
from typing import Callable, Dict, List, Set
from app.core.logger import JarvisLogger
from app.plugins.interfaces import EventBus
from app.plugins.models import PluginEvent

logger = JarvisLogger.get_logger("plugin_event_bus")

EventHandler = Callable[[PluginEvent], None]


class PluginEventBus(EventBus):
    """Thread-safe publish/subscribe event bus for plugin lifecycle and system events."""

    def __init__(self) -> None:
        self._listeners: Dict[str, List[EventHandler]] = {}
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribes a handler callback function to an event_type."""
        with self._lock:
            if event_type not in self._listeners:
                self._listeners[event_type] = []
            if handler not in self._listeners[event_type]:
                self._listeners[event_type].append(handler)
        logger.info(f"Subscribed handler '{handler.__name__ if hasattr(handler, '__name__') else str(handler)}' to event '{event_type}'.")

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribes a handler callback from an event_type."""
        with self._lock:
            if event_type in self._listeners and handler in self._listeners[event_type]:
                self._listeners[event_type].remove(handler)
        logger.info(f"Unsubscribed handler from event '{event_type}'.")

    def emit(self, event: PluginEvent) -> None:
        """Publishes an event to all subscribed listeners."""
        with self._lock:
            handlers = list(self._listeners.get(event.event_type, []))

        logger.info(f"Emitting event '{event.event_type}' (source='{event.source_plugin_id}') to {len(handlers)} listeners...")
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error executing event listener for '{event.event_type}': {e}")

    def clear(self) -> None:
        """Clears all subscribed listeners."""
        with self._lock:
            self._listeners.clear()
