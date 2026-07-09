"""Unit tests for the Controlled Action Approval Runtime."""

import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
import pytest

from app.approval.models import PendingAction, PendingActionStatus
from app.approval.repository import SQLiteApprovalRepository
from app.approval.manager import ApprovalManager
from app.approval.policy import requires_approval, generate_approval_reason
from app.approval.cli import prompt_user_approval
from app.tools.base import BaseTool
from app.tools.models import ToolPermission, ToolResult
from app.tools.registry import ToolRegistry
from app.tools.executor import ToolExecutor
from app.agent.models import ToolCall, AgentRequest, AgentResponse
from app.agent.runner import AgentRunner
from app.ai.manager import LLMManager
from app.ai.parser import ResponseParser
from app.core.exceptions import ApprovalError, ApprovalPersistenceError
from app.planning.models import TaskPlan, PlanStep, StepType, StepStatus, PlanStatus, StepObservation
from app.planning.executor import TaskExecutor
from app.planning.validator import PlanValidator


# Harmless CONFIRMATION tool for tests/diagnostics
class RecordConfirmationActionTool(BaseTool):
    """Harmless confirmation tool for diagnostic verification."""

    def __init__(self, recorder: list | None = None) -> None:
        self.recorder = recorder if recorder is not None else []

    @property
    def name(self) -> str:
        return "record_confirmation_action"

    @property
    def description(self) -> str:
        return "A harmless confirmation tool that appends inputs to a diagnostic recorder list."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.CONFIRMATION

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {
                        "type": "string",
                        "description": "Value to append to the in-memory recorder."
                    }
                },
                "required": ["value"]
            }
        }

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        val = kwargs.get("value", "")
        self.recorder.append(val)
        return {"status": "success", "recorded_value": val}


# Harmless RESTRICTED tool for tests/diagnostics
class HarmlessRestrictedTool(BaseTool):
    """Harmless restricted tool for diagnostic verification."""

    @property
    def name(self) -> str:
        return "harmless_restricted_tool"

    @property
    def description(self) -> str:
        return "A harmless restricted tool for checking blocked scenarios."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.RESTRICTED

    def get_schema(self) -> Dict[str, Any]:
        return {"name": self.name, "description": self.description, "parameters": {"type": "object", "properties": {}}}

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        return {"status": "restricted_executed"}


# Harmless SAFE tool for tests/diagnostics
class HarmlessSafeTool(BaseTool):
    """Harmless safe tool for diagnostic verification."""

    @property
    def name(self) -> str:
        return "harmless_safe_tool"

    @property
    def description(self) -> str:
        return "A harmless safe tool for checking normal scenarios."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.SAFE

    def get_schema(self) -> Dict[str, Any]:
        return {"name": self.name, "description": self.description, "parameters": {"type": "object", "properties": {}}}

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        return {"status": "safe_executed"}


# ----------------------------------------------------
# 1. PendingAction Domain Tests
# ----------------------------------------------------

def test_pending_action_immutability():
    now = datetime.now(timezone.utc)
    args = {"path": "C:\\test"}
    action = PendingAction(
        action_id="act_123",
        tool_name="test_tool",
        arguments=args,
        permission_level=ToolPermission.CONFIRMATION,
        status=PendingActionStatus.PENDING,
        created_at=now,
        expires_at=now + timedelta(seconds=120),
        reason="test"
    )
    
    # Verify values are correctly set
    assert action.action_id == "act_123"
    assert action.tool_name == "test_tool"
    assert action.arguments == args
    
    # Verify arguments list/dict are defensively copied (so modifying original doesn't affect class)
    args["path"] = "modified"
    assert action.arguments["path"] == "C:\\test"

    # Verify that trying to modify field raises exception (frozen=True)
    with pytest.raises(Exception):
        action.tool_name = "new_name"


def test_pending_action_timezone_validation():
    # Naive datetime must raise ValueError
    naive = datetime.now()
    aware = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="All datetime fields must be timezone-aware"):
        PendingAction(
            action_id="act_123",
            tool_name="test_tool",
            arguments={},
            permission_level=ToolPermission.CONFIRMATION,
            status=PendingActionStatus.PENDING,
            created_at=naive,
            expires_at=aware,
            reason="test"
        )


# ----------------------------------------------------
# 2. SQLite Repository Tests
# ----------------------------------------------------

def test_repository_lifecycle(tmp_path):
    db_file = tmp_path / "test_approvals.db"
    repo = SQLiteApprovalRepository(database_path=db_file)
    
    now = datetime.now(timezone.utc)
    action = PendingAction(
        action_id="act_1",
        tool_name="test_tool",
        arguments={"x": [1, 2, {"y": 3}]},
        permission_level=ToolPermission.CONFIRMATION,
        status=PendingActionStatus.PENDING,
        created_at=now,
        expires_at=now + timedelta(seconds=120),
        reason="reason text",
        metadata={"sess": "abc"}
    )
    
    # 1. Add and get
    repo.add(action)
    fetched = repo.get("act_1")
    assert fetched is not None
    assert fetched.action_id == "act_1"
    assert fetched.tool_name == "test_tool"
    assert fetched.arguments == {"x": [1, 2, {"y": 3}]}
    assert fetched.status == PendingActionStatus.PENDING
    
    # 2. Status update
    repo.update_status("act_1", PendingActionStatus.APPROVED)
    assert repo.get("act_1").status == PendingActionStatus.APPROVED

    # 3. List pending
    repo.add(PendingAction(
        action_id="act_2",
        tool_name="test_tool",
        arguments={},
        permission_level=ToolPermission.CONFIRMATION,
        status=PendingActionStatus.PENDING,
        created_at=now,
        expires_at=now + timedelta(seconds=120),
        reason="test"
    ))
    pending = repo.list_pending()
    assert len(pending) == 1
    assert pending[0].action_id == "act_2"

    # 4. Persistence across reconstruction
    repo2 = SQLiteApprovalRepository(database_path=db_file)
    fetched2 = repo2.get("act_1")
    assert fetched2 is not None
    assert fetched2.status == PendingActionStatus.APPROVED

    # 5. Atomic consume
    assert repo2.atomic_consume("act_1") is True
    assert repo2.get("act_1").status == PendingActionStatus.EXECUTED
    # Twice fails
    assert repo2.atomic_consume("act_1") is False


def test_repository_corrupted_json(tmp_path):
    db_file = tmp_path / "test_corrupted.db"
    repo = SQLiteApprovalRepository(database_path=db_file)
    
    now = datetime.now(timezone.utc)
    action = PendingAction(
        action_id="act_1",
        tool_name="test_tool",
        arguments={"x": 1},
        permission_level=ToolPermission.CONFIRMATION,
        status=PendingActionStatus.PENDING,
        created_at=now,
        expires_at=now + timedelta(seconds=120),
        reason="test"
    )
    repo.add(action)

    # Corrupt the JSON inside DB directly
    import sqlite3
    conn = sqlite3.connect(str(db_file))
    conn.execute("UPDATE pending_actions SET arguments = 'invalid json {', metadata = 'corrupted' WHERE action_id = 'act_1'")
    conn.commit()
    conn.close()

    # Load should fallback safely and not crash
    fetched = repo.get("act_1")
    assert fetched is not None
    assert fetched.arguments == {}
    assert fetched.metadata == {}


# ----------------------------------------------------
# 3. ApprovalManager Tests
# ----------------------------------------------------

def test_manager_operations(tmp_path):
    repo = SQLiteApprovalRepository(database_path=tmp_path / "db.sqlite")
    # Using small expiration for test
    manager = ApprovalManager(repository=repo, timeout_seconds=1)

    # Create
    action = manager.create_pending_action(
        tool_name="test_tool",
        arguments={"a": 1},
        permission_level=ToolPermission.CONFIRMATION,
        reason="test"
    )
    assert action.status == PendingActionStatus.PENDING

    # Approve
    manager.approve(action.action_id)
    assert manager.get(action.action_id).status == PendingActionStatus.APPROVED

    # Approve already approved/non-pending raises
    with pytest.raises(ApprovalError):
        manager.approve(action.action_id)

    # Exclude replay / Consume approved
    manager.consume_approved_action(action.action_id, "test_tool", {"a": 1})
    assert manager.get(action.action_id).status == PendingActionStatus.EXECUTED

    # Consume twice blocks
    with pytest.raises(ApprovalError, match="Replay blocked"):
        manager.consume_approved_action(action.action_id, "test_tool", {"a": 1})


def test_manager_rejection(tmp_path):
    repo = SQLiteApprovalRepository(database_path=tmp_path / "db.sqlite")
    manager = ApprovalManager(repository=repo, timeout_seconds=120)

    action = manager.create_pending_action(
        tool_name="test_tool",
        arguments={"a": 1},
        permission_level=ToolPermission.CONFIRMATION,
        reason="test"
    )
    manager.reject(action.action_id)
    assert manager.get(action.action_id).status == PendingActionStatus.REJECTED

    # Rejected action cannot be consumed
    with pytest.raises(ApprovalError, match="REJECTED"):
        manager.consume_approved_action(action.action_id, "test_tool", {"a": 1})


def test_manager_expiration(tmp_path):
    repo = SQLiteApprovalRepository(database_path=tmp_path / "db.sqlite")
    # 0.1s timeout
    manager = ApprovalManager(repository=repo, timeout_seconds=1)
    
    # We cheat the expires_at date in the DB to simulate timeout without sleeping
    action = manager.create_pending_action(
        tool_name="test_tool",
        arguments={"a": 1},
        permission_level=ToolPermission.CONFIRMATION,
        reason="test"
    )
    
    # Manually modify expiration in db
    import sqlite3
    conn = sqlite3.connect(str(tmp_path / "db.sqlite"))
    past_time = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    conn.execute("UPDATE pending_actions SET expires_at = ? WHERE action_id = ?", (past_time, action.action_id))
    conn.commit()
    conn.close()

    # Getting action lazy-expires it
    fetched = manager.get(action.action_id)
    assert fetched.status == PendingActionStatus.EXPIRED

    # Cannot approve expired
    with pytest.raises(ApprovalError, match="expired"):
        manager.approve(action.action_id)


def test_manager_validation_payload_mismatch(tmp_path):
    repo = SQLiteApprovalRepository(database_path=tmp_path / "db.sqlite")
    manager = ApprovalManager(repository=repo, timeout_seconds=120)

    # Test tool name mismatch
    action1 = manager.create_pending_action(
        tool_name="test_tool",
        arguments={"a": 1, "nested": {"x": [1, 2]}},
        permission_level=ToolPermission.CONFIRMATION,
        reason="test"
    )
    manager.approve(action1.action_id)
    with pytest.raises(ApprovalError, match="tool name does not match"):
        manager.consume_approved_action(action1.action_id, "different_tool", {"a": 1, "nested": {"x": [1, 2]}})
    assert manager.get(action1.action_id).status == PendingActionStatus.FAILED

    # Test arguments mismatch
    action2 = manager.create_pending_action(
        tool_name="test_tool",
        arguments={"a": 1, "nested": {"x": [1, 2]}},
        permission_level=ToolPermission.CONFIRMATION,
        reason="test"
    )
    manager.approve(action2.action_id)
    with pytest.raises(ApprovalError, match="arguments do not match"):
        manager.consume_approved_action(action2.action_id, "test_tool", {"a": 1, "nested": {"x": [1, 3]}})
    assert manager.get(action2.action_id).status == PendingActionStatus.FAILED


# ----------------------------------------------------
# 4. ToolExecutor Tests
# ----------------------------------------------------

def test_tool_executor_routing(tmp_path):
    registry = ToolRegistry()
    safe_tool = HarmlessSafeTool()
    restricted_tool = HarmlessRestrictedTool()
    conf_tool = RecordConfirmationActionTool()
    registry.register(safe_tool)
    registry.register(restricted_tool)
    registry.register(conf_tool)

    repo = SQLiteApprovalRepository(database_path=tmp_path / "db.sqlite")
    manager = ApprovalManager(repository=repo)
    executor = ToolExecutor(registry, approval_manager=manager)

    # 1. SAFE executes directly
    res_safe = executor.execute(ToolCall(tool_name="harmless_safe_tool", arguments={}))
    assert res_safe.success is True
    assert res_safe.output == {"status": "safe_executed"}

    # 2. RESTRICTED always blocked
    res_rest = executor.execute(ToolCall(tool_name="harmless_restricted_tool", arguments={}))
    assert res_rest.success is False
    assert "restricted" in res_rest.error

    # 3. CONFIRMATION creates pending action when no approval ID passed
    res_conf = executor.execute(ToolCall(tool_name="record_confirmation_action", arguments={"value": "test"}))
    assert res_conf.success is False
    assert res_conf.metadata.get("confirmation_required") is True
    action_id = res_conf.metadata.get("pending_action_id")
    assert action_id is not None
    
    # 4. Pending action executes after approval
    manager.approve(action_id)
    res_approved = executor.execute(
        ToolCall(tool_name="record_confirmation_action", arguments={"value": "test"}),
        approval_action_id=action_id
    )
    assert res_approved.success is True
    assert res_approved.output == {"status": "success", "recorded_value": "test"}

    # 5. Replay blocks execute twice
    res_replay = executor.execute(
        ToolCall(tool_name="record_confirmation_action", arguments={"value": "test"}),
        approval_action_id=action_id
    )
    assert res_replay.success is False
    assert "Replay blocked" in res_replay.error


# ----------------------------------------------------
# 5. CLI Presentation Flow Helper Tests
# ----------------------------------------------------

def test_cli_presentation_approved(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "y")
    assert prompt_user_approval("tool_name", "reason", {"a": 1}) is True

    monkeypatch.setattr("builtins.input", lambda _: "yes")
    assert prompt_user_approval("tool_name", "reason", {"a": 1}) is True


def test_cli_presentation_rejected(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "n")
    assert prompt_user_approval("tool_name", "reason", {"a": 1}) is False

    monkeypatch.setattr("builtins.input", lambda _: "")
    assert prompt_user_approval("tool_name", "reason", {"a": 1}) is False

    monkeypatch.setattr("builtins.input", lambda _: "arbitrary")
    assert prompt_user_approval("tool_name", "reason", {"a": 1}) is False


def test_cli_presentation_interrupted(monkeypatch):
    def mock_interrupt(_):
        raise KeyboardInterrupt()
    monkeypatch.setattr("builtins.input", mock_interrupt)
    assert prompt_user_approval("tool_name", "reason", {"a": 1}) is False
