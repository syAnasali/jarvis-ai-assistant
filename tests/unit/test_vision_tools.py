"""Unit tests for built-in vision tools using MockVisionProvider."""

import pytest
from app.tools.builtin.vision import (
    CaptureScreenTool,
    ExplainErrorTool,
    ReadClipboardImageTool,
    AnalyzeRegionTool,
)
from app.tools.models import ToolResult
from app.vision.manager import VisionManager
from app.vision.providers import MockVisionProvider


@pytest.fixture
def mock_vision_manager():
    mgr = VisionManager(provider=MockVisionProvider())
    mgr.initialize()
    return mgr


def test_capture_screen_tool_execution(mock_vision_manager):
    tool = CaptureScreenTool(vision_manager=mock_vision_manager)
    res = tool.execute(prompt="Describe screen", target="fullscreen")
    assert isinstance(res, ToolResult)
    assert res.success is True
    assert "analysis" in res.output


def test_explain_error_tool_execution(mock_vision_manager):
    tool = ExplainErrorTool(vision_manager=mock_vision_manager)
    res = tool.execute(prompt="Read on-screen error dialog")
    assert isinstance(res, ToolResult)
    assert res.success is True
    assert "error_explanation" in res.output


def test_read_clipboard_image_tool_execution(mock_vision_manager):
    tool = ReadClipboardImageTool(vision_manager=mock_vision_manager)
    res = tool.execute()
    assert isinstance(res, ToolResult)


def test_analyze_region_tool_execution(mock_vision_manager):
    tool = AnalyzeRegionTool(vision_manager=mock_vision_manager)
    res = tool.execute(x=0, y=0, width=200, height=200, prompt="Analyze region")
    assert isinstance(res, ToolResult)
    assert res.success is True
