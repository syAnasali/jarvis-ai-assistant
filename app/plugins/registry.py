"""Thread-safe Plugin Registry maintaining plugin catalog state and metadata."""

import threading
from typing import Dict, List, Optional
from app.core.logger import JarvisLogger
from app.plugins.models import PluginInfo, PluginStatus

logger = JarvisLogger.get_logger("plugin_registry")


class PluginRegistry:
    """Thread-safe catalog storing active, inactive, and failed plugin information."""

    def __init__(self) -> None:
        self._plugins: Dict[str, PluginInfo] = {}
        self._lock = threading.Lock()

    def register_plugin(self, info: PluginInfo) -> None:
        """Registers or updates a plugin entry in the catalog."""
        with self._lock:
            self._plugins[info.manifest.id] = info
        logger.info(f"Registered plugin '{info.manifest.id}' (status='{info.status.value}') in registry.")

    def unregister_plugin(self, plugin_id: str) -> None:
        """Removes a plugin entry from the catalog."""
        with self._lock:
            if plugin_id in self._plugins:
                del self._plugins[plugin_id]
        logger.info(f"Unregistered plugin '{plugin_id}' from registry.")

    def get_plugin(self, plugin_id: str) -> Optional[PluginInfo]:
        """Retrieves a PluginInfo entry by plugin_id."""
        with self._lock:
            return self._plugins.get(plugin_id)

    def list_plugins(self) -> List[PluginInfo]:
        """Lists all registered plugins."""
        with self._lock:
            return list(self._plugins.values())

    def update_status(self, plugin_id: str, status: PluginStatus, error_message: Optional[str] = None) -> None:
        """Updates the status and error state of a registered plugin."""
        with self._lock:
            info = self._plugins.get(plugin_id)
            if info:
                info.status = status
                if error_message is not None:
                    info.error_message = error_message
        logger.info(f"Updated plugin '{plugin_id}' status to '{status.value}'.")
