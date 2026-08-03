"""Unit tests for all ToolPermission.CONFIRMATION tools verifying identical approval lifecycle."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from app.tools.models import ToolPermission
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry
from app.agent.models import ToolCall
from app.approval.manager import ApprovalManager
from app.approval.repository import SQLiteApprovalRepository
from app.services.filesystem.policy import FilesystemPolicy
from app.services.filesystem.resolver import FilesystemResolver
from app.services.filesystem.service import FilesystemService
from app.services.desktop.policy import DesktopPolicy
from app.services.desktop.resolver import DesktopResolver
from app.services.desktop.service import DesktopService
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
    return tmp_path / "test_approval.db"


@pytest.fixture
def approval_mgr(temp_db):
    repo = SQLiteApprovalRepository(database_path=temp_db)
    return ApprovalManager(repository=repo)


@pytest.fixture
def fs_service():
    policy = FilesystemPolicy()
    resolver = FilesystemResolver(policy)
    return FilesystemService(policy=policy, resolver=resolver)


@pytest.fixture
def desktop_service():
    mock_backend = MagicMock()
    mock_backend.get_foreground_window.return_value = (1001, "Test Window - Notepad", 1234, "notepad.exe")
    mock_backend.list_visible_windows.return_value = [(1001, "Test Window - Notepad", 1234, "notepad.exe")]
    mock_backend.focus_window.return_value = True
    mock_backend.send_text.return_value = True
    mock_backend.send_key.return_value = True
    mock_backend.send_hotkey.return_value = True
    mock_backend.click.return_value = True

    policy = DesktopPolicy()
    resolver = DesktopResolver()
    return DesktopService(policy=policy, resolver=resolver, backend=mock_backend)


def test_delete_path_approval_lifecycle(approval_mgr, fs_service):
    # Setup test file
    fs_service.write_text_file("Temp", "unit_delete_me.txt", "content")

    tool = DeletePathTool(service=fs_service)
    assert tool.permission_level == ToolPermission.CONFIRMATION

    registry = ToolRegistry()
    registry.register(tool)
    executor = ToolExecutor(registry=registry, approval_manager=approval_mgr)

    tc = ToolCall(tool_name="delete_path", arguments={"root": "Temp", "relative_path": "unit_delete_me.txt"})

    # 1. Unapproved execution -> suspended
    res1 = executor.execute(tc)
    assert res1.success is False
    assert res1.metadata.get("confirmation_required") is True
    action_id = res1.metadata.get("pending_action_id")
    assert action_id is not None

    # 2. Approve action
    approval_mgr.approve(action_id)

    # 3. Approved execution -> succeeds
    res2 = executor.execute(tc, approval_action_id=action_id)
    assert res2.success is True


def test_move_path_approval_lifecycle(approval_mgr, fs_service):
    fs_service.write_text_file("Temp", "unit_src.txt", "move me")

    tool = MovePathTool(service=fs_service)
    assert tool.permission_level == ToolPermission.CONFIRMATION

    registry = ToolRegistry()
    registry.register(tool)
    executor = ToolExecutor(registry=registry, approval_manager=approval_mgr)

    tc = ToolCall(tool_name="move_path", arguments={
        "source_root": "Temp",
        "source_relative_path": "unit_src.txt",
        "destination_root": "Temp",
        "destination_relative_path": "unit_dest.txt"
    })

    # 1. Unapproved execution -> suspended
    res1 = executor.execute(tc)
    assert res1.success is False
    assert res1.metadata.get("confirmation_required") is True
    action_id = res1.metadata.get("pending_action_id")

    # 2. Approve and execute
    approval_mgr.approve(action_id)
    res2 = executor.execute(tc, approval_action_id=action_id)
    assert res2.success is True

    # Cleanup
    fs_service.delete_path("Temp", "unit_dest.txt")


def test_write_text_file_approval_lifecycle(approval_mgr, fs_service):
    tool = WriteTextFileTool(service=fs_service)
    assert tool.permission_level == ToolPermission.CONFIRMATION

    registry = ToolRegistry()
    registry.register(tool)
    executor = ToolExecutor(registry=registry, approval_manager=approval_mgr)

    tc = ToolCall(tool_name="write_text_file", arguments={
        "root": "Temp",
        "relative_path": "unit_write_test.txt",
        "content": "Hello World"
    })

    # 1. Unapproved execution -> suspended
    res1 = executor.execute(tc)
    assert res1.success is False
    assert res1.metadata.get("confirmation_required") is True
    action_id = res1.metadata.get("pending_action_id")

    # 2. Approve and execute
    approval_mgr.approve(action_id)
    res2 = executor.execute(tc, approval_action_id=action_id)
    assert res2.success is True

    # Cleanup
    fs_service.delete_path("Temp", "unit_write_test.txt")


def test_create_directory_approval_lifecycle(approval_mgr, fs_service):
    tool = CreateDirectoryTool(service=fs_service)
    assert tool.permission_level == ToolPermission.CONFIRMATION

    registry = ToolRegistry()
    registry.register(tool)
    executor = ToolExecutor(registry=registry, approval_manager=approval_mgr)

    tc = ToolCall(tool_name="create_directory", arguments={"root": "Temp", "relative_path": "unit_new_folder"})

    # 1. Unapproved execution -> suspended
    res1 = executor.execute(tc)
    assert res1.success is False
    assert res1.metadata.get("confirmation_required") is True
    action_id = res1.metadata.get("pending_action_id")

    # 2. Approve and execute
    approval_mgr.approve(action_id)
    res2 = executor.execute(tc, approval_action_id=action_id)
    assert res2.success is True

    # Cleanup
    fs_service.delete_path("Temp", "unit_new_folder", recursive=True)


def test_create_file_approval_lifecycle(approval_mgr, fs_service):
    tool = CreateFileTool(service=fs_service)
    assert tool.permission_level == ToolPermission.CONFIRMATION

    registry = ToolRegistry()
    registry.register(tool)
    executor = ToolExecutor(registry=registry, approval_manager=approval_mgr)

    tc = ToolCall(tool_name="create_file", arguments={"root": "Temp", "relative_path": "unit_empty.txt"})

    # 1. Unapproved execution -> suspended
    res1 = executor.execute(tc)
    assert res1.success is False
    assert res1.metadata.get("confirmation_required") is True
    action_id = res1.metadata.get("pending_action_id")

    # 2. Approve and execute
    approval_mgr.approve(action_id)
    res2 = executor.execute(tc, approval_action_id=action_id)
    assert res2.success is True

    # Cleanup
    fs_service.delete_path("Temp", "unit_empty.txt")


def test_launch_application_approval_lifecycle(approval_mgr):
    tool = LaunchApplicationTool()
    assert tool.permission_level == ToolPermission.CONFIRMATION

    registry = ToolRegistry()
    registry.register(tool)
    executor = ToolExecutor(registry=registry, approval_manager=approval_mgr)

    tc = ToolCall(tool_name="launch_application", arguments={"application_id": "app_notepad"})

    res1 = executor.execute(tc)
    assert res1.success is False
    assert res1.metadata.get("confirmation_required") is True
    action_id = res1.metadata.get("pending_action_id")
    assert action_id is not None


def test_desktop_tools_approval_lifecycle(approval_mgr, desktop_service):
    tools = [
        FocusWindowTool(desktop_service),
        TypeTextTool(desktop_service, approval_mgr),
        PressKeyTool(desktop_service, approval_mgr),
        PressHotkeyTool(desktop_service, approval_mgr),
        ClickScreenTool(desktop_service, approval_mgr),
    ]

    registry = ToolRegistry()
    for t in tools:
        assert t.permission_level == ToolPermission.CONFIRMATION
        registry.register(t)

    executor = ToolExecutor(registry=registry, approval_manager=approval_mgr)

    # Test TypeTextTool confirmation
    tc_type = ToolCall(tool_name="type_text", arguments={"text": "hello"})
    res1 = executor.execute(tc_type)
    assert res1.success is False
    assert res1.metadata.get("confirmation_required") is True
    action_id = res1.metadata.get("pending_action_id")

    approval_mgr.approve(action_id)
    res2 = executor.execute(tc_type, approval_action_id=action_id)
    assert res2.success is True
