"""Unit tests for Windows application discovery, resolution, and launching."""

import os
import sys
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.services.applications.models import InstalledApplication
from app.services.applications.resolver import ApplicationResolver, ApplicationResolution, ALIASES, BUILT_IN_APPLICATIONS
from app.services.applications.launcher import ApplicationLauncher
from app.tools.builtin.applications import ResolveApplicationTool, LaunchApplicationTool
from app.tools.models import ToolPermission
from app.agent.models import ToolCall, AgentRequest, AgentResponse
from app.agent.runner import AgentRunner, AgentRunResult
from app.agent.metrics import AgentExecutionMetrics
from app.ai.manager import LLMManager
from app.ai.parser import ResponseParser
from app.ai.models import GenerationResult, GenerationMetrics
from app.approval.models import PendingAction, PendingActionStatus
from app.approval.manager import ApprovalManager
from app.approval.repository import SQLiteApprovalRepository
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry
from app.planning.models import TaskPlan, PlanStep, StepType, StepStatus, PlanStatus
from app.planning.executor import TaskExecutor
from app.planning.validator import PlanValidator
from app.core.exceptions import ToolExecutionError


# ----------------------------------------------------
# 1. InstalledApplication Domain Model Tests
# ----------------------------------------------------

def test_installed_application_immutability():
    app = InstalledApplication(
        name="Test Editor",
        executable_path="C:\\Windows\\System32\\notepad.exe",
        version="1.0.0",
        publisher="Microsoft",
        source="Start Menu",
        metadata={"custom": "info"}
    )
    
    assert app.name == "Test Editor"
    assert app.executable_path == "C:\\Windows\\System32\\notepad.exe"
    assert app.version == "1.0.0"
    assert app.publisher == "Microsoft"
    assert app.source == "Start Menu"
    assert app.application_id.startswith("app_test_editor_")
    assert app.metadata == {"custom": "info"}
    
    # Try to modify fields (should raise error since frozen=True)
    with pytest.raises(Exception):
        app.name = "New Name"
        
    # Metadata should be read-only and raise TypeError if modified
    with pytest.raises(TypeError):
        app.metadata["custom"] = "modified"


def test_installed_application_deterministic_id():
    app1 = InstalledApplication("Notepad", "C:\\Windows\\System32\\notepad.exe")
    app2 = InstalledApplication("Notepad", "C:\\Windows\\System32\\notepad.exe")
    app3 = InstalledApplication("Notepad", "C:\\Windows\\notepad.exe")
    
    assert app1.application_id == app2.application_id
    assert app1.application_id != app3.application_id
    assert not app1.application_id.startswith("uuid")  # must be deterministic hash-based


def test_installed_application_normalized_paths():
    app = InstalledApplication("App", "  \"C:\\Path\\To\\Exe.exe\"  ")
    # Path should be stripped and normalized
    assert app.executable_path == os.path.normpath("C:\\Path\\To\\Exe.exe")


# ----------------------------------------------------
# 2. ApplicationResolver Tests
# ----------------------------------------------------

@pytest.fixture
def mock_resolver():
    resolver = ApplicationResolver()
    # Populate cache with mock applications
    resolver._cached_apps = {
        "c:\\windows\\system32\\notepad.exe": InstalledApplication(
            name="Notepad",
            executable_path="C:\\Windows\\System32\\notepad.exe",
            version="10.0",
            publisher="Microsoft Corporation",
            source="Built-in",
            metadata={"aliases": ["notepad"]}
        ),
        "c:\\program files\\microsoft vs code\\code.exe": InstalledApplication(
            name="Visual Studio Code",
            executable_path="C:\\Program Files\\Microsoft VS Code\\code.exe",
            version="1.85",
            publisher="Microsoft Corporation",
            source="Start Menu",
            metadata={"aliases": ["vscode", "vs code"]}
        ),
        "c:\\program files\\visual studio\\vs.exe": InstalledApplication(
            name="Visual Studio",
            executable_path="C:\\Program Files\\Visual Studio\\vs.exe",
            version="17.8",
            publisher="Microsoft Corporation",
            source="App Paths"
        ),
        "c:\\windows\\system32\\calc.exe": InstalledApplication(
            name="Calculator",
            executable_path="C:\\Windows\\System32\\calc.exe",
            version="10.0",
            publisher="Microsoft Corporation",
            source="Built-in",
            metadata={"aliases": ["calc"]}
        )
    }
    return resolver


def test_resolver_exact_match(mock_resolver):
    res = mock_resolver.resolve("Notepad")
    assert res.status == "RESOLVED"
    assert res.match_type == "exact_name"
    assert res.application.name == "Notepad"


def test_resolver_alias_match(mock_resolver):
    res = mock_resolver.resolve("vscode")
    assert res.status == "RESOLVED"
    assert res.match_type == "exact_alias"
    assert res.application.name == "Visual Studio Code"


def test_resolver_prefix_match(mock_resolver):
    res = mock_resolver.resolve("Visual Studio C")
    assert res.status == "RESOLVED"
    assert res.match_type == "prefix"
    assert res.application.name == "Visual Studio Code"


def test_resolver_substring_match(mock_resolver):
    res = mock_resolver.resolve("Studio")
    # Both "Visual Studio Code" and "Visual Studio" contain "Studio", so prefix/substring yields ambiguity!
    assert res.status == "AMBIGUOUS"
    assert len(res.candidates) == 2
    assert res.candidates[0].name == "Visual Studio"  # Alphabetical ordering: Visual Studio before Visual Studio Code
    assert res.candidates[1].name == "Visual Studio Code"


def test_resolver_case_insensitive_matching(mock_resolver):
    res = mock_resolver.resolve("nOtEpAd")
    assert res.status == "RESOLVED"
    assert res.application.name == "Notepad"


def test_resolver_not_found(mock_resolver):
    res = mock_resolver.resolve("NonExistentAppName")
    assert res.status == "NOT_FOUND"
    assert res.application is None
    assert len(res.candidates) == 0


def test_resolver_candidate_bounds(mock_resolver):
    # Set max candidates setting to 1
    with patch("app.config.settings.settings.application_resolution_max_candidates", 1):
        res = mock_resolver.resolve("Studio")
        assert res.status == "AMBIGUOUS"
        assert len(res.candidates) == 1
        assert res.candidates[0].name == "Visual Studio"


# ----------------------------------------------------
# 3. ApplicationLauncher Tests
# ----------------------------------------------------

def test_launcher_valid_executable(tmp_path):
    exe_file = tmp_path / "valid.exe"
    exe_file.touch()
    
    app = InstalledApplication("Valid", str(exe_file))
    launcher = ApplicationLauncher()
    
    # Mock subprocess.Popen
    mock_process = MagicMock()
    mock_process.pid = 1234
    
    with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
        res = launcher.launch(app)
        assert res["launched"] is True
        assert res["pid"] == 1234
        assert res["application_id"] == app.application_id
        
        # Verify shell=True was NEVER used
        _, kwargs = mock_popen.call_args
        assert kwargs.get("shell") is not True


def test_launcher_missing_executable():
    app = InstalledApplication("Missing", "C:\\nonexistent.exe")
    launcher = ApplicationLauncher()
    with pytest.raises(ToolExecutionError, match="executable not found"):
        launcher.launch(app)


def test_launcher_directory_rejected(tmp_path):
    app = InstalledApplication("Folder", str(tmp_path))
    launcher = ApplicationLauncher()
    with pytest.raises(ToolExecutionError, match="target is not a file"):
        launcher.launch(app)


def test_launcher_unsupported_extensions(tmp_path):
    script_file = tmp_path / "script.bat"
    script_file.touch()
    
    app = InstalledApplication("Script", str(script_file))
    launcher = ApplicationLauncher()
    with pytest.raises(ToolExecutionError, match="blocked execution"):
        launcher.launch(app)


# ----------------------------------------------------
# 4. resolve_application Tool Tests
# ----------------------------------------------------

def test_resolve_application_tool(mock_resolver):
    tool = ResolveApplicationTool()
    assert tool.permission_level == ToolPermission.SAFE
    
    # Resolve successful
    with patch("app.services.applications.resolver.ApplicationResolver", return_value=mock_resolver):
        res = tool.execute(query="Notepad")
        assert res["status"] == "RESOLVED"
        assert "application" in res
        assert "executable_path" not in res["application"]  # Executable path hidden from LLM
        assert res["application"]["application_id"] is not None

        # Resolve ambiguous
        res_amb = tool.execute(query="Studio")
        assert res_amb["status"] == "AMBIGUOUS"
        assert len(res_amb["candidates"]) == 2
        for cand in res_amb["candidates"]:
            assert "executable_path" not in cand  # path hidden


# ----------------------------------------------------
# 5. launch_application Tool Tests
# ----------------------------------------------------

def test_launch_application_tool(mock_resolver, tmp_path):
    tool = LaunchApplicationTool()
    assert tool.permission_level == ToolPermission.CONFIRMATION
    
    exe_file = tmp_path / "notepad.exe"
    exe_file.touch()
    
    # Update mock app path to point to mock temp file
    app_obj = mock_resolver._cached_apps["c:\\windows\\system32\\notepad.exe"]
    object.__setattr__(app_obj, "executable_path", str(exe_file))
    
    mock_process = MagicMock()
    mock_process.pid = 9999
    
    with patch("app.services.applications.resolver.ApplicationResolver", return_value=mock_resolver), \
         patch("subprocess.Popen", return_value=mock_process):
        res = tool.execute(application_id=app_obj.application_id)
        assert res["launched"] is True
        assert res["pid"] == 9999


# ----------------------------------------------------
# 6. Approval Integration Tests
# ----------------------------------------------------

def test_launch_approval_lifecycle(mock_resolver, tmp_path):
    registry = ToolRegistry()
    launch_tool = LaunchApplicationTool()
    registry.register(launch_tool)
    
    repo = SQLiteApprovalRepository(database_path=tmp_path / "db.sqlite")
    manager = ApprovalManager(repo)
    executor = ToolExecutor(registry, approval_manager=manager)
    
    exe_file = tmp_path / "notepad.exe"
    exe_file.touch()
    
    app_obj = mock_resolver._cached_apps["c:\\windows\\system32\\notepad.exe"]
    object.__setattr__(app_obj, "executable_path", str(exe_file))
    
    # 1. Try execution (should yield confirmation required)
    tc = ToolCall(tool_name="launch_application", arguments={"application_id": app_obj.application_id})
    with patch("app.services.applications.resolver.ApplicationResolver", return_value=mock_resolver):
        res = executor.execute(tc)
        
    assert res.success is False
    assert res.metadata.get("confirmation_required") is True
    action_id = res.metadata.get("pending_action_id")
    assert action_id is not None
    
    # 2. Approved launch executes once
    manager.approve(action_id)
    
    mock_process = MagicMock()
    mock_process.pid = 1111
    
    with patch("app.services.applications.resolver.ApplicationResolver", return_value=mock_resolver), \
         patch("subprocess.Popen", return_value=mock_process):
        res_exec = executor.execute(tc, approval_action_id=action_id)
        
    assert res_exec.success is True
    assert res_exec.output["pid"] == 1111

    # 3. Replay blocked
    with patch("app.services.applications.resolver.ApplicationResolver", return_value=mock_resolver):
        res_replay = executor.execute(tc, approval_action_id=action_id)
    assert res_replay.success is False
    assert "Replay blocked" in res_replay.error


# ----------------------------------------------------
# 7. AgentRunner / TaskExecutor Integration Tests
# ----------------------------------------------------

def test_task_executor_planned_launch_approval(mock_resolver, tmp_path):
    # Setup ToolRegistry with launch tool
    registry = ToolRegistry()
    launch_tool = LaunchApplicationTool()
    registry.register(launch_tool)
    
    repo = SQLiteApprovalRepository(database_path=tmp_path / "db.sqlite")
    manager = ApprovalManager(repo)
    executor = ToolExecutor(registry, approval_manager=manager)
    
    exe_file = tmp_path / "notepad.exe"
    exe_file.touch()
    
    app_obj = mock_resolver._cached_apps["c:\\windows\\system32\\notepad.exe"]
    object.__setattr__(app_obj, "executable_path", str(exe_file))

    # Setup Plan: launch step -> synthesis step
    step1 = PlanStep("step_1", 1, "Launch app", StepType.TOOL, "launch_application", {"application_id": app_obj.application_id})
    step2 = PlanStep("step_2", 2, "Synthesis step", StepType.SYNTHESIS)
    
    plan = TaskPlan("plan_launch", "Launch editor", [step1, step2])
    
    mock_llm = MagicMock(spec=LLMManager)
    task_executor = TaskExecutor(mock_llm, registry, executor, PlanValidator(registry))
    
    # Run plan execution (suspends at step 1)
    with patch("app.services.applications.resolver.ApplicationResolver", return_value=mock_resolver):
        result = task_executor.execute(plan, "Launch editor request")
        
    assert result.plan_status == PlanStatus.WAITING_APPROVAL
    assert step1.status == StepStatus.WAITING_APPROVAL
    assert step2.status == StepStatus.PENDING
    
    pending_action_id = result.metadata.get("pending_action_id")
    assert pending_action_id is not None
    
    # Approve action
    manager.approve(pending_action_id)
    
    # Resume the same plan!
    mock_process = MagicMock()
    mock_process.pid = 2222
    
    mock_llm.generate.return_value = GenerationResult(
        raw_response={"message": {"content": "Editor launched successfully"}},
        metrics=GenerationMetrics("ollama", "model", 10.0, 1.0, 1.0, 8.0, 10, 20, 2.5, "fast")
    )
    
    with patch("app.services.applications.resolver.ApplicationResolver", return_value=mock_resolver), \
         patch("subprocess.Popen", return_value=mock_process):
        resume_result = task_executor.execute(
            plan=plan,
            original_request_text="Launch editor request",
            approval_action_id=pending_action_id,
            previous_observations=result.observations
        )
        
    assert resume_result.plan_status == PlanStatus.COMPLETED
    assert step1.status == StepStatus.COMPLETED
    assert step2.status == StepStatus.COMPLETED
    assert manager.get(pending_action_id).status == PendingActionStatus.EXECUTED
