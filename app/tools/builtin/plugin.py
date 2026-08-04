"""Built-in Plugin tools for listing, enabling, disabling, and hot-reloading plugins."""

from typing import Any, Dict, Optional
from app.plugins.manager import PluginManager
from app.tools.base import BaseTool
from app.tools.models import ToolPermission, ToolResult


class ListPluginsTool(BaseTool):
    """Tool to list installed plugins, versions, status, and declared permissions."""

    name = "list_plugins"
    description = "Lists all installed plugins, their status, versions, and declared permissions."
    permission_level = ToolPermission.SAFE

    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }

    def __init__(self, plugin_manager: Optional[PluginManager] = None) -> None:
        self._manager = plugin_manager or PluginManager()

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level.value,
            "parameters": self.parameters
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            report = self._manager.health_report()
            return ToolResult(tool_name=self.name, success=True, output=report)
        except Exception as e:
            return ToolResult(tool_name=self.name, success=False, output={}, error=f"List plugins tool failed: {e}")


class EnablePluginTool(BaseTool):
    """Tool to enable an installed plugin."""

    name = "enable_plugin"
    description = "Enables an installed plugin by plugin_id."
    permission_level = ToolPermission.SAFE

    parameters = {
        "type": "object",
        "properties": {
            "plugin_id": {"type": "string", "description": "Unique plugin_id identifier."}
        },
        "required": ["plugin_id"]
    }

    def __init__(self, plugin_manager: Optional[PluginManager] = None) -> None:
        self._manager = plugin_manager or PluginManager()

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level.value,
            "parameters": self.parameters
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        plugin_id = kwargs.get("plugin_id", "")
        if not plugin_id:
            return ToolResult(tool_name=self.name, success=False, output={}, error="plugin_id must not be empty.")

        try:
            self._manager.enable_plugin(plugin_id)
            return ToolResult(tool_name=self.name, success=True, output={"plugin_id": plugin_id, "status": "enabled"})
        except Exception as e:
            return ToolResult(tool_name=self.name, success=False, output={}, error=f"Enable plugin failed: {e}")


class DisablePluginTool(BaseTool):
    """Tool to disable an active plugin."""

    name = "disable_plugin"
    description = "Disables an active plugin by plugin_id."
    permission_level = ToolPermission.SAFE

    parameters = {
        "type": "object",
        "properties": {
            "plugin_id": {"type": "string", "description": "Unique plugin_id identifier."}
        },
        "required": ["plugin_id"]
    }

    def __init__(self, plugin_manager: Optional[PluginManager] = None) -> None:
        self._manager = plugin_manager or PluginManager()

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level.value,
            "parameters": self.parameters
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        plugin_id = kwargs.get("plugin_id", "")
        if not plugin_id:
            return ToolResult(tool_name=self.name, success=False, output={}, error="plugin_id must not be empty.")

        try:
            self._manager.disable_plugin(plugin_id)
            return ToolResult(tool_name=self.name, success=True, output={"plugin_id": plugin_id, "status": "disabled"})
        except Exception as e:
            return ToolResult(tool_name=self.name, success=False, output={}, error=f"Disable plugin failed: {e}")


class ReloadPluginTool(BaseTool):
    """Tool to hot-reload a plugin without restarting Jarvis."""

    name = "reload_plugin"
    description = "Hot-reloads an installed plugin by plugin_id without restarting Jarvis."
    permission_level = ToolPermission.SAFE

    parameters = {
        "type": "object",
        "properties": {
            "plugin_id": {"type": "string", "description": "Unique plugin_id identifier."}
        },
        "required": ["plugin_id"]
    }

    def __init__(self, plugin_manager: Optional[PluginManager] = None) -> None:
        self._manager = plugin_manager or PluginManager()

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level.value,
            "parameters": self.parameters
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        plugin_id = kwargs.get("plugin_id", "")
        if not plugin_id:
            return ToolResult(tool_name=self.name, success=False, output={}, error="plugin_id must not be empty.")

        try:
            info = self._manager.reload_plugin(plugin_id)
            return ToolResult(
                tool_name=self.name,
                success=True,
                output={
                    "plugin_id": plugin_id,
                    "status": info.status.value,
                    "version": info.manifest.version
                }
            )
        except Exception as e:
            return ToolResult(tool_name=self.name, success=False, output={}, error=f"Reload plugin failed: {e}")
