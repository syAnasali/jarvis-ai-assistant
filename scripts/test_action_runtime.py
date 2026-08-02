#!/usr/bin/env python3
"""Diagnostic script to verify Action Approval Runtime, multiple actions, double-ops, and safety."""

import sys
import os
import shutil
import time
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

# Add project root to python path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from app.core.application import Application
from app.agent.models import AgentRequest, ToolCall
from app.approval.models import PendingActionStatus
from app.core.exceptions import ToolValidationError, ApprovalError
from app.tools.builtin.filesystem import CreateFileTool, CreateDirectoryTool
from app.agent.metrics import AgentExecutionMetrics
from app.agent.runner import AgentRunResult
from app.tools.models import ToolPermission

def safe_print(msg: str):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'))

def run_diagnostics():
    safe_print("=== Starting E2E Action Approval Runtime Diagnostics ===")

    app = Application()
    app.initialize()
    try:
        app._initialize_llm()
    except Exception as e:
        safe_print(f"Notice: Ollama offline, mocking LLMManager: {e}")
        llm_manager = MagicMock()
        app.container.register("llm_manager", llm_manager)
    app._initialize_agent()

    approval_manager = app.container.get("approval_manager")

    # 1. Test "No Timeout" default behavior
    safe_print("\nTesting: No Timeout (Default)")
    action_no_timeout = approval_manager.create_pending_action(
        tool_name="create_file",
        arguments={"root": "desktop", "relative_path": "no_timeout.txt"},
        permission_level=ToolPermission.CONFIRMATION,
        reason="Test no timeout"
    )
    # Check that expiration is set far in the future
    days_to_expire = (action_no_timeout.expires_at - datetime.now(timezone.utc)).days
    safe_print(f"Action expires in {days_to_expire} days.")
    if days_to_expire < 365:
        safe_print("FAIL: Action has default timeout but should have no timeout (expiring far in future).")
        sys.exit(1)
    safe_print("PASS: Default action has no timeout.")

    # 2. Test Approve Action and Resume
    safe_print("\nTesting: Approve action")
    action_approve = approval_manager.create_pending_action(
        tool_name="create_file",
        arguments={"root": "desktop", "relative_path": "test_approve.txt"},
        permission_level=ToolPermission.CONFIRMATION,
        reason="Test approve action"
    )
    approval_manager.approve(action_approve.action_id)
    refreshed = approval_manager.get(action_approve.action_id)
    if refreshed.status != PendingActionStatus.APPROVED:
        safe_print(f"FAIL: Expected status APPROVED, got {refreshed.status}")
        sys.exit(1)
    safe_print("PASS: Action approved successfully.")

    # 3. Test Double Approval
    safe_print("\nTesting: Approve twice")
    try:
        approval_manager.approve(action_approve.action_id)
        safe_print("FAIL: Double approval did not raise ApprovalError.")
        sys.exit(1)
    except ApprovalError as e:
        safe_print(f"PASS: Double approval blocked: {e}")

    # 4. Test Reject Action
    safe_print("\nTesting: Reject action")
    action_reject = approval_manager.create_pending_action(
        tool_name="create_file",
        arguments={"root": "desktop", "relative_path": "test_reject.txt"},
        permission_level=ToolPermission.CONFIRMATION,
        reason="Test reject action"
    )
    approval_manager.reject(action_reject.action_id)
    refreshed = approval_manager.get(action_reject.action_id)
    if refreshed.status != PendingActionStatus.REJECTED:
        safe_print(f"FAIL: Expected status REJECTED, got {refreshed.status}")
        sys.exit(1)
    safe_print("PASS: Action rejected successfully.")

    # 5. Test Double Rejection
    safe_print("\nTesting: Reject twice")
    try:
        approval_manager.reject(action_reject.action_id)
        safe_print("FAIL: Double rejection did not raise ApprovalError.")
        sys.exit(1)
    except ApprovalError as e:
        safe_print(f"PASS: Double rejection blocked: {e}")

    # 6. Test Multiple Pending Actions
    safe_print("\nTesting: Multiple pending actions")
    action_m1 = approval_manager.create_pending_action(
        tool_name="create_file",
        arguments={"root": "desktop", "relative_path": "file1.txt"},
        permission_level=ToolPermission.CONFIRMATION,
        reason="Action 1"
    )
    action_m2 = approval_manager.create_pending_action(
        tool_name="create_file",
        arguments={"root": "desktop", "relative_path": "file2.txt"},
        permission_level=ToolPermission.CONFIRMATION,
        reason="Action 2"
    )
    if action_m1.action_id == action_m2.action_id:
        safe_print("FAIL: Multiple actions generated non-unique IDs.")
        sys.exit(1)
    safe_print("PASS: Multiple pending actions handled safely.")

    # 7. Test Filesystem execution after approval
    safe_print("\nTesting: Filesystem execution after approval")
    # Clean up file if it already exists
    policy = app.container.get("filesystem_service")._policy
    desktop_path = policy.get_root_path("desktop")
    test_file_path = desktop_path / "test_exec.txt"
    if test_file_path.exists():
        test_file_path.unlink()

    action_exec = approval_manager.create_pending_action(
        tool_name="create_file",
        arguments={"root": "desktop", "relative_path": "test_exec.txt"},
        permission_level=ToolPermission.CONFIRMATION,
        reason="Create execution file"
    )
    approval_manager.approve(action_exec.action_id)
    
    # Execute tool
    from app.tools.executor import ToolExecutor
    tool_executor = app.container.get("tool_executor")
    tool_call = ToolCall(tool_name="create_file", arguments={"root": "desktop", "relative_path": "test_exec.txt"})
    result = tool_executor.execute(tool_call, approval_action_id=action_exec.action_id)
    
    safe_print(f"Tool execution success: {result.success}")
    if not result.success:
        safe_print(f"FAIL: Tool execution failed: {result.error}")
        sys.exit(1)
    if not test_file_path.exists():
        safe_print("FAIL: File was not created by the approved execution.")
        sys.exit(1)
    safe_print("PASS: Filesystem execution succeeded after approval.")

    # Prevent duplicate execution of same action
    safe_print("\nTesting: Prevent duplicate execution")
    dup_result = tool_executor.execute(tool_call, approval_action_id=action_exec.action_id)
    if dup_result.success:
        safe_print("FAIL: Replay/duplicate execution succeeded.")
        sys.exit(1)
    safe_print(f"PASS: Replay/duplicate execution prevented: {dup_result.error}")

    # Clean up
    if test_file_path.exists():
        test_file_path.unlink()

    app.shutdown()
    safe_print("\n" + "=" * 60)
    safe_print("ALL ACTION RUNTIME DIAGNOSTICS PASSED SUCCESSFULLY!")
    safe_print("=" * 60)

if __name__ == "__main__":
    run_diagnostics()
