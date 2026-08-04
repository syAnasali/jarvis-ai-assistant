"""GuiSettingsManager persisting window geometry, active page, sidebar state, and themes."""

from typing import Any, Dict, Optional
from PySide6.QtCore import QSettings
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("gui_settings")


class GuiSettingsManager:
    """Thread-safe settings manager persisting GUI configuration via QSettings."""

    def __init__(self, organization: str = "JarvisAI", application: str = "JarvisAssistant") -> None:
        self.settings = QSettings(organization, application)


    def get_theme(self) -> str:
        """Returns the saved theme name ('dark' or 'light')."""
        return str(self.settings.value("theme", "dark"))

    def set_theme(self, theme_name: str) -> None:
        """Saves the theme name ('dark' or 'light')."""
        self.settings.setValue("theme", theme_name)
        logger.info(f"Saved GUI theme preference: '{theme_name}'.")

    def is_sidebar_collapsed(self) -> bool:
        """Returns whether the sidebar is collapsed."""
        val = self.settings.value("sidebar_collapsed", False)
        if isinstance(val, bool):
            return val
        return str(val).lower() == "true"

    def set_sidebar_collapsed(self, collapsed: bool) -> None:
        """Saves sidebar collapsed state."""
        self.settings.setValue("sidebar_collapsed", collapsed)

    def get_active_page(self) -> str:
        """Returns the last active page name."""
        return str(self.settings.value("active_page", "chat"))

    def set_active_page(self, page_name: str) -> None:
        """Saves the active page name."""
        self.settings.setValue("active_page", page_name)

    def get_window_geometry(self) -> Optional[Any]:
        """Returns saved QByteArray window geometry."""
        return self.settings.value("window_geometry", None)

    def set_window_geometry(self, geometry: Any) -> None:
        """Saves QByteArray window geometry."""
        self.settings.setValue("window_geometry", geometry)
