"""Unit tests for built-in plugin tools."""

import pytest
from app.tools.builtin.plugin import (
    ListPluginsTool,
    EnablePluginTool,
    DisablePluginTool,
    ReloadPluginTool,
)
from app.tools.models import ToolResult


def test_list_plugins_tool():
    tool = ListPluginsTool()
    res = tool.execute()
    assert isinstance(res, ToolResult)
    assert res.success is True
    assert "total_plugins" in res.output


def test_reload_plugin_tool():
    tool_list = ListPluginsTool()
    res_list = tool_list.execute()
    mgr = tool_list._manager
    mgr.initialize()

    plugins = mgr.list_plugins()
    if plugins:
        p_id = plugins[0].manifest.id
        tool_reload = ReloadPluginTool(plugin_manager=mgr)
        res_reload = tool_reload.execute(plugin_id=p_id)
        assert res_reload.success is True
        assert res_reload.output["status"] == "ACTIVE"

    mgr.shutdown()
