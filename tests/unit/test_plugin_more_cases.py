"""Additional comprehensive unit tests for Plugin Architecture."""

import pytest
from app.plugins.models import (
    PluginManifest,
    PluginStatus,
    PluginPermission,
    PluginInfo,
    PluginEvent,
)
from app.plugins.manifest import PluginManifestParser
from app.plugins.sandbox import PluginPermissionSandbox
from app.plugins.events import PluginEventBus
from app.plugins.manager import PluginManager
from app.tools.builtin.plugin import (
    ListPluginsTool,
    EnablePluginTool,
    DisablePluginTool,
    ReloadPluginTool,
)


def test_plugin_permission_enum_values():
    assert PluginPermission.FILESYSTEM.value == "filesystem"
    assert PluginPermission.DESKTOP.value == "desktop"
    assert PluginPermission.VOICE.value == "voice"
    assert PluginPermission.VISION.value == "vision"


def test_plugin_event_creation():
    ev = PluginEvent(event_type="test_type", payload={"key": "val"}, source_plugin_id="my_plugin")
    assert ev.event_type == "test_type"
    assert ev.source_plugin_id == "my_plugin"
    assert ev.payload["key"] == "val"


def test_disable_and_enable_plugin_tools():
    mgr = PluginManager(plugins_dir="plugins/examples")
    mgr.initialize()

    plugins = mgr.list_plugins()
    if plugins:
        p_id = plugins[0].manifest.id
        t_disable = DisablePluginTool(plugin_manager=mgr)
        res_dis = t_disable.execute(plugin_id=p_id)
        assert res_dis.success is True

        t_enable = EnablePluginTool(plugin_manager=mgr)
        res_en = t_enable.execute(plugin_id=p_id)
        assert res_en.success is True

    mgr.shutdown()


def test_list_plugins_tool_schema():
    tool = ListPluginsTool()
    schema = tool.get_schema()
    assert schema["name"] == "list_plugins"


def test_reload_plugin_tool_schema():
    tool = ReloadPluginTool()
    schema = tool.get_schema()
    assert schema["name"] == "reload_plugin"
    assert "plugin_id" in schema["parameters"]["properties"]
