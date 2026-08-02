"""Unit tests for tool reliability validations and planner retry mechanism."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.core.exceptions import ToolValidationError, ToolExecutionError
from app.tools.models import ToolPermission, ToolResult
from app.agent.models import ToolCall, AgentRequest
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry
from app.tools.builtin.filesystem import CreateDirectoryTool, CreateFileTool, WriteTextFileTool
from app.planning.executor import TaskExecutor
from app.planning.models import TaskPlan, StepStatus, StepType, PlanStep, PlanStatus


def test_create_directory_validation():
    """Verify that CreateDirectoryTool rejects file paths ending with file extensions."""
    mock_service = MagicMock()
    tool = CreateDirectoryTool(mock_service)
    
    # Valid relative path directory name
    tool.validate_arguments({"root": "desktop", "relative_path": "projects/jarvis"})
    
    # Invalid paths with file extensions
    invalid_paths = [
        "projects/notes.txt",
        "notes.py",
        "nested/data.json",
        "docs/report.pdf",
    ]
    for p in invalid_paths:
        with pytest.raises(ToolValidationError) as excinfo:
            tool.validate_arguments({"root": "desktop", "relative_path": p})
        assert "must only be used for folders/directories" in str(excinfo.value)
        assert p in str(excinfo.value)


def test_create_file_validation():
    """Verify that CreateFileTool rejects directory paths and enforces file extensions."""
    mock_service = MagicMock()
    tool = CreateFileTool(mock_service)
    
    # Valid relative file path
    tool.validate_arguments({"root": "desktop", "relative_path": "notes.txt"})
    
    # Invalid paths representing directories (ends with slash or lacks dot)
    invalid_paths = [
        "projects/jarvis/",
        "projects\\jarvis\\",
        "projects/jarvis",
    ]
    for p in invalid_paths:
        with pytest.raises(ToolValidationError) as excinfo:
            tool.validate_arguments({"root": "desktop", "relative_path": p})
        assert "must only be used for files, never for folders" in str(excinfo.value)
        assert p in str(excinfo.value)


def test_write_text_file_validation():
    """Verify that WriteTextFileTool rejects directory paths and enforces non-empty content."""
    mock_service = MagicMock()
    tool = WriteTextFileTool(mock_service)
    
    # Valid arguments
    tool.validate_arguments({"root": "desktop", "relative_path": "todo.txt", "content": "1. Buy milk"})
    
    # Invalid path
    with pytest.raises(ToolValidationError) as excinfo:
        tool.validate_arguments({"root": "desktop", "relative_path": "projects/jarvis/", "content": "test"})
    assert "must target a file path, never a directory" in str(excinfo.value)
    
    # Empty content
    with pytest.raises(ToolValidationError) as excinfo:
        tool.validate_arguments({"root": "desktop", "relative_path": "todo.txt", "content": ""})
    assert "requires non-empty content to write" in str(excinfo.value)
    
    with pytest.raises(ToolValidationError) as excinfo:
        tool.validate_arguments({"root": "desktop", "relative_path": "todo.txt", "content": None})
    assert "must be of type string" in str(excinfo.value)


def test_validation_happens_before_approval():
    """Verify that invalid tool calls fail validation before invoking the approval flow."""
    mock_registry = ToolRegistry()
    mock_service = MagicMock()
    
    # CreateDirectoryTool is CONFIRMATION permission level
    tool = CreateDirectoryTool(mock_service)
    mock_registry.register(tool)
    
    mock_approval_mgr = MagicMock()
    executor = ToolExecutor(mock_registry, mock_approval_mgr)
    
    # Call tool with invalid extension
    tc = ToolCall(tool_name="create_directory", arguments={"root": "desktop", "relative_path": "notes.txt"})
    result = executor.execute(tc)
    
    # Verification
    assert result.success is False
    assert result.metadata.get("validation_failed") is True
    assert "Validation failed" in result.error
    
    # Assert no pending action was created in ApprovalManager!
    mock_approval_mgr.create_pending_action.assert_not_called()


def test_planner_retry_success():
    """Verify that TaskExecutor correctly triggers one planner retry when validation fails, and completes successfully."""
    llm_manager = MagicMock()
    registry = ToolRegistry()
    
    # Register tools
    mock_service = MagicMock()
    mock_service.write_text_file.return_value = True
    create_dir_tool = CreateDirectoryTool(mock_service)
    create_file_tool = CreateFileTool(mock_service)
    registry.register(create_dir_tool)
    registry.register(create_file_tool)
    
    # Set up ToolExecutor
    tool_executor = ToolExecutor(registry)
    
    # Setup mock Planner
    planner = MagicMock()
    
    # Configure TaskExecutor
    task_executor = TaskExecutor(
        llm_manager=llm_manager,
        registry=registry,
        tool_executor=tool_executor,
        planner=planner
    )
    task_executor._extract_text = MagicMock(return_value="Task completed successfully.")
    
    # Plan A: Has a wrong tool call (create_directory on notes.txt)
    plan_a = TaskPlan(
        plan_id="plan_a",
        goal="Create an empty file notes.txt",
        steps=[
            PlanStep(
                step_id="step_1",
                sequence=1,
                step_type=StepType.TOOL,
                description="Create folder notes.txt",
                tool_name="create_directory",
                tool_arguments={"root": "desktop", "relative_path": "notes.txt"},
                status=StepStatus.PENDING
            ),
            PlanStep(
                step_id="step_2",
                sequence=2,
                step_type=StepType.SYNTHESIS,
                description="Summarize results",
                status=StepStatus.PENDING
            )
        ],
        status=PlanStatus.CREATED,
        created_at=datetime.now(timezone.utc)
    )
    
    # Plan B (the corrected retry plan generated by planner)
    plan_b = TaskPlan(
        plan_id="plan_b",
        goal="Create an empty file notes.txt",
        steps=[
            PlanStep(
                step_id="step_1",
                sequence=1,
                step_type=StepType.TOOL,
                description="Create empty file notes.txt",
                tool_name="create_file",
                tool_arguments={"root": "desktop", "relative_path": "notes.txt"},
                status=StepStatus.PENDING
            ),
            PlanStep(
                step_id="step_2",
                sequence=2,
                step_type=StepType.SYNTHESIS,
                description="Summarize results",
                status=StepStatus.PENDING
            )
        ],
        status=PlanStatus.CREATED,
        created_at=datetime.now(timezone.utc)
    )
    
    planner.create_plan.return_value = plan_b

    # Execute Plan A
    with patch.object(CreateFileTool, "permission_level", ToolPermission.SAFE):
        result = task_executor.execute(plan_a, original_request_text="Create empty notes.txt on desktop")

    # Assertions
    assert result.plan_status == PlanStatus.COMPLETED
    assert result.steps_completed == 2
    assert result.steps_failed == 0
    
    # Verify planner was called once with feedback in the request text
    planner.create_plan.assert_called_once()
    call_args = planner.create_plan.call_args[1]
    assert "[System Feedback:" in call_args["request"].text
    assert "create_directory" in call_args["request"].text


def test_planner_retry_failure():
    """Verify that when a planner retry still fails validation, it stops and returns a safe error without infinite looping."""
    llm_manager = MagicMock()
    registry = ToolRegistry()
    
    # Register tool
    mock_service = MagicMock()
    create_dir_tool = CreateDirectoryTool(mock_service)
    registry.register(create_dir_tool)
    
    tool_executor = ToolExecutor(registry)
    planner = MagicMock()
    
    task_executor = TaskExecutor(
        llm_manager=llm_manager,
        registry=registry,
        tool_executor=tool_executor,
        planner=planner
    )
    task_executor._extract_text = MagicMock(return_value="I couldn't complete the task. Tool validation error: create_directory failed.")
    
    # Plan A
    plan_a = TaskPlan(
        plan_id="plan_a",
        goal="Create folder notes.txt",
        steps=[
            PlanStep(
                step_id="step_1",
                sequence=1,
                step_type=StepType.TOOL,
                description="Create folder notes.txt",
                tool_name="create_directory",
                tool_arguments={"root": "desktop", "relative_path": "notes.txt"},
                status=StepStatus.PENDING
            ),
            PlanStep(
                step_id="step_2",
                sequence=2,
                step_type=StepType.SYNTHESIS,
                description="Summarize results",
                status=StepStatus.PENDING
            )
        ],
        status=PlanStatus.CREATED,
        created_at=datetime.now(timezone.utc)
    )
    
    # Plan B (still invalid)
    plan_b = TaskPlan(
        plan_id="plan_b",
        goal="Create folder notes.txt",
        steps=[
            PlanStep(
                step_id="step_1",
                sequence=1,
                step_type=StepType.TOOL,
                description="Create folder notes2.txt",
                tool_name="create_directory",
                tool_arguments={"root": "desktop", "relative_path": "notes2.txt"},
                status=StepStatus.PENDING
            ),
            PlanStep(
                step_id="step_2",
                sequence=2,
                step_type=StepType.SYNTHESIS,
                description="Summarize results",
                status=StepStatus.PENDING
            )
        ],
        status=PlanStatus.CREATED,
        created_at=datetime.now(timezone.utc)
    )
    
    planner.create_plan.return_value = plan_b
    
    # Execute Plan A
    result = task_executor.execute(plan_a, original_request_text="Create folder notes.txt")
    
    # Assertions
    assert result.plan_status == PlanStatus.FAILED
    assert result.steps_failed == 1
    assert "Tool validation error" in result.final_response
    
    # Verify planner was only called once (proving no infinite loop because retry_allowed = False on second run)
    assert planner.create_plan.call_count == 1
