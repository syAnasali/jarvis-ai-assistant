"""Unit tests for CommandPaletteDialog."""

import os
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.command_palette import CommandPaletteDialog


def test_command_palette_filtering():
    app = QApplication.instance() or QApplication([])

    palette = CommandPaletteDialog()
    palette._filter_commands("chat")

    assert palette.list_commands.count() == 1
    assert "Chat" in palette.list_commands.item(0).text()
