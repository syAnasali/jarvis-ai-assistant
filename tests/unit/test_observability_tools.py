"""Unit tests for built-in observability tools."""

import pytest
from app.tools.builtin.observability import (
    GetHealthReportTool,
    GetRuntimeTelemetryTool,
    ExportTelemetryTool,
)
from app.tools.models import ToolResult


def test_get_health_report_tool():
    tool = GetHealthReportTool()
    res = tool.execute()
    assert isinstance(res, ToolResult)
    assert res.success is True
    assert "overall_status" in res.output


def test_get_runtime_telemetry_tool():
    tool = GetRuntimeTelemetryTool()
    res = tool.execute()
    assert isinstance(res, ToolResult)
    assert res.success is True


def test_export_telemetry_tool(tmp_path):
    tool = ExportTelemetryTool()
    out_file = str(tmp_path / "telemetry.json")
    res = tool.execute(format="json", destination_path=out_file)
    assert isinstance(res, ToolResult)
    assert res.success is True
    assert res.output["format"] == "json"
