"""PluginsView assembling PluginBrowserWidget, PluginDetailsWidget, PluginLogsWidget, and PluginMarketplaceWidget."""

from typing import Any, Dict, Optional
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt
from app.gui.plugins.browser import PluginBrowserWidget
from app.gui.plugins.controller import PluginController
from app.gui.plugins.details import PluginDetailsWidget
from app.gui.plugins.logs import PluginLogsWidget
from app.gui.plugins.marketplace import PluginMarketplaceWidget


class PluginsView(QWidget):
    """Plugin Manager workspace interface powering extension lifecycle and permissions inspection."""

    def __init__(self, plugin_manager: Optional[Any] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.controller = PluginController(plugin_manager=plugin_manager, parent=self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Header Toolbar
        hdr_layout = QHBoxLayout()
        lbl_title = QLabel("Plugin Manager & Extensions")
        lbl_title.setObjectName("headerTitle")
        hdr_layout.addWidget(lbl_title)
        hdr_layout.addStretch()

        self.btn_reload_all = QPushButton("🔄 Hot-Reload All")
        self.btn_reload_all.clicked.connect(lambda: self.controller.execute_plugin_action("reload", "all"))
        hdr_layout.addWidget(self.btn_reload_all)

        self.btn_health = QPushButton("🏥 Health Check")
        self.btn_health.clicked.connect(lambda: self.controller.execute_plugin_action("health_check", "all"))
        hdr_layout.addWidget(self.btn_health)

        layout.addLayout(hdr_layout)

        # 2. Main Tab Widget (Installed Plugins vs Marketplace Catalog)
        self.tabs = QTabWidget(self)

        # Tab 1: Installed Plugins
        tab_installed = QWidget()
        inst_layout = QVBoxLayout(tab_installed)
        inst_layout.setContentsMargins(0, 8, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        self.browser = PluginBrowserWidget(self)
        splitter.addWidget(self.browser)

        # Right Column: Inspector Details + Logs
        right_col = QWidget()
        r_layout = QVBoxLayout(right_col)
        r_layout.setContentsMargins(0, 0, 0, 0)
        r_layout.setSpacing(8)

        self.details_inspector = PluginDetailsWidget(self)
        r_layout.addWidget(self.details_inspector)

        self.logs_widget = PluginLogsWidget(self)
        r_layout.addWidget(self.logs_widget)

        splitter.addWidget(right_col)
        splitter.setSizes([550, 450])

        inst_layout.addWidget(splitter)
        self.tabs.addTab(tab_installed, "Installed Plugins")

        # Tab 2: Marketplace Catalog
        self.marketplace = PluginMarketplaceWidget(self)
        self.tabs.addTab(self.marketplace, "Marketplace Catalog")

        layout.addWidget(self.tabs)

        # Wire Signals
        self.browser.plugin_selected.connect(self.details_inspector.set_plugin)
        self.browser.action_triggered.connect(self.controller.execute_plugin_action)

        self.controller.plugin_status_changed.connect(self._on_plugin_status_changed)
        self.controller.log_received.connect(self.logs_widget.append_log)

    def _on_plugin_status_changed(self, plugin_id: str, new_status: str) -> None:
        for p in self.browser.plugins:
            if p.get("id") == plugin_id or plugin_id == "all":
                p["status"] = new_status
        self.browser.populate_table(self.browser.plugins)
