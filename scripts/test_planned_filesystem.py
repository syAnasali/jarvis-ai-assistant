"""Diagnostic script for TaskExecutor planned filesystem sequential approval flow with real Ollama."""

import sys
import os
import shutil
import tempfile
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.application import Application
from app.agent.models import AgentRequest
from app.approval.models import PendingActionStatus


def run_diagnostic():
    print("=== Planned Filesystem Confirmation Diagnostic ===")
    
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
    filesystem_service = app.container.get("filesystem_service")

    # Setup isolated temp directory and redirect policy's desktop root
    temp_dir = Path(tempfile.mkdtemp())
    isolated_desktop = temp_dir / "Desktop"
    isolated_desktop.mkdir(parents=True, exist_ok=True)
    
    # In-place redirect of the desktop root
    filesystem_service._policy._roots["desktop"] = isolated_desktop.resolve()
    print(f"Redirected desktop root to: {isolated_desktop.resolve()}")

    failures = 0
    target_folder = isolated_desktop / "jarvis-notes"
    target_file = target_folder / "todo.txt"

    try:
        # Prompt semantically: sequential actions (create directory then write file)
        prompt = "Create a folder called jarvis-notes on my Desktop, then create todo.txt inside it containing Buy milk."
        print(f"\n1. Submitting planned request: '{prompt}'")
        request = AgentRequest("req_planned_fs", prompt, "terminal")
        response1 = controller.process_request(request)

        # A. Verify planned execution routing
        if controller._router.route(request).mode.value == "PLANNED":
            print("  [PASS] Request routed correctly to PLANNED mode.")
        else:
            print("  [WARNING] Router did not classify prompt as PLANNED. Continuing anyway...")

        # B. Verify first WAITING_APPROVAL (for create_directory)
        if response1.metadata.get("confirmation_required") is True:
            action_id_1 = response1.metadata.get("pending_action_id")
            tool_name_1 = response1.metadata.get("tool_name")
            print(f"  [PASS] First step suspended on confirmation. Tool: {tool_name_1}, PendingAction ID: {action_id_1}")
            if tool_name_1 != "create_directory":
                print(f"  [FAIL] Expected first tool to be 'create_directory', got '{tool_name_1}'")
                failures += 1
        else:
            print(f"  [FAIL] Expected first step confirmation suspension, got text: '{response1.text}'")
            shutil.rmtree(temp_dir)
            sys.exit(1)

        # Verify folder doesn't exist yet
        if not target_folder.exists():
            print("  [PASS] Target folder does not exist yet before first approval.")
        else:
            print("  [FAIL] Target folder exists before first approval.")
            failures += 1

        # C. Approve first action (create directory)
        print("\n2. Approving first action (create_directory)...")
        approval_manager.approve(action_id_1)
        print("  [PASS] First action approved.")

        # D. Resume plan execution (expects second WAITING_APPROVAL for write_text_file)
        print("\n3. Resuming plan execution...")
        response2 = controller.process_request(request, approval_action_id=action_id_1)

        if response2.metadata.get("confirmation_required") is True:
            action_id_2 = response2.metadata.get("pending_action_id")
            tool_name_2 = response2.metadata.get("tool_name")
            print(f"  [PASS] Second step suspended on confirmation. Tool: {tool_name_2}, PendingAction ID: {action_id_2}")
            if tool_name_2 != "write_text_file":
                print(f"  [FAIL] Expected second tool to be 'write_text_file', got '{tool_name_2}'")
                failures += 1
        else:
            print(f"  [FAIL] Expected second step confirmation suspension, got text: '{response2.text}'")
            failures += 1
            action_id_2 = None

        # Verify folder exists now, but file doesn't exist yet
        if target_folder.exists() and target_folder.is_dir():
            print("  [PASS] Directory exists after first approved resumption.")
        else:
            print("  [FAIL] Directory does not exist after first approved resumption.")
            failures += 1

        if not target_file.exists():
            print("  [PASS] File todo.txt does not exist yet before second approval.")
        else:
            print("  [FAIL] File todo.txt exists before second approval.")
            failures += 1

        if action_id_2:
            # E. Approve second action (write text file)
            print("\n4. Approving second action (write_text_file)...")
            approval_manager.approve(action_id_2)
            print("  [PASS] Second action approved.")

            # F. Resume plan execution again (expects plan completion and final synthesis)
            print("\n5. Resuming plan execution...")
            response3 = controller.process_request(request, approval_action_id=action_id_2)

            # Verify file exists now and content is correct
            if target_file.exists() and target_file.read_text(encoding="utf-8") == "Buy milk.":
                print("  [PASS] File todo.txt exists with expected content: 'Buy milk.'")
            elif target_file.exists() and "buy milk" in target_file.read_text(encoding="utf-8").lower():
                print(f"  [PASS] File todo.txt exists with semantic content: '{target_file.read_text(encoding='utf-8')}'")
            else:
                content = target_file.read_text(encoding="utf-8") if target_file.exists() else "None"
                print(f"  [FAIL] File todo.txt checking failed. Content: '{content}'")
                failures += 1

            # Verify final response
            if response3.text:
                print(f"  [PASS] Final plan completion response: '{response3.text}'")
            else:
                print("  [FAIL] Empty or invalid final response on plan completion.")
                failures += 1

    finally:
        # Clean up isolated diagnostic folder
        print("\nCleaning up temp diagnostic folders...")
        shutil.rmtree(temp_dir)
        print("  [PASS] Cleanup complete.")

    print("\n-------------------------------------------")
    if failures == 0:
        print("DIAGNOSTIC STATUS: PASS")
    else:
        print(f"DIAGNOSTIC STATUS: FAIL ({failures} failures)")
        sys.exit(1)


if __name__ == "__main__":
    run_diagnostic()
