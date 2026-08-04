"""JarvisGuiApplication PySide6 application bootstrapper."""

import sys
from typing import List, Optional
from PySide6.QtWidgets import QApplication
from app.core.logger import JarvisLogger
from app.gui.main_window import MainWindow
from app.gui.settings import GuiSettingsManager
from app.gui.theme import ThemeManager

logger = JarvisLogger.get_logger("gui_application")


class JarvisGuiApplication:
    """Bootstraps PySide6 QApplication, ThemeManager, GuiSettingsManager, and MainWindow."""

    def __init__(self, args: Optional[List[str]] = None) -> None:
        self.args = args or sys.argv
        self.app = QApplication.instance() or QApplication(self.args)

        self.settings_mgr = GuiSettingsManager()
        self.main_window = MainWindow(settings_manager=self.settings_mgr)

        # Apply saved theme
        saved_theme = self.settings_mgr.get_theme()
        ThemeManager.apply_theme(self.app, saved_theme)

    def run(self) -> int:
        """Shows MainWindow and enters PySide6 Qt event loop."""
        logger.info("Starting Jarvis Desktop GUI Application event loop...")
        self.main_window.show()
        return self.app.exec()
