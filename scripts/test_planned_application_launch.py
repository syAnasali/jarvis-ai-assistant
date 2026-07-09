"""Diagnostic script for planned application launch and process monitoring integration."""

import sys
import os
import signal
import time
import json
import ast
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.application import Application
from app.agent.models import AgentRequest
from app.planning.models import PlanStatus


def run_diagnostic():
    print("=== Planned Application Launch Diagnostic ===")
    
    app = Application()
    try:
        app.initialize()
        app._initialize_llm()
        app._initialize_agent()
    except Exception as e:
        print(f"FAILED: Application initialization failed: {e}")
        sys.exit(1)

    controller = app.container.get("controller")
    approval_manager = app.container.get("approval_manager")

    failures = 0

    # 1. Start execution with planned query
    prompt = "Open Notepad and then tell me whether Ollama is running."
    print(f"\n1. Submitting request: '{prompt}'")
    
    request = AgentRequest("req_planned_launch", prompt, "terminal")
    response1 = controller.process_request(request)

    # 2. Check routing and plan status
    # Planned execution routing should be used
    exec_mode = response1.metadata.get("execution_mode")
    plan_status = response1.metadata.get("plan_status")
    
    print(f"  Execution Mode: {exec_mode}")
    print(f"  Plan Status: {plan_status}")
    
    if exec_mode == "planned" and response1.metadata.get("confirmation_required") is True:
        action_id = response1.metadata.get("pending_action_id")
        tool_name = response1.metadata.get("tool_name")
        print(f"  [PASS] Plan execution suspended correctly. Tool: {tool_name}, PendingAction ID: {action_id}")
    else:
        print(f"  [FAIL] Expected planned execution suspension, got response: '{response1.text}'")
        sys.exit(1)

    # Verify no launch before approval
    # Notepad is not running yet

    # 3. Approve action
    print("\n3. Approving action in database...")
    try:
        approval_manager.approve(action_id)
        print("  [PASS] Action approved.")
    except Exception as e:
        print(f"  [FAIL] Failed to approve action: {e}")
        sys.exit(1)

    # 4. Resume execution
    print("\n4. Resuming planned execution...")
    response2 = controller.process_request(request, approval_action_id=action_id)

    # Check that plan completed successfully
    final_status = response2.metadata.get("plan_status")
    print(f"  Final Plan Status: {final_status}")
    
    if final_status == "COMPLETED" and response2.success:
        print("  [PASS] Plan completed successfully.")
    else:
        print(f"  [FAIL] Plan failed or did not complete. Response success={response2.success}")
        failures += 1

    # Extract PID from plan observations in active session/history or controller state
    pid = None
    # We can inspect controller's active observations or the conversation history messages
    # Since plan completes, observations are returned in the result, which are added to conversation.
    obs_list = response2.metadata.get("plan_observations") or []
    for obs in obs_list:
        if obs.get("tool_name") == "launch_application":
            try:
                import ast
                content_dict = ast.literal_eval(obs.get("content", "{}"))
                pid = content_dict.get("pid")
                print(f"  [PASS] Found launch tool output in plan observations. PID: {pid}")
            except Exception as e:
                print(f"  [WARNING] Failed to parse observation content: {e}")

    if pid:
        print(f"  [PASS] Notepad process PID: {pid}")
    else:
        print("  [FAIL] Could not retrieve PID from plan execution observations.")
        failures += 1

    # Verify final assistant response is non-empty and contains Ollama process check
    if response2.text and ("Ollama" in response2.text or "running" in response2.text or "process" in response2.text):
        print(f"  [PASS] Final assistant response: '{response2.text}'")
    else:
        print(f"  [FAIL] Empty or invalid final assistant response: '{response2.text}'")
        failures += 1

    # 5. Clean up Notepad process
    if pid:
        print(f"\n5. Cleaning up launched process (PID: {pid})...")
        try:
            os.kill(pid, signal.SIGTERM)
            print("  [PASS] Process terminated successfully.")
        except Exception as e:
            print(f"  [WARNING] Process cleanup warning: {e}")

    print("\n-------------------------------------------")
    if failures == 0:
        print("DIAGNOSTIC STATUS: PASS")
    else:
        print(f"DIAGNOSTIC STATUS: FAIL ({failures} failures)")
        sys.exit(1)


if __name__ == "__main__":
    run_diagnostic()
