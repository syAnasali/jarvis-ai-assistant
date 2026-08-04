"""Unit tests for GuiSettingsManager."""

import pytest
from app.gui.settings import GuiSettingsManager


def test_gui_settings_manager():
    mgr = GuiSettingsManager(organization="TestOrg", application="TestApp")

    mgr.set_theme("light")
    assert mgr.get_theme() == "light"

    mgr.set_theme("dark")
    assert mgr.get_theme() == "dark"

    mgr.set_sidebar_collapsed(True)
    assert mgr.is_sidebar_collapsed() is True

    mgr.set_active_page("planner")
    assert mgr.get_active_page() == "planner"
