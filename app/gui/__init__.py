"""Desktop GUI Foundation package exports."""

from app.gui.app import JarvisGuiApplication
from app.gui.main_window import MainWindow
from app.gui.navigation import NavigationManager
from app.gui.theme import ThemeManager
from app.gui.icons import IconManager
from app.gui.resources import ResourceLoader
from app.gui.settings import GuiSettingsManager
from app.gui.dialogs import ConfirmationDialog, ErrorDialog, AboutDialog

__all__ = [
    "JarvisGuiApplication",
    "MainWindow",
    "NavigationManager",
    "ThemeManager",
    "IconManager",
    "ResourceLoader",
    "GuiSettingsManager",
    "ConfirmationDialog",
    "ErrorDialog",
    "AboutDialog",
]
