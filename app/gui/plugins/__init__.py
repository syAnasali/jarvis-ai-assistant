"""Plugin Manager package exports."""

from app.gui.plugins.permissions import PluginPermissionsWidget
from app.gui.plugins.logs import PluginLogsWidget
from app.gui.plugins.details import PluginDetailsWidget
from app.gui.plugins.marketplace import PluginMarketplaceWidget
from app.gui.plugins.browser import PluginBrowserWidget
from app.gui.plugins.worker import PluginWorker
from app.gui.plugins.controller import PluginController

__all__ = [
    "PluginPermissionsWidget",
    "PluginLogsWidget",
    "PluginDetailsWidget",
    "PluginMarketplaceWidget",
    "PluginBrowserWidget",
    "PluginWorker",
    "PluginController",
]
