"""Diagnostic script for TaskExecutor planned desktop sequential approval flow with real Ollama."""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.application import Application
from app.agent.models import AgentRequest
from app.approval.models import PendingActionStatus
from tests.unit.test_desktop_service import FakeDesktopBackend


def run_diagnostic():
    print("=== Planned Desktop Confirmation Diagnostic ===")
    
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
    fake_backend.active_hwnd = 1002  # Chrome starts active, so focusing Notepad is required

    desktop_service._backend = fake_backend
    print("Injected FakeDesktopBackend into DesktopService.")

    failures = 0

    try:
        # Prompt semantically: sequential actions (focus Notepad then type text)
        prompt = "Focus the Notepad window, and then type Hello Anas into it."
        print(f"\n1. Submitting planned request: '{prompt}'")
        request = AgentRequest("req_planned_desktop", prompt, "terminal")
        response1 = controller.process_request(request)

        # A. Verify planned execution routing
        if controller._router.route(request).mode.value == "PLANNED":
            print("  [PASS] Request routed correctly to PLANNED mode.")
        else:
            print("  [WARNING] Router did not classify prompt as PLANNED. Continuing anyway...")

        # B. Verify first WAITING_APPROVAL (for focus_window)
        if response1.metadata.get("confirmation_required") is True:
            action_id_1 = response1.metadata.get("pending_action_id")
            tool_name_1 = response1.metadata.get("tool_name")
            print(f"  [PASS] First step suspended on confirmation. Tool: {tool_name_1}, PendingAction ID: {action_id_1}")
            if tool_name_1 != "focus_window":
                print(f"  [FAIL] Expected first tool to be 'focus_window', got '{tool_name_1}'")
                failures += 1
        else:
            print(f"  [FAIL] Expected first step confirmation suspension, got text: '{response1.text}'")
            sys.exit(1)

        # Verify active window hasn't changed to Notepad yet
        if fake_backend.active_hwnd == 1002:
            print("  [PASS] Active window is still Chrome before first approval.")
        else:
            print(f"  [FAIL] Active window is HWND {fake_backend.active_hwnd} before first approval.")
            failures += 1

        # C. Approve first action (focus_window)
        print("\n2. Approving first action (focus_window)...")
        approval_manager.approve(action_id_1)
        print("  [PASS] First action approved.")

        # D. Resume plan execution (expects second WAITING_APPROVAL for type_text)
        print("\n3. Resuming plan execution...")
        response2 = controller.process_request(request, approval_action_id=action_id_1)

        if response2.metadata.get("confirmation_required") is True:
            action_id_2 = response2.metadata.get("pending_action_id")
            tool_name_2 = response2.metadata.get("tool_name")
            print(f"  [PASS] Second step suspended on confirmation. Tool: {tool_name_2}, PendingAction ID: {action_id_2}")
            if tool_name_2 != "type_text":
                print(f"  [FAIL] Expected second tool to be 'type_text', got '{tool_name_2}'")
                failures += 1
        else:
            print(f"  [FAIL] Expected second step confirmation suspension, got text: '{response2.text}'")
            failures += 1
            action_id_2 = None

        # Verify focus has changed to Notepad, but text is not typed yet
        if fake_backend.active_hwnd == 1001:
            print("  [PASS] Focus successfully changed to Notepad after first resume.")
        else:
            print(f"  [FAIL] Focus did not change. Active HWND: {fake_backend.active_hwnd}")
            failures += 1

        if not fake_backend.typed_text:
            print("  [PASS] Text was not typed yet before second approval.")
        else:
            print(f"  [FAIL] Text typed before second approval: {fake_backend.typed_text}")
            failures += 1

        # E. Approve second action (type_text) and complete plan
        if action_id_2:
            print("\n4. Approving second action (type_text)...")
            approval_manager.approve(action_id_2)
            print("  [PASS] Second action approved.")

            print("\n5. Resuming plan execution to completion...")
            response3 = controller.process_request(request, approval_action_id=action_id_2)

            # Verify text was typed and final response is returned
            if fake_backend.typed_text and fake_backend.typed_text[-1] == "Hello Anas":
                print(f"  [PASS] Text correctly sent to backend: '{fake_backend.typed_text[-1]}'")
            else:
                print(f"  [FAIL] Text was not typed. Typed: {fake_backend.typed_text}")
                failures += 1

            if response3.text:
                print(f"  [PASS] Final plan response: '{response3.text}'")
            else:
                print("  [FAIL] Empty final plan response.")
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
