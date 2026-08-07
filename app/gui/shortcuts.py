"""GlobalShortcutManager binding application-wide keyboard hotkeys."""

from typing import Callable, Optional
from PySide6.QtWidgets import QMainWindow
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import QObject


class GlobalShortcutManager(QObject):
    """Binds and manages application-wide keyboard shortcuts."""

    def __init__(self, main_window: QMainWindow) -> None:
        super().__init__(main_window)
        self.main_window = main_window

    def bind_shortcut(self, key_sequence: str, callback: Callable[[], None]) -> QShortcut:
        """Binds a key sequence string (e.g. 'Ctrl+Shift+P') to a callback."""
        shortcut = QShortcut(QKeySequence(key_sequence), self.main_window)
        shortcut.activated.connect(callback)
        return shortcut
