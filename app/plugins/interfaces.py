"""Abstract interface contracts for Plugins, EventBus, and PluginSDK boundaries."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional
from app.plugins.models import PluginEvent, PluginManifest


class Plugin(ABC):
    """Abstract Base Class exposing mandatory lifecycle and capability hooks for all Jarvis plugins."""

    @abstractmethod
    def initialize(self, sdk: Any) -> None:
        """Initializes the plugin with the restricted PluginSDK instance."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Cleans up plugin resources upon unloading or application shutdown."""
        pass

    def health_check(self) -> Dict[str, Any]:
        """Returns plugin health status and metrics."""
        return {"status": "ok"}

    def register_tools(self, sdk: Any) -> None:
        """Registers custom tools via sdk.tools.register()."""
        pass

    def register_voice_commands(self, sdk: Any) -> None:
        """Registers voice commands or spoken triggers."""
        pass

    def register_memory_hooks(self, sdk: Any) -> None:
        """Registers memory lookup or persistence hooks."""
        pass

    def register_planner_hooks(self, sdk: Any) -> None:
        """Registers planner task formulation hooks."""
        pass

    def register_events(self, sdk: Any) -> None:
        """Subscribes to lifecycle or execution events via sdk.events."""
        pass


class EventBus(ABC):
    """Abstract interface for publish/subscribe event handling."""

    @abstractmethod
    def subscribe(self, event_type: str, handler: Callable[[PluginEvent], None]) -> None:
        """Subscribes a handler callback function to an event_type."""
        pass

    @abstractmethod
    def unsubscribe(self, event_type: str, handler: Callable[[PluginEvent], None]) -> None:
        """Unsubscribes a handler callback from an event_type."""
        pass

    @abstractmethod
    def emit(self, event: PluginEvent) -> None:
        """Publishes an event to all subscribed listeners."""
        pass
