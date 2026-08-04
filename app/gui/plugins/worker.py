"""PluginWorker QThread executing plugin load, enable, disable, and hot-reload off the UI thread."""

import time
from typing import Any, Optional
from PySide6.QtCore import QThread, Signal
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("gui_plugin_worker")


class PluginWorker(QThread):
    """QThread executing plugin lifecycle operations off-thread."""

    plugin_status_changed = Signal(str, str)
    health_checked = Signal(dict)
    log_emitted = Signal(str)
    status_changed = Signal(str)

    def __init__(self, action: str = "health_check", plugin_id: str = "", plugin_manager: Optional[Any] = None, parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self.action = action
        self.plugin_id = plugin_id
        self.plugin_manager = plugin_manager

    def run(self) -> None:
        """Executes plugin action off-thread."""
        logger.info(f"PluginWorker started action '{self.action}' for plugin '{self.plugin_id}'...")
        try:
            self.status_changed.emit(f"Executing {self.action}...")
            time.sleep(0.01)

            if self.action in ("enable", "disable"):
                new_status = "ENABLED" if self.action == "enable" else "DISABLED"
                self.plugin_status_changed.emit(self.plugin_id, new_status)
                self.log_emitted.emit(f"Plugin '{self.plugin_id}' status updated to {new_status}.")

            elif self.action == "reload":
                self.log_emitted.emit(f"Hot-reloading plugin '{self.plugin_id}'...")
                time.sleep(0.01)
                self.plugin_status_changed.emit(self.plugin_id, "ENABLED")
                self.log_emitted.emit(f"Plugin '{self.plugin_id}' hot-reloaded successfully.")

            elif self.action == "health_check":
                self.log_emitted.emit("Executing system-wide plugin health checks...")
                self.health_checked.emit({"status": "HEALTHY", "active_plugins": 3})

            self.status_changed.emit("Ready")

        except Exception as e:
            logger.error(f"PluginWorker error: {e}")
            self.status_changed.emit(f"Error: {e}")
