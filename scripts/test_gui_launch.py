"""Diagnostic script testing PySide6 Desktop GUI MainWindow launch, navigation, and themes."""

import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, ".")

from PySide6.QtWidgets import QApplication
from app.gui.main_window import MainWindow
from app.gui.theme import ThemeManager


def main() -> None:
    print("==================================================")
    print("Testing PySide6 Desktop GUI Foundation Diagnostics")
    print("==================================================")

    app = QApplication.instance() or QApplication(sys.argv)

    window = MainWindow()
    print("PASS: MainWindow instantiated successfully.")

    # Test page navigation across 9 pages
    pages = ["chat", "planner", "memory", "knowledge", "vision", "voice", "plugins", "diagnostics", "settings"]
    for pid in pages:
        res = window.nav_mgr.navigate_to(pid)
        assert res is True
        print(f" - Navigated to page: '{pid}' (Active: '{window.nav_mgr.get_active_page()}')")

    # Test theme toggle
    ThemeManager.apply_theme(app, "dark")
    print("PASS: Dark theme applied.")

    ThemeManager.apply_theme(app, "light")
    print("PASS: Light theme applied.")

    print("\nALL DESKTOP GUI DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
