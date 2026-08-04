"""Unit tests for PluginManager."""

import pytest
from app.plugins.manager import PluginManager
from app.plugins.models import PluginStatus


def test_plugin_manager_loads_examples():
    mgr = PluginManager(plugins_dir="plugins/examples")
    mgr.initialize()

    plugins = mgr.list_plugins()
    assert len(plugins) >= 1

    report = mgr.health_report()
    assert report["total_plugins"] >= 1
    mgr.shutdown()
