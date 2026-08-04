"""PluginMarketplaceWidget UI placeholder for online plugin discovery and installation."""

from typing import Optional
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt


class PluginMarketplaceWidget(QWidget):
    """UI catalog placeholder preparing future online plugin marketplace installs."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header Search Toolbar
        hdr_row = QHBoxLayout()
        lbl_title = QLabel("🌐 Jarvis Online Plugin Marketplace Catalog")
        lbl_title.setStyleSheet("font-weight: 600; color: #818cf8; font-size: 13px;")
        hdr_row.addWidget(lbl_title)
        hdr_row.addStretch()

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search community plugins & extensions...")
        self.txt_search.setFixedWidth(280)
        hdr_row.addWidget(self.txt_search)

        layout.addLayout(hdr_row)

        # Catalog Grid / Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(8)

        catalog_items = [
            {"name": "GitHub Assistant Integration", "version": "1.2.0", "author": "Community", "desc": "Automates GitHub PR reviews, issue creation, and repo indexing.", "installed": False},
            {"name": "Spotify & Media Controls", "version": "0.9.1", "author": "Community", "desc": "Voice commands to control Spotify playback and desktop volume.", "installed": False},
            {"name": "Notion Knowledge Sync", "version": "2.0.4", "author": "Jarvis Team", "desc": "Bi-directional RAG knowledge base sync with Notion workspaces.", "installed": False},
        ]

        for item in catalog_items:
            card = QFrame()
            card.setObjectName("cardFrame")
            card.setStyleSheet("background-color: #1a1d29; border: 1px solid #242838; border-radius: 8px; padding: 8px;")
            l = QHBoxLayout(card)

            v_l = QVBoxLayout()
            t = QLabel(f"📦 {item['name']} (v{item['version']})")
            t.setStyleSheet("font-weight: 600; color: #6366f1; font-size: 12px;")
            v_l.addWidget(t)

            d = QLabel(item["desc"])
            d.setWordWrap(True)
            d.setStyleSheet("color: #94a3b8; font-size: 11px;")
            v_l.addWidget(d)
            l.addLayout(v_l)

            l.addStretch()

            btn = QPushButton("Install")
            btn.setFixedSize(70, 28)
            btn.setStyleSheet("background-color: #312e81; color: #818cf8; font-weight: 600; border-radius: 4px;")
            l.addWidget(btn)

            c_layout.addWidget(card)

        c_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)
