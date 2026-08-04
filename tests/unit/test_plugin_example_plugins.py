"""Unit tests for example plugins (hello_world, calculator, system_monitor, weather_mock)."""

import pytest
from app.plugins.manager import PluginManager


def test_example_plugins_execution():
    mgr = PluginManager(plugins_dir="plugins/examples")
    mgr.initialize()

    plugins = mgr.list_plugins()
    ids = [p.manifest.id for p in plugins]

    assert "hello_world" in ids
    assert "calculator" in ids
    assert "system_monitor" in ids
    assert "weather_mock" in ids

    mgr.shutdown()
