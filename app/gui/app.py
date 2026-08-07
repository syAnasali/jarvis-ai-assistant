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

        # Bootstraps backend application services container
        self.backend_app = None
        try:
            from app.core.application import Application
            self.backend_app = Application()
            self.backend_app.initialize()
            self.backend_app._initialize_llm()
            self.backend_app._initialize_agent()
            logger.info("Successfully bootstrapped backend Application container for Desktop GUI.")
        except Exception as ex:
            logger.warning(f"Backend Application container running in lightweight mode: {ex}")

        self.settings_mgr = GuiSettingsManager()
        self.main_window = MainWindow(settings_manager=self.settings_mgr, app_container=self.backend_app)

        # Apply saved theme
        saved_theme = self.settings_mgr.get_theme()
        ThemeManager.apply_theme(self.app, saved_theme)

    def run(self) -> int:
        """Shows MainWindow and enters PySide6 Qt event loop."""
        logger.info("Starting Jarvis Desktop GUI Application event loop...")
        self.main_window.show()
        return self.app.exec()


if __name__ == "__main__":
    gui_app = JarvisGuiApplication()
    sys.exit(gui_app.run())

