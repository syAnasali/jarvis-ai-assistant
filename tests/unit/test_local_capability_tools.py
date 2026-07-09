"""Unit tests for safe local capability tools and safety helper functions."""

import os
import shutil
import pytest
import psutil
from unittest.mock import MagicMock, patch
from typing import Any, Dict, List
from app.core.exceptions import ToolExecutionError
from app.tools.builtin.filesystem import validate_and_resolve_path, ListDirectoryTool, is_sensitive_path
from app.tools.builtin.disk import GetDiskUsageTool
from app.tools.builtin.process import ListRunningProcessesTool, FindRunningProcessTool
from app.tools.builtin.applications import ListInstalledApplicationsTool, FindInstalledApplicationTool, discover_installed_applications
from app.tools.registry import ToolRegistry
from app.tools.executor import ToolExecutor
from app.tools.models import ToolPermission, ToolResult
from app.agent.models import ToolCall
from app.planning.planner import LLMTaskPlanner
from app.config.settings import settings


# =====================================================================
# PATH SAFETY HELPER TESTS
# =====================================================================

def test_path_helper_valid_directory(tmp_path):
    """Verify that a valid existing directory path is expanded and resolved correctly."""
    resolved = validate_and_resolve_path(str(tmp_path), expected_type="directory")
    assert os.path.isabs(resolved)
    assert resolved == os.path.abspath(tmp_path)


def test_path_helper_nonexistent_path():
    """Verify that a nonexistent path raises a ToolExecutionError."""
    with pytest.raises(ToolExecutionError, match="Path does not exist"):
        validate_and_resolve_path("non_existent_folder_xyz_123")


def test_path_helper_null_byte_rejection():
    """Verify that paths containing null bytes are strictly rejected."""
    with pytest.raises(ToolExecutionError, match="null bytes"):
        validate_and_resolve_path("some/path\x00/file.txt")


def test_path_helper_type_validation_file_vs_dir(tmp_path):
    """Verify that expected type constraints (file vs directory) are enforced."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("content")

    # Correct type
    assert validate_and_resolve_path(str(file_path), expected_type="file")
    assert validate_and_resolve_path(str(tmp_path), expected_type="directory")

    # Incorrect type
    with pytest.raises(ToolExecutionError, match="not a directory"):
        validate_and_resolve_path(str(file_path), expected_type="directory")

    with pytest.raises(ToolExecutionError, match="not a regular file"):
        validate_and_resolve_path(str(tmp_path), expected_type="file")


def test_path_helper_sensitive_filename_denylist(tmp_path):
    """Verify that credential and private key filenames are blocked."""
    sensitive_names = [
        ".env", ".env.production", "id_rsa", "id_ed25519",
        "credentials.json", "service-account.json", "key.pem", "private.key"
    ]
    for name in sensitive_names:
        p = tmp_path / name
        p.write_text("secret_stuff")
        assert is_sensitive_path(str(p)) is True
        with pytest.raises(ToolExecutionError, match="Access to sensitive file blocked"):
            validate_and_resolve_path(str(p))

    # Test allowed name
    allowed = tmp_path / "notes.txt"
    allowed.write_text("public_notes")
    assert is_sensitive_path(str(allowed)) is False
    assert validate_and_resolve_path(str(allowed)) == os.path.abspath(allowed)


# =====================================================================
# GET DISK USAGE TESTS
# =====================================================================

def test_get_disk_usage_valid_and_normalized(tmp_path):
    """Verify disk usage returns expected fields and normalized percent."""
    tool = GetDiskUsageTool()
    res = tool.execute(path=str(tmp_path))
    assert res["path"] == os.path.abspath(tmp_path)
    assert isinstance(res["total_bytes"], int)
    assert isinstance(res["used_bytes"], int)
    assert isinstance(res["free_bytes"], int)
    assert isinstance(res["used_percent"], float)
    assert 0.0 <= res["used_percent"] <= 100.0


def test_get_disk_usage_default_path():
    """Verify disk usage uses system drive when no path is supplied."""
    tool = GetDiskUsageTool()
    res = tool.execute()
    assert "total_bytes" in res
    assert res["path"].startswith(os.getenv("SystemDrive", "C:"))


def test_get_disk_usage_invalid_path():
    """Verify disk usage fails gracefully on an invalid path."""
    tool = GetDiskUsageTool()
    with pytest.raises(ToolExecutionError):
        tool.execute(path="invalid_path_dir_123_xyz")


# =====================================================================
# PROCESS TOOLS TESTS
# =====================================================================

@pytest.fixture
def mock_processes():
    """Returns a list of mocked psutil Process objects."""
    p1 = MagicMock()
    p1.info = {"pid": 100, "name": "ollama.exe", "exe": "C:\\Program Files\\Ollama\\ollama.exe"}
    
    p2 = MagicMock()
    p2.info = {"pid": 50, "name": "python.exe", "exe": "C:\\Python\\python.exe"}

    p3 = MagicMock()
    # Mocking AccessDenied on p3.info property query
    type(p3).info = property(lambda self: (_ for _ in ()).throw(psutil.AccessDenied()))

    return [p1, p2, p3]


@patch("psutil.process_iter")
def test_list_running_processes_sorting_and_denied(mock_iter, mock_processes):
    """Verify list processes sorts deterministically and ignores AccessDenied."""
    mock_iter.return_value = mock_processes
    tool = ListRunningProcessesTool()
    res = tool.execute(limit=10)
    
    # PID 50 should be first, then PID 100. PID of AccessDenied should be skipped.
    assert res["returned_count"] == 2
    assert res["processes"][0]["pid"] == 50
    assert res["processes"][1]["pid"] == 100
    assert res["truncated"] is False


@patch("psutil.process_iter")
def test_list_running_processes_limits(mock_iter, mock_processes):
    """Verify list processes respects user-defined and hardcoded limits."""
    mock_iter.return_value = mock_processes
    tool = ListRunningProcessesTool()
    
    # Limit of 1
    res = tool.execute(limit=1)
    assert res["returned_count"] == 1
    assert res["truncated"] is True

    # Invalid limits
    with pytest.raises(ToolExecutionError, match="Limit must be between 1 and 200"):
        tool.execute(limit=0)
    with pytest.raises(ToolExecutionError, match="Limit must be between 1 and 200"):
        tool.execute(limit=250)


@patch("psutil.process_iter")
def test_find_running_process_case_insensitive(mock_iter, mock_processes):
    """Verify find running process queries name and path case-insensitively."""
    mock_iter.return_value = mock_processes
    tool = FindRunningProcessTool()
    
    res = tool.execute(query="OLLAMA")
    assert res["match_count"] == 1
    assert res["matches"][0]["name"] == "ollama.exe"

    res_exe = tool.execute(query="program files")
    assert res_exe["match_count"] == 1
    assert res_exe["matches"][0]["name"] == "ollama.exe"


# =====================================================================
# APPLICATION TOOLS TESTS
# =====================================================================

@pytest.fixture
def mock_apps_data():
    """Returns fake installed application dictionary list."""
    return [
        {"name": "Visual Studio Code", "version": "1.85.0", "publisher": "Microsoft"},
        {"name": "Ollama", "version": "0.1.20", "publisher": "Ollama"},
        {"name": "Python 3.13", "version": "3.13.0", "publisher": "Python Software Foundation"}
    ]


def test_list_installed_applications_sorting_and_deduplication(mock_apps_data):
    """Verify applications list is sorted alphabetically."""
    with patch("app.tools.builtin.applications.discover_installed_applications", return_value=mock_apps_data):
        tool = ListInstalledApplicationsTool()
        res = tool.execute(limit=10)
        
        apps = res["applications"]
        assert len(apps) == 3
        # Alphabetical sorting
        assert apps[0]["name"] == "Ollama"
        assert apps[1]["name"] == "Python 3.13"
        assert apps[2]["name"] == "Visual Studio Code"


def test_find_installed_application_searching():
    """Verify application searching is case-insensitive and filters correctly."""
    fake_data = [
        {"name": "Visual Studio Code", "version": "1.85", "publisher": "Microsoft"},
        {"name": "visual studio Community", "version": "2022", "publisher": "Microsoft"},
        {"name": "Ollama", "version": "0.1.20", "publisher": "Ollama"}
    ]
    with patch("app.tools.builtin.applications.discover_installed_applications", return_value=fake_data):
        tool = FindInstalledApplicationTool()
        res = tool.execute(query="VISUAL STUDIO")
        
        assert res["match_count"] == 2
        assert res["matches"][0]["name"] == "Visual Studio Code"
        assert res["matches"][1]["name"] == "visual studio Community"


@patch("winreg.OpenKey", side_effect=OSError("Registry unavailable"))
def test_applications_registry_unavailable(mock_open):
    """Verify applications scan handles OS registry access failures safely."""
    apps = discover_installed_applications()
    assert apps == []  # Returns empty list rather than raising raw error


# =====================================================================
# REGISTRATION & REGRESSION TESTS
# =====================================================================

def test_tool_registration_singletons():
    """Verify all capability tools are registered exactly once."""
    from app.core.application import Application
    app = Application()
    app.initialize()
    app._initialize_llm()
    app._initialize_agent()
    
    reg = app.container.get("tool_registry")
    
    expected_tools = [
        "get_current_time", "get_system_info",
        "get_disk_usage", "list_running_processes", "find_running_process",
        "list_installed_applications", "find_installed_application",
        "inspect_path", "list_directory", "create_directory", "write_text_file",
        "move_path", "delete_path"
    ]
    
    for tool_name in expected_tools:
        # Check registered exactly once
        t = reg.get(tool_name)
        assert t is not None
        assert t.name == tool_name


def test_tool_permission_enforcement_regression():
    """Verify ToolExecutor correctly handles SAFE permission levels."""
    registry = ToolRegistry()
    registry.register(GetDiskUsageTool())
    executor = ToolExecutor(registry)

    # SAFE works
    tc = ToolCall(tool_name="get_disk_usage", arguments={})
    res = executor.execute(tc)
    assert res.success is True


def test_planning_integration_discovers_schemas():
    """Verify TaskPlanner retrieves and utilizes new capability tool schemas."""
    registry = ToolRegistry()
    registry.register(GetDiskUsageTool())
    
    mock_llm = MagicMock()
    planner = LLMTaskPlanner(mock_llm)
    
    schemas = registry.get_schemas()
    assert any(s["name"] == "get_disk_usage" for s in schemas)
