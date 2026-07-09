"""Diagnostic script for AgentController application launch confirmation flow with real Ollama."""

import sys
import os
import signal
import time
import json
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.application import Application
from app.agent.models import AgentRequest


def run_diagnostic():
    print("=== Agent Application Launch Diagnostic ===")
    
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

    # 1. Start agent execution with user prompt: "Open Notepad."
    print("\n1. Asking Jarvis to 'Open Notepad.'...")
    request = AgentRequest("req_agent_app_launch", "Open Notepad.", "terminal")
    response1 = controller.process_request(request)

    # We expect it to call resolve_application first, then launch_application, and suspend on confirmation.
    if response1.metadata.get("confirmation_required") is True:
        action_id = response1.metadata.get("pending_action_id")
        tool_name = response1.metadata.get("tool_name")
        print(f"  [PASS] Agent suspended correctly. Tool: {tool_name}, PendingAction ID: {action_id}")
    else:
        print(f"  [FAIL] Expected suspension, got response: '{response1.text}'")
        sys.exit(1)

    # 2. Approve action
    print("\n2. Approving action in database...")
    try:
        approval_manager.approve(action_id)
        print("  [PASS] Action approved.")
    except Exception as e:
        print(f"  [FAIL] Failed to approve action: {e}")
        sys.exit(1)

    # 3. Resume agent execution
    print("\n3. Resuming agent execution...")
    response2 = controller.process_request(request, approval_action_id=action_id)

    # Verify Notepad is launched and PID is returned
    pid = None
    messages = controller.conversation.get_history()
    for msg in messages:
        if msg.role.value == "tool" and msg.metadata.get("tool_name") == "launch_application":
            try:
                data = json.loads(msg.content)
                pid = data.get("pid")
                print(f"  [PASS] Found launch tool output in history. PID: {pid}")
            except Exception as e:
                print(f"  [WARNING] Failed to parse tool content: {e}")

    if pid:
        print(f"  [PASS] Notepad process PID: {pid}")
    else:
        print("  [FAIL] Could not retrieve PID from tool execution output.")
        failures += 1

    # Verify final assistant response is non-empty
    if response2.text and "Open Notepad" not in response2.text:
        print(f"  [PASS] Final assistant response: '{response2.text}'")
    else:
        print(f"  [FAIL] Empty or invalid final assistant response: '{response2.text}'")
        failures += 1

    # 4. Clean up Notepad process
    if pid:
        print(f"\n4. Cleaning up launched process (PID: {pid})...")
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
