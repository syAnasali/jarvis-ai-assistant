"""PluginController managing plugin lifecycle operations and QThread workers."""

from typing import Any, Dict, List, Optional
from PySide6.QtCore import QObject, Signal
from app.core.logger import JarvisLogger
from app.gui.plugins.worker import PluginWorker

logger = JarvisLogger.get_logger("gui_plugin_controller")


class PluginController(QObject):
    """Controller orchestrating Plugin Manager actions."""

    plugin_status_changed = Signal(str, str)
    log_received = Signal(str)
    status_updated = Signal(str)

    def __init__(self, plugin_manager: Optional[Any] = None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.plugin_manager = plugin_manager
        self.active_worker: Optional[PluginWorker] = None

    def execute_plugin_action(self, action: str, plugin_id: str) -> None:
        """Triggers asynchronous plugin lifecycle action worker."""
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.wait()

        self.active_worker = PluginWorker(action=action, plugin_id=plugin_id, plugin_manager=self.plugin_manager, parent=self)
        self.active_worker.plugin_status_changed.connect(self.plugin_status_changed.emit)
        self.active_worker.log_emitted.connect(self.log_received.emit)
        self.active_worker.status_changed.connect(self.status_updated.emit)
        self.active_worker.start()
