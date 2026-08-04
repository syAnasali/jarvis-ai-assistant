"""System Monitor Example Plugin for Jarvis Plugin SDK."""

import psutil
from typing import Any, Dict
from app.plugins.interfaces import Plugin
from app.plugins.sdk import JarvisPluginSDK
from app.tools.base import BaseTool
from app.tools.models import ToolPermission, ToolResult


class GetSystemTelemetryTool(BaseTool):
    """Tool to inspect CPU and RAM memory telemetry."""

    name = "get_system_telemetry"
    description = "Returns current CPU utilization and RAM memory usage percentages."
    permission_level = ToolPermission.SAFE

    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level.value,
            "parameters": self.parameters
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        cpu_pct = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        return ToolResult(
            tool_name=self.name,
            success=True,
            output={
                "cpu_percent": cpu_pct,
                "ram_total_gb": round(mem.total / (1024**3), 2),
                "ram_used_gb": round(mem.used / (1024**3), 2),
                "ram_percent": mem.percent
            }
        )


class SystemMonitorPlugin(Plugin):
    """Plugin implementation for System Monitor example."""

    def initialize(self, sdk: JarvisPluginSDK) -> None:
        self.sdk = sdk

    def shutdown(self) -> None:
        pass

    def register_tools(self, sdk: JarvisPluginSDK) -> None:
        sdk.tools.register(GetSystemTelemetryTool())
