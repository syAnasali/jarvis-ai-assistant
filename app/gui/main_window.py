"""MainWindow application shell assembling SidebarNav, TopToolbar, QStackedWidget views, and StatusBarNav."""

from typing import Any, Optional
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt
from app.core.logger import JarvisLogger
from app.gui.dialogs import AboutDialog
from app.gui.navigation import NavigationManager
from app.gui.settings import GuiSettingsManager
from app.gui.theme import ThemeManager
from app.gui.views import (
    ChatView,
    DiagnosticsView,
    KnowledgeView,
    MemoryView,
    PlannerView,
    PluginsView,
    SettingsView,
    VisionView,
    VoiceView,
)
from app.gui.widgets import SidebarNav, StatusBarNav, TopToolbar

logger = JarvisLogger.get_logger("gui_main_window")


class MainWindow(QMainWindow):
    """Main application shell window for Jarvis Desktop GUI."""

    def __init__(
        self,
        settings_manager: Optional[GuiSettingsManager] = None,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Jarvis AI Assistant")
        self.resize(1280, 800)

        self.settings_mgr = settings_manager or GuiSettingsManager()

        # Root Central Widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Body Layout (Sidebar + Content Area)
        body_widget = QWidget()
        body_layout = QHBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # 1. Sidebar Navigation
        self.sidebar = SidebarNav(self)
        body_layout.addWidget(self.sidebar)

        # 2. Main Content Area (Toolbar + Stacked Views)
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.toolbar = TopToolbar(self)
        content_layout.addWidget(self.toolbar)

        self.stacked_widget = QStackedWidget(self)
        content_layout.addWidget(self.stacked_widget)

        body_layout.addWidget(content_area)
        root_layout.addWidget(body_widget)

        # 3. Bottom Status Bar Navigation
        self.status_bar = StatusBarNav(self)
        root_layout.addWidget(self.status_bar)

        # Navigation Manager & Page Registration
        self.nav_mgr = NavigationManager(self.stacked_widget)
        self._register_views()

        # Wire Signals
        self.sidebar.page_changed.connect(self._on_page_changed)
        self.toolbar.theme_toggled.connect(self._on_theme_toggled)
        self.toolbar.about_clicked.connect(self._on_about_clicked)

        # Restore saved settings
        self._restore_settings()

    def _register_views(self) -> None:
        """Instantiates and registers all 9 placeholder page views."""
        self.nav_mgr.register_page("chat", ChatView(self))
        self.nav_mgr.register_page("planner", PlannerView(self))
        self.nav_mgr.register_page("memory", MemoryView(self))
        self.nav_mgr.register_page("knowledge", KnowledgeView(self))
        self.nav_mgr.register_page("vision", VisionView(self))
        self.nav_mgr.register_page("voice", VoiceView(self))
        self.nav_mgr.register_page("plugins", PluginsView(self))
        self.nav_mgr.register_page("diagnostics", DiagnosticsView(self))
        self.nav_mgr.register_page("settings", SettingsView(self))

    def _on_page_changed(self, page_id: str) -> None:
        """Handles sidebar page change events."""
        if self.nav_mgr.navigate_to(page_id):
            title = page_id.replace("_", " ").title()
            self.toolbar.set_page_title(title)
            self.settings_mgr.set_active_page(page_id)

    def _on_theme_toggled(self) -> None:
        """Toggles between Dark and Light mode themes."""
        curr_theme = self.settings_mgr.get_theme()
        new_theme = "light" if curr_theme == "dark" else "dark"
        self.settings_mgr.set_theme(new_theme)
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            ThemeManager.apply_theme(app, new_theme)

    def _on_about_clicked(self) -> None:
        """Opens About dialog."""
        dialog = AboutDialog(self)
        dialog.exec()

    def _restore_settings(self) -> None:
        """Restores saved active page, theme, and sidebar state."""
        saved_page = self.settings_mgr.get_active_page()
        self.sidebar.select_page(saved_page)

        if self.settings_mgr.is_sidebar_collapsed():
            self.sidebar.toggle_collapse()

    def closeEvent(self, event: Any) -> None:
        """Saves geometry on window close."""
        self.settings_mgr.set_window_geometry(self.saveGeometry())
        super().closeEvent(event)
