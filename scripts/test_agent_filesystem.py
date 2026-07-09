"""Diagnostic script for AgentController filesystem tool confirmation flow with real Ollama."""

import sys
import os
import shutil
import tempfile
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.application import Application
from app.agent.models import AgentRequest


def run_diagnostic():
    print("=== Agent Filesystem Confirmation Diagnostic ===")
    
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

    # Set up isolated temp directory and redirect policy's desktop root
    temp_dir = Path(tempfile.mkdtemp())
    isolated_desktop = temp_dir / "Desktop"
    isolated_desktop.mkdir(parents=True, exist_ok=True)
    
    # In-place redirect of the desktop root
    filesystem_service._policy._roots["desktop"] = isolated_desktop.resolve()
    print(f"Redirected desktop root to: {isolated_desktop.resolve()}")

    failures = 0
    target_folder = isolated_desktop / "jarvis-test"

    try:
        # 1. Start agent execution with user prompt
        print("\n1. Asking Jarvis to 'Create a folder called jarvis-test on my Desktop.'...")
        request = AgentRequest("req_agent_fs_create", "Create a folder called jarvis-test on my Desktop.", "terminal")
        response1 = controller.process_request(request)

        # Expect suspension
        if response1.metadata.get("confirmation_required") is True:
            action_id = response1.metadata.get("pending_action_id")
            tool_name = response1.metadata.get("tool_name")
            print(f"  [PASS] Agent suspended correctly. Tool: {tool_name}, PendingAction ID: {action_id}")
        else:
            print(f"  [FAIL] Expected suspension, got response: '{response1.text}'")
            shutil.rmtree(temp_dir)
            sys.exit(1)

        # Verify folder is absent before approval
        if not target_folder.exists():
            print("  [PASS] Folder is correctly absent before approval.")
        else:
            print("  [FAIL] Folder exists before approval.")
            failures += 1

        # 2. Approve action
        print("\n2. Approving action in database...")
        approval_manager.approve(action_id)
        print("  [PASS] Action approved.")

        # 3. Resume agent execution
        print("\n3. Resuming agent execution...")
        response2 = controller.process_request(request, approval_action_id=action_id)

        # Verify directory exists
        if target_folder.exists() and target_folder.is_dir():
            print("  [PASS] Folder exists and is a directory.")
        else:
            print("  [FAIL] Folder was not created after approval.")
            failures += 1

        # Verify final response is non-empty
        if response2.text:
            print(f"  [PASS] Final assistant response: '{response2.text}'")
        else:
            print("  [FAIL] Empty or invalid final assistant response.")
            failures += 1

    finally:
        # Clean up temp directories
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
