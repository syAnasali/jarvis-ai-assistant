"""ThemeManager for Dark/Light QSS stylesheets, color tokens, and font hierarchy."""

from typing import Dict
from PySide6.QtWidgets import QApplication
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("gui_theme")


class ThemeManager:
    """Manages QSS stylesheets, color palettes, and theme toggling for PySide6 GUI."""

    DARK_STYSHEET = """
        QMainWindow, QDialog {
            background-color: #12141c;
            color: #e2e8f0;
            font-family: 'Segoe UI', 'Inter', sans-serif;
            font-size: 13px;
        }
        QWidget#sidebarWidget {
            background-color: #181b26;
            border-right: 1px solid #242838;
        }
        QWidget#toolbarWidget {
            background-color: #181b26;
            border-bottom: 1px solid #242838;
        }
        QWidget#statusBarWidget {
            background-color: #181b26;
            border-top: 1px solid #242838;
        }
        QPushButton#sidebarButton {
            background-color: transparent;
            color: #94a3b8;
            border: none;
            border-radius: 6px;
            padding: 8px 12px;
            text-align: left;
            font-weight: 500;
        }
        QPushButton#sidebarButton:hover {
            background-color: #242838;
            color: #ffffff;
        }
        QPushButton#sidebarButton:checked {
            background-color: #312e81;
            color: #818cf8;
            border-left: 3px solid #6366f1;
        }
        QFrame#cardFrame {
            background-color: #1a1d29;
            border: 1px solid #242838;
            border-radius: 8px;
        }
        QLabel {
            color: #e2e8f0;
        }
        QLabel#headerTitle {
            font-size: 18px;
            font-weight: 600;
            color: #ffffff;
        }
        QLabel#statusLabel {
            color: #94a3b8;
            font-size: 12px;
        }
    """

    LIGHT_STYLESHEET = """
        QMainWindow, QDialog {
            background-color: #f8fafc;
            color: #0f172a;
            font-family: 'Segoe UI', 'Inter', sans-serif;
            font-size: 13px;
        }
        QWidget#sidebarWidget {
            background-color: #ffffff;
            border-right: 1px solid #e2e8f0;
        }
        QWidget#toolbarWidget {
            background-color: #ffffff;
            border-bottom: 1px solid #e2e8f0;
        }
        QWidget#statusBarWidget {
            background-color: #ffffff;
            border-top: 1px solid #e2e8f0;
        }
        QPushButton#sidebarButton {
            background-color: transparent;
            color: #64748b;
            border: none;
            border-radius: 6px;
            padding: 8px 12px;
            text-align: left;
            font-weight: 500;
        }
        QPushButton#sidebarButton:hover {
            background-color: #f1f5f9;
            color: #0f172a;
        }
        QPushButton#sidebarButton:checked {
            background-color: #e0e7ff;
            color: #4338ca;
            border-left: 3px solid #4f46e5;
        }
        QFrame#cardFrame {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
        }
        QLabel {
            color: #0f172a;
        }
        QLabel#headerTitle {
            font-size: 18px;
            font-weight: 600;
            color: #0f172a;
        }
        QLabel#statusLabel {
            color: #64748b;
            font-size: 12px;
        }
    """

    @classmethod
    def get_stylesheet(cls, theme_name: str) -> str:
        """Returns QSS stylesheet string for 'dark' or 'light'."""
        if theme_name.lower() == "light":
            return cls.LIGHT_STYLESHEET
        return cls.DARK_STYSHEET

    @classmethod
    def apply_theme(cls, app: QApplication, theme_name: str) -> None:
        """Applies stylesheet to the target QApplication instance."""
        ss = cls.get_stylesheet(theme_name)
        app.setStyleSheet(ss)
        logger.info(f"Applied GUI theme '{theme_name}'.")
