"""Unit tests for AgentRunner and TaskExecutor human approval integrations."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.agent.runner import AgentRunner, AgentRunResult
from app.agent.models import AgentRequest, ToolCall
from app.agent.metrics import AgentExecutionMetrics
from app.tools.registry import ToolRegistry
from app.tools.executor import ToolExecutor
from app.tools.models import ToolPermission, ToolResult
from app.ai.manager import LLMManager
from app.ai.parser import ResponseParser
from app.ai.models import GenerationResult, GenerationMetrics
from app.approval.models import PendingAction, PendingActionStatus
from app.approval.manager import ApprovalManager
from app.planning.models import TaskPlan, PlanStep, StepType, StepStatus, PlanStatus, StepObservation
from app.planning.executor import TaskExecutor
from app.planning.validator import PlanValidator
from tests.unit.test_approval_system import RecordConfirmationActionTool, HarmlessSafeTool


def test_agent_runner_suspends_on_confirmation(tmp_path):
    # Setup ToolRegistry with a confirmation tool
    registry = ToolRegistry()
    conf_tool = RecordConfirmationActionTool()
    registry.register(conf_tool)

    # Setup ApprovalManager & ToolExecutor
    from app.approval.repository import SQLiteApprovalRepository
    repo = SQLiteApprovalRepository(database_path=tmp_path / "db.sqlite")
    manager = ApprovalManager(repository=repo)
    executor = ToolExecutor(registry, approval_manager=manager)

    # Setup LLMManager Mock that requests the tool call
    mock_llm_manager = MagicMock(spec=LLMManager)
    
    # Mock Ollama generation result
    metrics = GenerationMetrics("ollama", "qwen3:8b", 10.0, 1.0, 1.0, 8.0, 10, 20, 2.5, "tool_selection")
    gen_result = GenerationResult(
        raw_response={
            "message": {
                "role": "assistant",
                "content": "Let me record this confirmation action.",
                "tool_calls": [
                    {
                        "type": "function",
                        "function": {
                            "name": "record_confirmation_action",
                            "arguments": {"value": "diagnostic_test"}
                        }
                    }
                ]
            }
        },
        metrics=metrics
    )
    mock_llm_manager.generate.return_value = gen_result

    # ResponseParser setup
    parser = ResponseParser()

    # AgentRunner setup
    runner = AgentRunner(
        llm_manager=mock_llm_manager,
        registry=registry,
        executor=executor,
        parser=parser
    )

    request = AgentRequest("req_123", "Run record confirmation tool.", "terminal")
    
    # Run agent loop
    run_result = runner.run(request, [])
    
    # Assert runner execution stopped/suspended
    assert run_result.confirmation_required is True
    assert run_result.pending_action_id is not None
    
    # Verify PendingAction created in DB
    action = manager.get(run_result.pending_action_id)
    assert action is not None
    assert action.tool_name == "record_confirmation_action"
    assert action.arguments == {"value": "diagnostic_test"}
    assert action.status == PendingActionStatus.PENDING


def test_task_executor_waits_for_approval(tmp_path):
    # Setup ToolRegistry with safe and confirmation tools
    registry = ToolRegistry()
    safe_tool = HarmlessSafeTool()
    conf_tool = RecordConfirmationActionTool()
    registry.register(safe_tool)
    registry.register(conf_tool)

    # Setup ApprovalManager & ToolExecutor
    from app.approval.repository import SQLiteApprovalRepository
    repo = SQLiteApprovalRepository(database_path=tmp_path / "db.sqlite")
    manager = ApprovalManager(repository=repo)
    executor = ToolExecutor(registry, approval_manager=manager)

    # Setup LLMManager Mock
    mock_llm = MagicMock(spec=LLMManager)

    # Setup Plan Step list: Safe step -> Confirmation step -> Synthesis step
    step1 = PlanStep("step_1", 1, "Run safe tool", StepType.TOOL, "harmless_safe_tool", {})
    step2 = PlanStep("step_2", 2, "Run conf tool", StepType.TOOL, "record_confirmation_action", {"value": "p_val"})
    step3 = PlanStep("step_3", 3, "Synthesis step", StepType.SYNTHESIS)
    
    plan = TaskPlan("plan_1", "Test goal", [step1, step2, step3])

    task_executor = TaskExecutor(mock_llm, registry, executor, PlanValidator(registry))

    # Run plan execution
    result = task_executor.execute(plan, "Test request")

    # Assert plan execution entered WAITING_APPROVAL at step 2
    assert result.plan_status == PlanStatus.WAITING_APPROVAL
    assert step1.status == StepStatus.COMPLETED
    assert step2.status == StepStatus.WAITING_APPROVAL
    assert step3.status == StepStatus.PENDING  # subsequent steps remain pending
    
    # Check confirmation metadata
    assert result.metadata.get("confirmation_required") is True
    pending_action_id = result.metadata.get("pending_action_id")
    assert pending_action_id is not None

    # Assert action exists in repository and is PENDING
    action = manager.get(pending_action_id)
    assert action is not None
    assert action.tool_name == "record_confirmation_action"
    assert action.arguments == {"value": "p_val"}
    assert action.status == PendingActionStatus.PENDING

    # Now approve the action
    manager.approve(pending_action_id)

    # Resume the same plan!
    mock_llm.generate.return_value = GenerationResult(
        raw_response={"message": {"content": "Reasoning step finished"}},
        metrics=GenerationMetrics("ollama", "model", 10.0, 1.0, 1.0, 8.0, 10, 20, 2.5, "fast")
    )
    
    resume_result = task_executor.execute(
        plan=plan,
        original_request_text="Test request",
        approval_action_id=pending_action_id,
        previous_observations=result.observations
    )

    # Assert plan finished successfully after resumption
    assert resume_result.plan_status == PlanStatus.COMPLETED
    assert step2.status == StepStatus.COMPLETED
    assert step3.status == StepStatus.COMPLETED
    
    # Assert action state is EXECUTED
    assert manager.get(pending_action_id).status == PendingActionStatus.EXECUTED
