"""Built-in Observability tools for health reporting, live telemetry inspection, and file exports."""

from typing import Any, Dict, Optional
from app.observability.manager import ObservabilityManager
from app.tools.base import BaseTool
from app.tools.models import ToolPermission, ToolResult


class GetHealthReportTool(BaseTool):
    """Tool to inspect overall system health report and subsystem statuses."""

    name = "get_health_report"
    description = "Returns comprehensive system health report and subsystem statuses."
    permission_level = ToolPermission.SAFE

    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }

    def __init__(self, manager: Optional[ObservabilityManager] = None) -> None:
        self._manager = manager or ObservabilityManager()

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level.value,
            "parameters": self.parameters
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            report = self._manager.dashboard.health_report()
            return ToolResult(tool_name=self.name, success=True, output=report)
        except Exception as e:
            return ToolResult(tool_name=self.name, success=False, output={}, error=f"Get health report tool failed: {e}")


class GetRuntimeTelemetryTool(BaseTool):
    """Tool to inspect live aggregated runtime metrics across subsystems."""

    name = "get_runtime_telemetry"
    description = "Returns live metrics counters and latencies across LLM, Agent, Memory, Knowledge, Planner, Voice, Vision, and Plugin runtimes."
    permission_level = ToolPermission.SAFE

    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }

    def __init__(self, manager: Optional[ObservabilityManager] = None) -> None:
        self._manager = manager or ObservabilityManager()

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level.value,
            "parameters": self.parameters
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            summary = self._manager.dashboard.system_metrics()
            return ToolResult(tool_name=self.name, success=True, output=summary)
        except Exception as e:
            return ToolResult(tool_name=self.name, success=False, output={}, error=f"Get runtime telemetry tool failed: {e}")


class ExportTelemetryTool(BaseTool):
    """Tool to export telemetry diagnostics to JSON, CSV, or Markdown format."""

    name = "export_telemetry"
    description = "Exports system telemetry metrics, tracing spans, and timeline events to JSON, CSV, or Markdown file."
    permission_level = ToolPermission.SAFE

    parameters = {
        "type": "object",
        "properties": {
            "format": {"type": "string", "description": "Export format ('json', 'csv', or 'markdown')", "default": "json"},
            "destination_path": {"type": "string", "description": "Destination file path", "default": "data/telemetry_export.json"}
        },
        "required": ["format", "destination_path"]
    }

    def __init__(self, manager: Optional[ObservabilityManager] = None) -> None:
        self._manager = manager or ObservabilityManager()

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level.value,
            "parameters": self.parameters
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        fmt = kwargs.get("format", "json")
        path = kwargs.get("destination_path", "data/telemetry_export.json")
        try:
            res_path = self._manager.export(fmt, path)
            return ToolResult(
                tool_name=self.name,
                success=True,
                output={"format": fmt, "file_path": res_path}
            )
        except Exception as e:
            return ToolResult(tool_name=self.name, success=False, output={}, error=f"Export telemetry tool failed: {e}")
