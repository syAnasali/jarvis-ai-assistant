"""PluginDetailsWidget manifest inspector displaying capabilities and registered hooks."""

from typing import Any, Dict, Optional
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt
from app.gui.plugins.permissions import PluginPermissionsWidget


class PluginDetailsWidget(QFrame):
    """Inspector panel rendering selected plugin manifest, registered tools, and hooks."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setStyleSheet("background-color: #1a1d29; border: 1px solid #242838; border-radius: 8px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        lbl_hdr = QLabel("📦 Plugin Manifest Inspector")
        lbl_hdr.setStyleSheet("font-weight: 600; color: #818cf8; font-size: 12px;")
        layout.addWidget(lbl_hdr)

        self.lbl_name = QLabel("Select a plugin to view manifest details.")
        self.lbl_name.setWordWrap(True)
        self.lbl_name.setStyleSheet("color: #e2e8f0; font-size: 13px; font-weight: 600;")
        layout.addWidget(self.lbl_name)

        self.lbl_author = QLabel("Author: -")
        self.lbl_author.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(self.lbl_author)

        self.lbl_tools = QLabel("Registered Tools: -")
        self.lbl_tools.setStyleSheet("color: #38bdf8; font-size: 11px;")
        layout.addWidget(self.lbl_tools)

        self.lbl_hooks = QLabel("Planner/Voice Hooks: -")
        self.lbl_hooks.setStyleSheet("color: #38bdf8; font-size: 11px;")
        layout.addWidget(self.lbl_hooks)

        # Embedded permissions widget
        self.permissions_widget = PluginPermissionsWidget(self)
        layout.addWidget(self.permissions_widget)

    def set_plugin(self, plugin_dict: Dict[str, Any]) -> None:
        """Sets selected plugin data."""
        self.lbl_name.setText(f"{plugin_dict.get('name', 'Plugin')} (v{plugin_dict.get('version', '1.0.0')})")
        self.lbl_author.setText(f"Author: {plugin_dict.get('author', 'Jarvis Core')}")
        self.lbl_tools.setText(f"Registered Tools: {', '.join(plugin_dict.get('tools', []))}")
        self.lbl_hooks.setText(f"Planner/Voice Hooks: {', '.join(plugin_dict.get('hooks', []))}")
        self.permissions_widget.set_permissions(plugin_dict.get("permissions", []))
