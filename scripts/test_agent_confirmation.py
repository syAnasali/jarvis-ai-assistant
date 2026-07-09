"""Diagnostic script for AgentRunner human approval loop integration."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.append(str(Path(__file__).parent.parent))

from app.core.application import Application
from app.agent.models import AgentRequest, ToolCall
from app.ai.manager import LLMManager
from app.ai.models import GenerationResult, GenerationMetrics
from tests.unit.test_approval_system import RecordConfirmationActionTool


def run_diagnostic():
    print("=== Agent Runner Confirmation loop Diagnostic ===")
    
    app = Application()
    try:
        app.initialize()
        app._initialize_llm()
        app._initialize_agent()
    except Exception as e:
        print(f"FAILED: Application initialization failed: {e}")
        sys.exit(1)

    # Register Harmless CONFIRMATION tool in production registry for this run
    registry = app.container.get("tool_registry")
    recorder = []
    conf_tool = RecordConfirmationActionTool(recorder)
    registry.register(conf_tool)

    # Mock the LLMManager so it requests a tool first, then replies with final response
    original_llm_manager = app.container.get("llm_manager")
    mock_llm = MagicMock(spec=LLMManager)
    app.container.register("llm_manager", mock_llm)
    
    # Also update controller and runner to use this mock llm manager
    controller = app.container.get("controller")
    runner = app.container.get("agent_runner")
    controller._llm_manager = mock_llm
    runner._llm_manager = mock_llm

    # Setup the mock generations
    metrics = GenerationMetrics("ollama", "qwen3:8b", 10.0, 1.0, 1.0, 8.0, 10, 20, 2.5, "tool_selection")
    
    # 1st call: request the confirmation tool call
    gen_result_1 = GenerationResult(
        raw_response={
            "message": {
                "role": "assistant",
                "content": "I need to record a confirmation action.",
                "tool_calls": [
                    {
                        "type": "function",
                        "function": {
                            "name": "record_confirmation_action",
                            "arguments": {"value": "agent_loop_test"}
                        }
                    }
                ]
            }
        },
        metrics=metrics
    )

    # 2nd call (resumption): provide the final assistant answer
    gen_result_2 = GenerationResult(
        raw_response={
            "message": {
                "role": "assistant",
                "content": "I have successfully recorded the action as requested."
            }
        },
        metrics=metrics
    )

    mock_llm.generate.side_effect = [gen_result_1, gen_result_2]

    failures = 0

    # 1. Run direct request
    print("\n1. Running agent loop requesting confirmation tool...")
    request = AgentRequest("req_agent_loop", "Record agent loop test.", "terminal")
    response1 = controller.process_request(request)

    # Check if suspended
    if response1.metadata.get("confirmation_required") is True:
        action_id = response1.metadata.get("pending_action_id")
        print(f"  [PASS] Loop suspended. PendingAction ID: {action_id}")
    else:
        print(f"  [FAIL] Expected suspension, got: {response1.text}")
        failures += 1
        return

    # Check that tool has not executed
    if len(recorder) == 0:
        print("  [PASS] Tool has not executed yet.")
    else:
        print("  [FAIL] Tool executed prematurely.")
        failures += 1

    # 2. Approve and Resume
    print("\n2. Approving action and resuming execution...")
    approval_manager = app.container.get("approval_manager")
    approval_manager.approve(action_id)
    
    response2 = controller.process_request(request, approval_action_id=action_id)

    # Check that tool was executed once
    if len(recorder) == 1 and recorder[0] == "agent_loop_test":
        print("  [PASS] Tool executed once with correct value.")
    else:
        print(f"  [FAIL] Execution list count: {len(recorder)}")
        failures += 1

    # Check that final response is produced
    if response2.metadata.get("confirmation_required") is not True and "recorded the action" in response2.text:
        print(f"  [PASS] Final assistant response produced: '{response2.text}'")
    else:
        print(f"  [FAIL] Expected final text response, got: '{response2.text}'")
        failures += 1

    print("\n-------------------------------------------")
    if failures == 0:
        print("DIAGNOSTIC STATUS: PASS")
    else:
        print(f"DIAGNOSTIC STATUS: FAIL ({failures} failures)")
        sys.exit(1)


if __name__ == "__main__":
    run_diagnostic()
