"""Diagnostic script testing PySide6 Production Polish & UX Refinement offscreen."""

import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, ".")

import time
from PySide6.QtWidgets import QApplication
from app.gui.animations import PageTransitionManager
from app.gui.command_palette import CommandPaletteDialog
from app.gui.main_window import MainWindow
from app.gui.session import SessionRestoreManager
from app.gui.shortcuts import GlobalShortcutManager
from app.gui.views.settings_view import SettingsView


def main() -> None:
    print("==================================================")
    print("Testing PySide6 Production Polish & UX Refinement")
    print("==================================================")

    app = QApplication.instance() or QApplication(sys.argv)

    # 1. Command Palette
    palette = CommandPaletteDialog()
    assert len(palette.commands) >= 9
    print("PASS: CommandPaletteDialog instantiated successfully.")

    # 2. Session Restore Manager
    session = SessionRestoreManager()
    session.save_session("planner", "draft hello")
    assert session.restore_active_page() == "planner"
    assert session.restore_draft_text() == "draft hello"
    print("PASS: SessionRestoreManager state persistence verified.")

    # 3. Expanded SettingsView
    settings_view = SettingsView()
    assert settings_view.tabs.count() == 5
    print("PASS: Expanded 5-tab SettingsView verified.")

    # 4. MainWindow Polish Features
    main_window = MainWindow()
    assert main_window.shortcut_mgr is not None
    assert main_window.transition_mgr is not None
    print("PASS: MainWindow polish integrations verified.")

    print("\nALL PRODUCTION POLISH & UX REFINEMENT DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
