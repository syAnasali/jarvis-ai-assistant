"""SidebarNav collapsible sidebar navigation menu for switching main application pages."""

from typing import Dict, Optional
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Signal, Qt
from app.gui.icons import IconManager


class SidebarNav(QWidget):
    """Sidebar navigation menu emitting page_changed signals for all 9 application views."""

    page_changed = Signal(str)

    PAGE_ITEMS = [
        ("chat", "Chat"),
        ("planner", "Planner"),
        ("memory", "Memory"),
        ("knowledge", "Knowledge"),
        ("vision", "Vision"),
        ("voice", "Voice"),
        ("plugins", "Plugins"),
        ("diagnostics", "Diagnostics"),
        ("settings", "Settings"),
    ]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebarWidget")
        self.setFixedWidth(200)
        self._is_collapsed = False
        self.buttons: Dict[str, QPushButton] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(4)

        # Header Title
        header_layout = QHBoxLayout()
        self.lbl_logo = QLabel("JARVIS")
        self.lbl_logo.setObjectName("headerTitle")
        header_layout.addWidget(self.lbl_logo)
        header_layout.addStretch()

        self.btn_toggle = QPushButton("≡")
        self.btn_toggle.setFixedSize(28, 28)
        self.btn_toggle.clicked.connect(self.toggle_collapse)
        header_layout.addWidget(self.btn_toggle)

        layout.addLayout(header_layout)
        layout.addSpacing(16)

        # Navigation Buttons
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        for page_id, page_name in self.PAGE_ITEMS:
            btn = QPushButton(page_name)
            btn.setObjectName("sidebarButton")
            btn.setCheckable(True)
            btn.setIcon(IconManager.get_icon(page_id))
            btn.clicked.connect(lambda checked=False, pid=page_id: self._on_button_clicked(pid))

            self.button_group.addButton(btn)
            self.buttons[page_id] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # Set default active page
        if "chat" in self.buttons:
            self.buttons["chat"].setChecked(True)

    def select_page(self, page_id: str) -> None:
        """Programmatically checks and selects a navigation page."""
        if page_id in self.buttons:
            self.buttons[page_id].setChecked(True)
            self.page_changed.emit(page_id)

    def _on_button_clicked(self, page_id: str) -> None:
        """Handler for navigation button click."""
        self.page_changed.emit(page_id)

    def toggle_collapse(self) -> None:
        """Toggles sidebar collapsed width."""
        self._is_collapsed = not self._is_collapsed
        if self._is_collapsed:
            self.setFixedWidth(64)
            self.lbl_logo.hide()
            for btn in self.buttons.values():
                btn.setText("")
        else:
            self.setFixedWidth(200)
            self.lbl_logo.show()
            for page_id, page_name in self.PAGE_ITEMS:
                if page_id in self.buttons:
                    self.buttons[page_id].setText(page_name)
