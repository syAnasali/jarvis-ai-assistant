"""Unit tests for built-in system tools."""

import platform
from app.tools.builtin.system import CurrentTimeTool, SystemInfoTool


def test_current_time_tool():
    """Verifies schema structure and output fields of the CurrentTimeTool."""
    tool = CurrentTimeTool()
    schema = tool.get_schema()
    
    assert schema["name"] == "get_current_time"
    assert "parameters" in schema
    
    res = tool.execute()
    assert "date" in res
    assert "time" in res
    assert "timezone" in res
    assert "iso_datetime" in res


def test_system_info_tool():
    """Verifies schema format, runtime checks, and absence of sensitive keys in SystemInfoTool."""
    tool = SystemInfoTool()
    schema = tool.get_schema()
    
    assert schema["name"] == "get_system_info"
    
    res = tool.execute()
    assert res["system"] == platform.system()
    assert "release" in res
    assert "version" in res
    assert "machine" in res
    assert "processor" in res
    assert "python_version" in res
    
    # Check sensitive data keys are absent
    sensitive_keys = [
        "env", "user", "username", "password", "token", "ip",
        "address", "network", "files", "processes"
    ]
    for key in res:
        for sk in sensitive_keys:
            assert sk not in key.lower()
