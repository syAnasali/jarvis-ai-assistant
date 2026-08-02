"""Chat list and bubble widgets supporting markdown and copyable code blocks."""

import re
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QFrame, QHBoxLayout, 
    QLabel, QPushButton, QTextBrowser, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QGuiApplication, QColor
from app.ui.theme import (
    BUBBLE_USER, BUBBLE_ASSISTANT, BUBBLE_SYSTEM, BUBBLE_TOOL,
    TEXT_PRIMARY, TEXT_SECONDARY, BG_CARD, BORDER_COLOR, ACCENT_BLUE
)

logger = logging.getLogger("gui_chat_view")


class CodeBlockWidget(QFrame):
    """Container for rendering a code block with a header and Copy button."""

    def __init__(self, language: str, code: str, parent=None) -> None:
        super().__init__(parent)
        self.code = code.strip()
        self.setObjectName("codeBlock")
        
        self.setStyleSheet(f"""
            QFrame#codeBlock {{
                background-color: #1e1e24;
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header Bar
        header = QFrame()
        header.setFixedHeight(30)
        header.setStyleSheet(f"""
            QFrame {{
                background-color: #16161a;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                border-bottom: 1px solid {BORDER_COLOR};
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 0, 10, 0)
        
        lang_label = QLabel(language.upper() if language else "CODE")
        lang_label.setStyleSheet("color: #9ba1a6; font-size: 11px; font-weight: bold;")
        header_layout.addWidget(lang_label)
        
        header_layout.addStretch()
        
        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #3a86ff;
                font-size: 11px;
                font-weight: bold;
                padding: 2px 6px;
            }
            QPushButton:hover {
                color: #2563eb;
                text-decoration: underline;
            }
        """)
        self.copy_btn.clicked.connect(self._copy_code)
        header_layout.addWidget(self.copy_btn)
        
        layout.addWidget(header)
        
        # Code Display
        self.editor = QTextBrowser()
        self.editor.setPlainText(self.code)
        self.editor.setReadOnly(True)
        self.editor.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.editor.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.editor.setStyleSheet(f"""
            QTextBrowser {{
                background-color: transparent;
                border: none;
                color: #d4d4d8;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                padding: 10px;
            }}
        """)
        # Dynamic height sizing based on text length (bounded between 60 and 300px)
        doc_height = int(self.editor.document().size().height()) * 1.2
        self.editor.setFixedHeight(max(60, min(300, doc_height + 25)))
        
        layout.addWidget(self.editor)

    @Slot()
    def _copy_code(self) -> None:
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.code)
        self.copy_btn.setText("Copied!")
        self.copy_btn.setEnabled(False)
        # Restore button text after 2 seconds
        self.copy_btn.setStyleSheet("color: #06d6a0;")  # Accent green
        from PySide6.QtCore import QTimer
        QTimer.singleShot(2000, self._reset_copy_btn)

    def _reset_copy_btn(self) -> None:
        self.copy_btn.setText("Copy")
        self.copy_btn.setEnabled(True)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #3a86ff;
                font-size: 11px;
                font-weight: bold;
                padding: 2px 6px;
            }
            QPushButton:hover {
                color: #2563eb;
                text-decoration: underline;
            }
        """)


class ChatBubble(QWidget):
    """Individual chat bubble for rendering Markdown text and block components."""

    def __init__(self, role: str, text: str, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        
        # Outer bubble frame
        self.frame = QFrame()
        self.frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        
        if role == "user":
            self.frame.setStyleSheet(BUBBLE_USER)
            bubble_layout = QHBoxLayout(self)
            bubble_layout.addStretch()
            bubble_layout.addWidget(self.frame)
            content_margins = (8, 8, 8, 8)
        elif role == "assistant":
            self.frame.setStyleSheet(BUBBLE_ASSISTANT)
            bubble_layout = QHBoxLayout(self)
            bubble_layout.addWidget(self.frame)
            bubble_layout.addStretch()
            content_margins = (12, 12, 12, 12)
        elif role == "system":
            self.frame.setStyleSheet(BUBBLE_SYSTEM)
            bubble_layout = QHBoxLayout(self)
            bubble_layout.addWidget(self.frame)
            bubble_layout.addStretch()
            content_margins = (8, 8, 8, 8)
        else: # tool
            self.frame.setStyleSheet(BUBBLE_TOOL)
            bubble_layout = QHBoxLayout(self)
            bubble_layout.addWidget(self.frame)
            bubble_layout.addStretch()
            content_margins = (8, 8, 8, 8)
            
        frame_layout = QVBoxLayout(self.frame)
        frame_layout.setContentsMargins(*content_margins)
        frame_layout.setSpacing(6)
        
        # Parse text into code blocks and normal text blocks
        parts = re.split(r'```', text)
        for i, part in enumerate(parts):
            if i % 2 == 0:
                # Normal text chunk -> Markdown rendering
                if not part.strip():
                    continue
                browser = QTextBrowser()
                browser.setOpenExternalLinks(True)
                browser.setMarkdown(part.strip())
                browser.setStyleSheet("background-color: transparent; border: none; padding: 0px;")
                # Compute dynamic height
                browser.document().adjustSize()
                h = int(browser.document().size().height())
                browser.setFixedHeight(h + 10)
                frame_layout.addWidget(browser)
            else:
                # Fenced code block chunk
                lines = part.split("\n", 1)
                lang = lines[0].strip() if lines[0].strip() else "code"
                code = lines[1] if len(lines) > 1 else ""
                code_widget = CodeBlockWidget(lang, code)
                frame_layout.addWidget(code_widget)
                
        layout.addLayout(bubble_layout)


class ChatViewWidget(QScrollArea):
    """Scrollable chat log view displaying bubbles sequentially."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
        """)
        
        self.container = QWidget()
        self.container.setStyleSheet("background-color: transparent;")
        
        self.scroll_layout = QVBoxLayout(self.container)
        self.scroll_layout.setContentsMargins(10, 10, 10, 10)
        self.scroll_layout.setSpacing(5)
        
        # Spacer pushing bubbles to the bottom of the list
        self.spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.scroll_layout.addItem(self.spacer)
        
        self.setWidget(self.container)
        self.bubbles = []

    def add_message(self, role: str, text: str) -> None:
        """Appends a new message bubble to the chat log."""
        bubble = ChatBubble(role, text)
        self.scroll_layout.addWidget(bubble)
        self.bubbles.append(bubble)
        # Scroll to bottom
        self.scroll_to_bottom()

    def clear(self) -> None:
        """Removes all chat bubbles."""
        for bubble in self.bubbles:
            self.scroll_layout.removeWidget(bubble)
            bubble.deleteLater()
        self.bubbles.clear()

    def scroll_to_bottom(self) -> None:
        """Scrolls container view slider to bottom position."""
        # Simple deferred call to allow layout updates to finish
        from PySide6.QtCore import QTimer
        QTimer.singleShot(50, self._do_scroll)

    def _do_scroll(self) -> None:
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())
