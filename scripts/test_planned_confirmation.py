"""Diagnostic script for planned execution human approval integration."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.append(str(Path(__file__).parent.parent))

from app.core.application import Application
from app.planning.models import TaskPlan, PlanStep, StepType, StepStatus, PlanStatus
from app.ai.manager import LLMManager
from app.ai.models import GenerationResult, GenerationMetrics
from tests.unit.test_approval_system import RecordConfirmationActionTool, HarmlessSafeTool


def run_diagnostic():
    print("=== Planned Execution Confirmation loop Diagnostic ===")
    
    app = Application()
    try:
        app.initialize()
        app._initialize_llm()
        app._initialize_agent()
    except Exception as e:
        print(f"FAILED: Application initialization failed: {e}")
        sys.exit(1)

    # Register Harmless SAFE and CONFIRMATION tools
    registry = app.container.get("tool_registry")
    safe_tool = HarmlessSafeTool()
    recorder = []
    conf_tool = RecordConfirmationActionTool(recorder)
    registry.register(safe_tool)
    registry.register(conf_tool)

    # Mock the LLMManager so we don't hit Ollama
    mock_llm = MagicMock(spec=LLMManager)
    
    # 1. Setup mock generation result for the final reasoning/synthesis step resumption
    metrics = GenerationMetrics("ollama", "model", 10.0, 1.0, 1.0, 8.0, 10, 20, 2.5, "fast")
    mock_llm.generate.return_value = GenerationResult(
        raw_response={"message": {"content": "Planned task completed successfully."}},
        metrics=metrics
    )

    # Also update controller and task_executor to use mock LLM
    controller = app.container.get("controller")
    controller._llm_manager = mock_llm
    task_executor = app.container.get("planning_executor")
    task_executor._llm_manager = mock_llm

    failures = 0

    # 2. Setup the TaskPlan with safe tool, confirmation tool, and synthesis
    step1 = PlanStep("step_1", 1, "Run safe tool", StepType.TOOL, "harmless_safe_tool", {})
    step2 = PlanStep("step_2", 2, "Run conf tool", StepType.TOOL, "record_confirmation_action", {"value": "planned_val"})
    step3 = PlanStep("step_3", 3, "Synthesis step", StepType.SYNTHESIS)
    
    plan = TaskPlan("plan_planned_diag", "Test planned goal", [step1, step2, step3])

    # Assign it as active plan in controller
    controller._active_plan = plan
    controller._active_observations = []

    # 3. Run execution
    print("\n1. Running planned execution...")
    # Simulate routing decision mode PLANNED
    from app.planning.models import ExecutionMode, PlanningDecision
    from app.agent.models import AgentRequest
    request = AgentRequest("req_planned_diag", "Run planned goal.", "terminal")
    
    # Execute step 1 & 2
    exec_result = task_executor.execute(plan, "Run planned goal.")

    # Check if suspended at step 2
    if exec_result.plan_status == PlanStatus.WAITING_APPROVAL:
        action_id = exec_result.metadata.get("pending_action_id")
        print(f"  [PASS] Plan execution suspended. PendingAction ID: {action_id}")
        assert step1.status == StepStatus.COMPLETED
        assert step2.status == StepStatus.WAITING_APPROVAL
        assert step3.status == StepStatus.PENDING
        print("  [PASS] SAFE step completed, CONFIRMATION step waiting, Synthesis step remains pending.")
    else:
        print(f"  [FAIL] Expected suspension, got status: {exec_result.plan_status.value}")
        failures += 1
        return

    # Check that tool has not executed
    if len(recorder) == 0:
        print("  [PASS] Tool has not executed yet.")
    else:
        print("  [FAIL] Tool executed prematurely.")
        failures += 1

    # 4. Approve and Resume
    print("\n2. Approving action and resuming planned execution...")
    approval_manager = app.container.get("approval_manager")
    approval_manager.approve(action_id)

    # Save active state to controller just like process_request does
    controller._active_observations = exec_result.observations

    # Resume plan
    resume_result = task_executor.execute(
        plan=plan,
        original_request_text="Run planned goal.",
        approval_action_id=action_id,
        previous_observations=controller._active_observations
    )

    # Check that tool was executed once
    if len(recorder) == 1 and recorder[0] == "planned_val":
        print("  [PASS] Tool executed once with correct value.")
    else:
        print(f"  [FAIL] Execution list count: {len(recorder)}")
        failures += 1

    # Check that plan finished successfully
    if resume_result.plan_status == PlanStatus.COMPLETED:
        print(f"  [PASS] Plan completed successfully. Final response: '{resume_result.final_response}'")
    else:
        print(f"  [FAIL] Expected plan completion, got status: {resume_result.plan_status.value}")
        failures += 1

    print("\n-------------------------------------------")
    if failures == 0:
        print("DIAGNOSTIC STATUS: PASS")
    else:
        print(f"DIAGNOSTIC STATUS: FAIL ({failures} failures)")
        sys.exit(1)


if __name__ == "__main__":
    run_diagnostic()
