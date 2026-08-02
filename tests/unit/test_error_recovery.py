import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.agent.models import AgentRequest, AgentResponse
from app.agent.controller import AgentController
from app.planning.executor import TaskExecutor
from app.planning.models import TaskPlan, PlanStep, StepType, StepStatus, PlanStatus, PlanExecutionResult
from app.tools.registry import ToolRegistry
from app.tools.executor import ToolExecutor, ToolResult
from app.core.exceptions import PlanExecutionError, StepExecutionError


def test_recursion_depth_protection():
    """Verify that TaskExecutor aborts execution if recursion depth limit is exceeded."""
    llm_manager = MagicMock()
    registry = ToolRegistry()
    tool_executor = ToolExecutor(registry)
    planner = MagicMock()

    executor = TaskExecutor(
        llm_manager=llm_manager,
        registry=registry,
        tool_executor=tool_executor,
        planner=planner
    )

    plan = TaskPlan(
        plan_id="plan_depth_test",
        goal="Test recursion depth limit",
        steps=[
            PlanStep(
                step_id="step_1",
                sequence=1,
                step_type=StepType.SYNTHESIS,
                description="Final reply",
                status=StepStatus.PENDING
            )
        ],
        status=PlanStatus.CREATED,
        created_at=datetime.now(timezone.utc)
    )

    with pytest.raises(PlanExecutionError) as exc_info:
        executor.execute(plan, "test request", recursion_depth=3)

    assert "Recursion depth safeguard triggered" in str(exc_info.value)


def test_duplicate_tool_call_protection():
    """Verify that duplicate tool calls with the same arguments are blocked by TaskExecutor."""
    llm_manager = MagicMock()
    registry = ToolRegistry()
    
    # Register mock create_file tool to satisfy PlanValidator
    mock_tool = MagicMock()
    mock_tool.name = "create_file"
    registry.register(mock_tool)
    
    tool_executor = ToolExecutor(registry)
    planner = MagicMock()

    executor = TaskExecutor(
        llm_manager=llm_manager,
        registry=registry,
        tool_executor=tool_executor,
        planner=planner
    )

    plan = TaskPlan(
        plan_id="plan_dup_test",
        goal="Test duplicate protection",
        steps=[
            PlanStep(
                step_id="step_1",
                sequence=1,
                step_type=StepType.TOOL,
                description="Call a tool",
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

    # Pre-populate failed_attempts with this exact tool and args
    failed_attempts = {("create_file", (("relative_path", "notes.txt"), ("root", "desktop")))}

    result = executor.execute(plan, "test request", failed_attempts=failed_attempts)
    
    assert not result.success
    assert result.plan_status == PlanStatus.FAILED
    assert any("Duplicate tool call blocked" in obs.content for obs in result.observations)


def test_controller_graceful_recovery_ollama_unavailable():
    """Verify that AgentController gracefully handles Ollama connection failures."""
    llm_manager = MagicMock()
    llm_manager.generate.side_effect = Exception("Ollama connection failed: ConnectError")

    conversation = MagicMock()
    context_manager = MagicMock()
    controller = AgentController(
        conversation=conversation,
        context_manager=context_manager,
        llm_manager=llm_manager
    )

    request = AgentRequest(
        request_id="test_ollama_unavailable",
        text="Hello Jarvis",
        source="unit_test",
        timestamp=datetime.now(timezone.utc)
    )

    response = controller.process_request(request)

    assert isinstance(response, AgentResponse)
    assert not response.success
    assert "trouble connecting to the local Ollama service" in response.text
    assert response.metadata["recovery_path"] == "ollama_connection_fallback"


def test_controller_graceful_recovery_permission_denied():
    """Verify that AgentController gracefully handles filesystem permission errors."""
    llm_manager = MagicMock()
    
    # Force a permission error in _prepare_request or similar initialization
    with patch("app.agent.controller.AgentController._prepare_request", side_effect=PermissionError("[WinError 5] Access is denied")):
        conversation = MagicMock()
        context_manager = MagicMock()
        controller = AgentController(
            conversation=conversation,
            context_manager=context_manager,
            llm_manager=llm_manager
        )

        request = AgentRequest(
            request_id="test_permission_denied",
            text="Delete system files",
            source="unit_test",
            timestamp=datetime.now(timezone.utc)
        )

        response = controller.process_request(request)

        assert isinstance(response, AgentResponse)
        assert not response.success
        assert "filesystem permission error occurred" in response.text
        assert response.metadata["recovery_path"] == "permission_denied_fallback"


def test_controller_graceful_recovery_file_not_found():
    """Verify that AgentController gracefully handles file not found errors."""
    llm_manager = MagicMock()
    
    with patch("app.agent.controller.AgentController._prepare_request", side_effect=FileNotFoundError("[WinError 2] The system cannot find the file specified")):
        conversation = MagicMock()
        context_manager = MagicMock()
        controller = AgentController(
            conversation=conversation,
            context_manager=context_manager,
            llm_manager=llm_manager
        )

        request = AgentRequest(
            request_id="test_file_not_found",
            text="Read nonexistent file",
            source="unit_test",
            timestamp=datetime.now(timezone.utc)
        )

        response = controller.process_request(request)

        assert isinstance(response, AgentResponse)
        assert not response.success
        assert "File not found error" in response.text
        assert response.metadata["recovery_path"] == "file_not_found_fallback"
