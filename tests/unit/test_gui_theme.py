"""Unit tests for ThemeManager."""

import pytest
from app.gui.theme import ThemeManager


def test_theme_manager_stylesheets():
    dark_ss = ThemeManager.get_stylesheet("dark")
    light_ss = ThemeManager.get_stylesheet("light")

    assert "#12141c" in dark_ss
    assert "#f8fafc" in light_ss
