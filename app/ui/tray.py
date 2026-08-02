"""System tray icon and menu integration for Jarvis."""

import sys
import logging
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor

logger = logging.getLogger("gui_tray")


class JarvisSystemTray(QSystemTrayIcon):
    """System tray adapter for Jarvis, handling window minimization and mode switches."""

    def __init__(self, main_window) -> None:
        super().__init__(main_window)
        self.main_window = main_window
        
        # Create standard/colored QIcon painted on the fly to avoid missing asset crashes
        self.setIcon(self._create_tray_icon())
        self.setToolTip("Jarvis AI Assistant")
        
        # Build tray context menu
        self.menu = QMenu()
        
        self.open_action = self.menu.addAction("Open Jarvis")
        self.open_action.triggered.connect(self._show_window)
        
        self.menu.addSeparator()
        
        self.voice_action = self.menu.addAction("Voice Mode")
        self.voice_action.triggered.connect(self._toggle_voice)
        
        self.terminal_action = self.menu.addAction("Terminal Mode")
        self.terminal_action.triggered.connect(self._toggle_terminal)
        
        self.settings_action = self.menu.addAction("Settings")
        self.settings_action.triggered.connect(self._open_settings)
        
        self.menu.addSeparator()
        
        self.exit_action = self.menu.addAction("Exit")
        self.exit_action.triggered.connect(self._exit_app)
        
        self.setContextMenu(self.menu)
        self.activated.connect(self._on_activated)

    def _create_tray_icon(self) -> QIcon:
        """Paints a modern, rounded tray icon dynamically."""
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor("transparent"))
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background circle
        painter.setBrush(QColor("#3a86ff"))  # Accent blue
        painter.setPen(QColor("#2f2f37"))
        painter.drawEllipse(2, 2, 28, 28)
        
        # Draw letter "J" inside
        painter.setPen(QColor("#ffffff"))
        font = painter.font()
        font.setPointSize(16)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), 0x0084, "J")  # Center aligned
        
        painter.end()
        return QIcon(pixmap)

    def _on_activated(self, reason) -> None:
        """Double clicking or clicking the tray icon shows the main window."""
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._show_window()

    def _show_window(self) -> None:
        self.main_window.show()
        self.main_window.activateWindow()
        self.main_window.raise_()

    def _toggle_voice(self) -> None:
        # Toggle voice mode inside main window
        self.main_window.toggle_voice_mode()

    def _toggle_terminal(self) -> None:
        # Minimizes GUI and prints instruction to console
        self.main_window.hide()
        logger.info("Minimizing GUI, switching focus back to terminal mode.")
        print("\n[Jarvis: Switched to Terminal Mode. GUI minimized to tray.]")

    def _open_settings(self) -> None:
        self._show_window()
        self.main_window.open_settings_dialog()

    def _exit_app(self) -> None:
        self.hide()
        self.main_window.close_and_exit()
