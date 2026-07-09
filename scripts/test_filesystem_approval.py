"""Diagnostic script to verify filesystem approval flows and replay protection."""

import os
import shutil
import tempfile
import sys
from pathlib import Path

from app.services.filesystem.policy import FilesystemPolicy
from app.services.filesystem.resolver import FilesystemResolver
from app.services.filesystem.service import FilesystemService
from app.tools.builtin.filesystem import WriteTextFileTool, DeletePathTool
from app.tools.registry import ToolRegistry
from app.tools.executor import ToolExecutor
from app.agent.models import ToolCall
from app.approval.repository import SQLiteApprovalRepository
from app.approval.manager import ApprovalManager
from app.core.exceptions import ToolExecutionError


def run_diagnostics() -> bool:
    print("=== Running Filesystem Action Approval Diagnostics ===")
    
    # Setup isolated temporary roots
    temp_dir = Path(tempfile.mkdtemp())
    custom_roots = {
        "desktop": temp_dir / "Desktop",
        "documents": temp_dir / "Documents",
        "downloads": temp_dir / "Downloads",
        "workspace": temp_dir / "Workspace",
    }
    for p in custom_roots.values():
        p.mkdir(parents=True, exist_ok=True)

    success = True
    try:
        policy = FilesystemPolicy(custom_roots=custom_roots)
        resolver = FilesystemResolver(policy)
        service = FilesystemService(policy, resolver)

        # Setup SQLite Database Approval Repository and ApprovalManager
        db_file = custom_roots["workspace"] / "test_approval.db"
        repo = SQLiteApprovalRepository(database_path=db_file)
        manager = ApprovalManager(repository=repo, timeout_seconds=10)

        registry = ToolRegistry()
        registry.register(WriteTextFileTool(service))
        registry.register(DeletePathTool(service))
        executor = ToolExecutor(registry, manager)

        target_file = custom_roots["desktop"] / "notes.txt"

        # PART 1: Write File Approval Flow
        print("\nPart 1: Write text file approval verification...")
        
        # 1. Trigger write tool call (without approval ID)
        tc_write = ToolCall(
            tool_name="write_text_file",
            arguments={"root": "desktop", "relative_path": "notes.txt", "content": "approved content"},
        )
        res1 = executor.execute(tc_write)
        if res1.success is False and res1.metadata.get("confirmation_required") is True:
            print("  [PASS] Tool call correctly suspended on confirmation.")
        else:
            print(f"  [FAIL] Suspense check failed. Res: {res1}")
            success = False

        pending_id = res1.metadata.get("pending_action_id")
        if not target_file.exists():
            print("  [PASS] File is correctly absent before approval.")
        else:
            print("  [FAIL] File exists before approval.")
            success = False

        # 2. Approve and execute
        manager.approve(pending_id)
        res2 = executor.execute(tc_write, approval_action_id=pending_id)
        if res2.success is True:
            print("  [PASS] Executing with approved action succeeded.")
        else:
            print(f"  [FAIL] Approved execution failed: {res2.error}")
            success = False

        if target_file.exists() and target_file.read_text(encoding="utf-8") == "approved content":
            print("  [PASS] File created and content is correct.")
        else:
            print("  [FAIL] File content checking failed.")
            success = False

        # 3. Replay prevention
        res3 = executor.execute(tc_write, approval_action_id=pending_id)
        if res3.success is False and "Replay blocked" in res3.error:
            print("  [PASS] Replay blocked duplicate execution successfully.")
        else:
            print(f"  [FAIL] Replay check failed: {res3}")
            success = False


        # PART 2: Recursive Deletion Approval Flow
        print("\nPart 2: Recursive deletion approval verification...")
        
        # Setup directory to delete
        target_dir = custom_roots["desktop"] / "folder_to_delete"
        target_dir.mkdir()
        (target_dir / "child.txt").write_text("child")

        tc_delete = ToolCall(
            tool_name="delete_path",
            arguments={"root": "desktop", "relative_path": "folder_to_delete", "recursive": True},
        )

        # 1. Trigger delete tool call
        res_del1 = executor.execute(tc_delete)
        if res_del1.success is False and res_del1.metadata.get("confirmation_required") is True:
            print("  [PASS] Deletion tool call correctly suspended on confirmation.")
        else:
            print(f"  [FAIL] Deletion suspense failed. Res: {res_del1}")
            success = False

        del_pending_id = res_del1.metadata.get("pending_action_id")
        if target_dir.exists():
            print("  [PASS] Directory correctly exists before approval.")
        else:
            print("  [FAIL] Directory was deleted prematurely.")
            success = False

        # 2. Approve and delete
        manager.approve(del_pending_id)
        res_del2 = executor.execute(tc_delete, approval_action_id=del_pending_id)
        if res_del2.success is True:
            print("  [PASS] Deletion executed with approved action successfully.")
        else:
            print(f"  [FAIL] Approved deletion failed: {res_del2.error}")
            success = False

        if not target_dir.exists():
            print("  [PASS] Directory was successfully deleted.")
        else:
            print("  [FAIL] Directory still exists after approval execution.")
            success = False

        # 3. Replay prevention for deletion
        res_del3 = executor.execute(tc_delete, approval_action_id=del_pending_id)
        if res_del3.success is False and "Replay blocked" in res_del3.error:
            print("  [PASS] Replay blocked duplicate deletion successfully.")
        else:
            print(f"  [FAIL] Replay check on deletion failed: {res_del3}")
            success = False

    finally:
        # Clean up diagnostic data
        shutil.rmtree(temp_dir)

    print("\n==========================================================")
    if success:
        print("DIAGNOSTICS STATUS: PASS")
    else:
        print("DIAGNOSTICS STATUS: FAIL")
    print("==========================================================")
    return success


if __name__ == "__main__":
    ok = run_diagnostics()
    sys.exit(0 if ok else 1)
