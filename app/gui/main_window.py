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
        app_container: Optional[Any] = None,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Jarvis AI Assistant")
        self.resize(1280, 800)

        self.settings_mgr = settings_manager or GuiSettingsManager()
        self.app_container = app_container
        approval_manager = None
        if self.app_container and hasattr(self.app_container, "container"):
            if self.app_container.container.has("approval_manager"):
                approval_manager = self.app_container.container.get("approval_manager")

        from app.gui.approval import ApprovalController, ApprovalDialog
        self.approval_ctrl = ApprovalController(approval_manager=approval_manager, parent=self)
        self.approval_ctrl.approval_requested.connect(self._on_approval_requested)
        self.approval_ctrl.action_resolved.connect(self._on_approval_action_resolved)

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

        # Polish Managers
        from app.gui.animations import PageTransitionManager
        from app.gui.shortcuts import GlobalShortcutManager
        from app.gui.session import SessionRestoreManager

        self.transition_mgr = PageTransitionManager(self.stacked_widget, self)
        self.session_mgr = SessionRestoreManager()
        self.shortcut_mgr = GlobalShortcutManager(self)
        self._bind_global_shortcuts()

        # Restore saved settings
        self._restore_settings()


    def _bind_global_shortcuts(self) -> None:
        """Binds global hotkeys."""
        self.shortcut_mgr.bind_shortcut("Ctrl+Shift+P", self._open_command_palette)
        self.shortcut_mgr.bind_shortcut("Ctrl+T", self._on_theme_toggled)
        self.shortcut_mgr.bind_shortcut("F11", self._toggle_fullscreen)

    def _open_command_palette(self) -> None:
        """Opens Command Palette popup."""
        from app.gui.command_palette import CommandPaletteDialog
        dialog = CommandPaletteDialog(self)
        dialog.command_selected.connect(self._on_command_palette_selected)
        dialog.exec()

    def _on_command_palette_selected(self, target: str) -> None:
        if target == "action_toggle_theme":
            self._on_theme_toggled()
        elif target in self.nav_mgr.pages:
            self.sidebar.select_page(target)

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _register_views(self) -> None:
        """Instantiates and registers all 9 workspace views connected to backend services."""
        agent_runner = None
        if self.app_container and hasattr(self.app_container, "container"):
            if self.app_container.container.has("agent_runner"):
                agent_runner = self.app_container.container.get("agent_runner")

        self.nav_mgr.register_page("chat", ChatView(agent_runner=agent_runner, parent=self))
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

    def _on_approval_requested(self, action_dict: dict) -> None:
        """Launches modal ApprovalDialog on pending tool approval request."""
        from app.gui.approval import ApprovalDialog
        dialog = ApprovalDialog(action_dict, self)
        decision = "APPROVE" if dialog.exec() else "REJECT"
        self.approval_ctrl.resolve_action(decision, action_dict.get("id", ""))

    def _on_approval_action_resolved(self, action_id: str, decision: str) -> None:
        """Handles approval action completion and posts GUI chat update."""
        if hasattr(self, "nav_mgr") and "chat" in getattr(self.nav_mgr, "pages", {}):
            chat_idx = self.nav_mgr.pages["chat"]
            chat_view = self.stacked_widget.widget(chat_idx)
            if chat_view and hasattr(chat_view, "controller"):
                ctrl = chat_view.controller
                folder_name = "New Folder"
                target_path = "Desktop"
                try:
                    from app.core.constants import DATABASE_PATH
                    from app.approval.repository import SQLiteApprovalRepository
                    repo = SQLiteApprovalRepository(database_path=DATABASE_PATH)
                    target_action = repo.get(action_id)
                    if target_action and target_action.arguments:
                        args = target_action.arguments
                        rel_p = args.get("relative_path") or args.get("path") or args.get("directory_path") or args.get("folder_name") or args.get("name") or args.get("target") or "New Folder"
                        from pathlib import Path
                        folder_name = Path(rel_p).name
                        target_path = f"Desktop\\{folder_name}"
                except Exception:
                    pass

                if decision.upper() in ("APPROVED", "APPROVE"):
                    msg_content = f"✅ **Tool Action Approved & Executed!**\n\nSuccessfully created folder `{folder_name}` on Desktop at:\n`{target_path}`"
                else:
                    msg_content = f"❌ **Tool Action Rejected!**\n\nExecution for action `{action_id}` was rejected by user."

                from app.gui.chat.models import ChatMessage, MessageType
                confirm_msg = ChatMessage(
                    message_type=MessageType.ASSISTANT,
                    content=msg_content
                )
                ctrl.active_session.messages.append(confirm_msg)
                ctrl.message_added.emit(confirm_msg)
                ctrl.save_sessions()

    def closeEvent(self, event: Any) -> None:
        """Saves geometry on window close."""
        self.settings_mgr.set_window_geometry(self.saveGeometry())
        super().closeEvent(event)
