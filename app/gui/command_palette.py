"""CommandPaletteDialog modal popup triggered via Ctrl+Shift+P for instant command navigation."""

from typing import Any, Callable, Dict, List, Optional
from PySide6.QtWidgets import (
    QDialog,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Signal, Qt


class CommandPaletteDialog(QDialog):
    """Command palette dialog allowing quick search and keyboard execution of app views and actions."""

    command_selected = Signal(str)  # Emits target page or action name

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Jarvis Command Palette (Ctrl+Shift+P)")
        self.setFixedWidth(520)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.setStyleSheet("""
            QDialog {
                background-color: #1a1d29;
                border: 2px solid #6366f1;
                border-radius: 8px;
            }
            QLineEdit {
                background-color: #12141c;
                color: #e2e8f0;
                font-size: 13px;
                padding: 8px;
                border: 1px solid #242838;
                border-radius: 6px;
            }
            QListWidget {
                background-color: #12141c;
                color: #e2e8f0;
                border: none;
                border-radius: 6px;
            }
            QListWidget::item:selected {
                background-color: #312e81;
                color: #818cf8;
                font-weight: 600;
            }
        """)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Type a command or page name (e.g. 'chat', 'planner', 'theme')...")
        layout.addWidget(self.txt_search)

        self.list_commands = QListWidget()
        layout.addWidget(self.list_commands)

        self.commands: List[Dict[str, str]] = [
            {"name": "💬 Go to Chat View", "target": "chat"},
            {"name": "🗺️ Go to Planner Dashboard", "target": "planner"},
            {"name": "🧠 Go to Memory Center", "target": "memory"},
            {"name": "📚 Go to Knowledge Base (RAG)", "target": "knowledge"},
            {"name": "👁️ Go to Vision Workspace", "target": "vision"},
            {"name": "🎙️ Go to Voice Workspace", "target": "voice"},
            {"name": "🔌 Go to Plugin Manager", "target": "plugins"},
            {"name": "📊 Go to Diagnostics & Observability", "target": "diagnostics"},
            {"name": "⚙️ Go to Settings", "target": "settings"},
            {"name": "🌓 Toggle Dark/Light Theme", "target": "action_toggle_theme"},
            {"name": "📥 Export Telemetry Report", "target": "action_export_telemetry"},
        ]

        self.populate_list(self.commands)

        self.txt_search.textChanged.connect(self._filter_commands)
        self.list_commands.itemActivated.connect(self._on_item_activated)

    def populate_list(self, items: List[Dict[str, str]]) -> None:
        """Populates command list."""
        self.list_commands.clear()
        for item in items:
            l_item = QListWidgetItem(item["name"])
            l_item.setData(Qt.UserRole, item["target"])
            self.list_commands.addItem(l_item)

        if self.list_commands.count() > 0:
            self.list_commands.setCurrentRow(0)

    def _filter_commands(self, text: str) -> None:
        filtered = [c for c in self.commands if text.lower() in c["name"].lower() or text.lower() in c["target"].lower()]
        self.populate_list(filtered)

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        target = item.data(Qt.UserRole)
        if target:
            self.command_selected.emit(target)
            self.accept()

    def keyPressEvent(self, event: Any) -> None:
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            curr = self.list_commands.currentItem()
            if curr:
                self._on_item_activated(curr)
        elif event.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)
