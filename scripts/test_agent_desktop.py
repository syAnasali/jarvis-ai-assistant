"""Diagnostic script for AgentController desktop tool confirmation flow with real Ollama."""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.application import Application
from app.agent.models import AgentRequest
from tests.unit.test_desktop_service import FakeDesktopBackend


def run_diagnostic():
    print("=== Agent Desktop Confirmation Diagnostic ===")
    
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
    desktop_service = app.container.get("desktop_service")

    # Inject FakeDesktopBackend to keep diagnostic robust and non-destructive
    fake_backend = FakeDesktopBackend()
    fake_backend.windows = [
        (1001, "Notepad", 8001, "notepad.exe"),
        (1002, "Google Chrome", 8002, "chrome.exe"),
    ]
    fake_backend.valid_hwnds = {1001, 1002}
    fake_backend.active_hwnd = 1001  # Notepad is active

    desktop_service._backend = fake_backend
    print("Injected FakeDesktopBackend into DesktopService.")

    failures = 0

    try:
        # 1. Ask agent to type into active window
        print("\n1. Asking Jarvis to 'Type Hello Anas in the current window.'...")
        request = AgentRequest("req_agent_desktop_type", "Type Hello Anas in the current window.", "terminal")
        response1 = controller.process_request(request)

        # Expect suspension
        if response1.metadata.get("confirmation_required") is True:
            action_id = response1.metadata.get("pending_action_id")
            tool_name = response1.metadata.get("tool_name")
            print(f"  [PASS] Agent suspended correctly. Tool: {tool_name}, PendingAction ID: {action_id}")
        else:
            print(f"  [FAIL] Expected suspension, got response: '{response1.text}'")
            sys.exit(1)

        # Verify no text typed before approval
        if not fake_backend.typed_text:
            print("  [PASS] Text was not sent to backend before approval.")
        else:
            print(f"  [FAIL] Text sent before approval: {fake_backend.typed_text}")
            failures += 1

        # 2. Approve action
        print("\n2. Approving action in database...")
        approval_manager.approve(action_id)
        print("  [PASS] Action approved.")

        # 3. Resume execution
        print("\n3. Resuming agent execution...")
        response2 = controller.process_request(request, approval_action_id=action_id)

        # Verify text was typed
        if fake_backend.typed_text and fake_backend.typed_text[-1] == "Hello Anas":
            print(f"  [PASS] Text correctly sent to backend: '{fake_backend.typed_text[-1]}'")
        else:
            print(f"  [FAIL] Text was not typed correctly. Typed: {fake_backend.typed_text}")
            failures += 1

        # Verify final response is non-empty
        if response2.text:
            print(f"  [PASS] Final assistant response: '{response2.text}'")
        else:
            print("  [FAIL] Empty final assistant response.")
            failures += 1

    except Exception as e:
        print(f"  [FAIL] Diagnostic encountered unexpected exception: {e}")
        failures += 1

    print("\n-------------------------------------------")
    if failures == 0:
        print("DIAGNOSTIC STATUS: PASS")
    else:
        print(f"DIAGNOSTIC STATUS: FAIL ({failures} failures)")
        sys.exit(1)


if __name__ == "__main__":
    run_diagnostic()
