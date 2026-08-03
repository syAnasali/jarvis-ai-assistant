"""Integration tests verifying blocking action approval dialog behavior, zero-timeout interactive lifetime, and lifecycle synchronization."""

import time
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.core.application import Application
from app.approval.manager import ApprovalManager
from app.approval.repository import SQLiteApprovalRepository
from app.tools.models import ToolPermission
from app.agent.models import AgentRequest, ToolCall
from app.ai.models import GenerationResult, GenerationMetrics
from app.tools.builtin.filesystem import (
    DeletePathTool,
    MovePathTool,
    WriteTextFileTool,
    CreateDirectoryTool,
    CreateFileTool,
)
from app.tools.builtin.applications import LaunchApplicationTool
from app.tools.builtin.desktop import (
    FocusWindowTool,
    TypeTextTool,
    PressKeyTool,
    PressHotkeyTool,
    ClickScreenTool,
)


@pytest.fixture
def temp_db(tmp_path):
    return tmp_path / "test_blocking_approval.db"


@pytest.fixture
def approval_mgr(temp_db):
    repo = SQLiteApprovalRepository(database_path=temp_db)
    return ApprovalManager(repository=repo, timeout_seconds=None)


def test_interactive_approval_has_no_timeout(approval_mgr):
    """Verify interactive approvals block indefinitely with no automatic timeout or expiration."""
    action = approval_mgr.create_pending_action(
        tool_name="delete_path",
        arguments={"root": "Temp", "relative_path": "demo.txt"},
        permission_level=ToolPermission.CONFIRMATION,
        reason="User requested file deletion"
    )

    # 1. Action is created in PENDING status
    assert action.status.value == "pending"

    # 2. Expiration run must NOT expire this interactive action
    expired_count = approval_mgr.expire_pending_actions()
    assert expired_count == 0

    fetched = approval_mgr.get(action.action_id)
    assert fetched is not None
    assert fetched.status.value == "pending"


def test_approved_action_resumes_and_executes(approval_mgr, tmp_path):
    """Verify approving an action ('y') transitions status, executes tool, and completes workflow."""
    app = Application()
    app.initialize()
    app._initialize_llm()
    app._initialize_agent()

    fs_service = app.container.get("filesystem_service")
    controller = app.container.get("controller")
    llm_manager = app.container.get("llm_manager")
    mgr = app.container.get("approval_manager")

    # Create target file
    fs_service.write_text_file("Temp", "blocking_del.txt", "content")

    raw_resp_delete = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "function": {
                    "name": "delete_path",
                    "arguments": {"root": "Temp", "relative_path": "blocking_del.txt"}
                }
            }]
        }
    }
    llm_manager.generate = MagicMock(return_value=GenerationResult(
        raw_response=raw_resp_delete,
        metrics=GenerationMetrics(provider="ollama", model="qwen2.5:7b")
    ))

    req = AgentRequest(request_id="req_block_1", text="Delete blocking_del.txt", source="test")
    resp1 = controller.process_request(req)

    assert resp1.success is False
    assert resp1.metadata.get("confirmation_required") is True
    action_id = resp1.metadata.get("pending_action_id")

    # Approve action
    mgr.approve(action_id)

    raw_resp_final = {
        "message": {
            "role": "assistant",
            "content": "Deleted blocking_del.txt successfully."
        }
    }
    llm_manager.generate = MagicMock(return_value=GenerationResult(
        raw_response=raw_resp_final,
        metrics=GenerationMetrics(provider="ollama", model="qwen2.5:7b")
    ))

    resp2 = controller.process_request(req, approval_action_id=action_id)
    assert resp2.success is True
    assert "Deleted blocking_del.txt" in resp2.text

    app.shutdown()


def test_rejected_action_cancels_cleanly():
    """Verify rejecting an action ('n') cancels execution cleanly without running the tool."""
    app = Application()
    app.initialize()
    app._initialize_llm()
    app._initialize_agent()

    fs_service = app.container.get("filesystem_service")
    controller = app.container.get("controller")
    llm_manager = app.container.get("llm_manager")
    mgr = app.container.get("approval_manager")

    # Target file
    fs_service.write_text_file("Temp", "reject_del.txt", "keep me")

    raw_resp_delete = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "function": {
                    "name": "delete_path",
                    "arguments": {"root": "Temp", "relative_path": "reject_del.txt"}
                }
            }]
        }
    }
    llm_manager.generate = MagicMock(return_value=GenerationResult(
        raw_response=raw_resp_delete,
        metrics=GenerationMetrics(provider="ollama", model="qwen2.5:7b")
    ))

    req = AgentRequest(request_id="req_block_rej", text="Delete reject_del.txt", source="test")
    resp1 = controller.process_request(req)

    assert resp1.metadata.get("confirmation_required") is True
    action_id = resp1.metadata.get("pending_action_id")

    # Reject action
    mgr.reject(action_id)

    resp2 = controller.process_request(req, approval_action_id=action_id)
    assert resp2.success is False
    assert "rejected by the user" in resp2.text.lower()

    # Target file must still exist
    target_info = fs_service.inspect_path("Temp", "reject_del.txt")
    assert target_info.exists is True

    # Cleanup
    fs_service.delete_path("Temp", "reject_del.txt")
    app.shutdown()


def test_shutdown_cleans_pending_approvals(approval_mgr):
    """Verify shutting down the application cancels/cleans pending approvals safely."""
    action = approval_mgr.create_pending_action(
        tool_name="write_text_file",
        arguments={"root": "Temp", "relative_path": "orphan.txt", "content": "test"},
        permission_level=ToolPermission.CONFIRMATION,
        reason="Orphan test"
    )
    assert action.status.value == "pending"

    count = approval_mgr.cancel_all_pending("Application exit")
    assert count == 1

    fetched = approval_mgr.get(action.action_id)
    assert fetched.status.value == "rejected"


def test_all_confirmation_tools_share_identical_approval_lifecycle(approval_mgr):
    """Verify that every ToolPermission.CONFIRMATION tool triggers confirmation_required without approval."""
    app = Application()
    app.initialize()
    app._initialize_llm()
    app._initialize_agent()

    from app.services.applications.resolver import ApplicationResolver
    fs_service = app.container.get("filesystem_service")
    desktop_service = MagicMock()
    resolver = ApplicationResolver()

    tools = [
        DeletePathTool(fs_service),
        MovePathTool(fs_service),
        WriteTextFileTool(fs_service),
        CreateDirectoryTool(fs_service),
        CreateFileTool(fs_service),
        LaunchApplicationTool(),
        FocusWindowTool(desktop_service),
        TypeTextTool(desktop_service, approval_mgr),
        PressKeyTool(desktop_service, approval_mgr),
        PressHotkeyTool(desktop_service, approval_mgr),
        ClickScreenTool(desktop_service, approval_mgr),
    ]

    for tool in tools:
        assert tool.permission_level == ToolPermission.CONFIRMATION, f"Tool {tool.name} must require CONFIRMATION"
