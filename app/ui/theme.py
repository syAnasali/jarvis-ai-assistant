"""UI styling theme and stylesheets for the Jarvis Desktop GUI."""

# CSS colors
BG_MAIN = "#121214"
BG_SIDEBAR = "#1a1a1e"
BG_CARD = "#232329"
BORDER_COLOR = "#2f2f37"
TEXT_PRIMARY = "#e3e3e6"
TEXT_SECONDARY = "#9ba1a6"
ACCENT_BLUE = "#3a86ff"
ACCENT_GREEN = "#06d6a0"
ACCENT_AMBER = "#ffd166"
ACCENT_RED = "#ef476f"

STYLE_MAIN = f"""
QMainWindow {{
    background-color: {BG_MAIN};
    color: {TEXT_PRIMARY};
}}

QWidget {{
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    font-size: 13px;
    color: {TEXT_PRIMARY};
}}

QFrame#sidebar {{
    background-color: {BG_SIDEBAR};
    border-left: 1px solid {BORDER_COLOR};
}}

QLabel#sidebarHeader {{
    font-weight: bold;
    font-size: 14px;
    color: {TEXT_PRIMARY};
    border-bottom: 2px solid {ACCENT_BLUE};
    padding-bottom: 4px;
}}

QTextEdit, QLineEdit {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 6px;
}}

QTextEdit:focus, QLineEdit:focus {{
    border: 1px solid {ACCENT_BLUE};
}}

QPushButton {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {BORDER_COLOR};
    border: 1px solid {ACCENT_BLUE};
}}

QPushButton:pressed {{
    background-color: {BG_MAIN};
}}

QPushButton#voiceBtnActive {{
    background-color: {ACCENT_RED};
    color: white;
    border: 1px solid {ACCENT_RED};
}}

QPushButton#sendBtn {{
    background-color: {ACCENT_BLUE};
    color: white;
    font-weight: bold;
    border: 1px solid {ACCENT_BLUE};
}}

QPushButton#sendBtn:hover {{
    background-color: #2563eb;
}}

QScrollBar:vertical {{
    border: none;
    background: {BG_MAIN};
    width: 8px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: {BORDER_COLOR};
    min-height: 20px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: {TEXT_SECONDARY};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QStatusBar {{
    background-color: {BG_SIDEBAR};
    border-top: 1px solid {BORDER_COLOR};
    color: {TEXT_SECONDARY};
}}

QStatusBar QLabel {{
    color: {TEXT_SECONDARY};
    font-size: 11px;
}}
"""

BUBBLE_USER = f"""
QFrame {{
    background-color: #2b5278;
    color: #ffffff;
    border-radius: 12px;
    border-top-right-radius: 2px;
    padding: 8px 12px;
}}
"""

BUBBLE_ASSISTANT = f"""
QFrame {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
    border-radius: 12px;
    border-top-left-radius: 2px;
    border: 1px solid {BORDER_COLOR};
    padding: 8px 12px;
}}
"""

BUBBLE_SYSTEM = f"""
QFrame {{
    background-color: #222228;
    color: {TEXT_SECONDARY};
    border-radius: 8px;
    border: 1px dashed {BORDER_COLOR};
    padding: 6px 10px;
}}
"""

BUBBLE_TOOL = f"""
QFrame {{
    background-color: #1b261b;
    color: #a3c9a8;
    border-radius: 8px;
    border: 1px solid #2e4a30;
    padding: 6px 10px;
}}
"""
