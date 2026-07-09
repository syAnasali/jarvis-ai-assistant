"""Unit tests for root-bounded filesystem capabilities, policies, and tools."""

import os
import shutil
import tempfile
from pathlib import Path
import pytest
from unittest.mock import MagicMock

from app.core.exceptions import (
    InvalidRootError,
    InvalidPathError,
    PathEscapeError,
    UnsupportedPathError,
    PathNotFoundError,
    PathAlreadyExistsError,
    TypeMismatchError,
    DirectoryNotEmptyError,
    BlockedExtensionError,
    ContentTooLargeError,
    ToolExecutionError,
)
from app.services.filesystem.policy import FilesystemPolicy
from app.services.filesystem.resolver import FilesystemResolver
from app.services.filesystem.service import FilesystemService
from app.services.filesystem.models import FilesystemTarget
from app.tools.builtin.filesystem import (
    InspectPathTool,
    ListDirectoryTool,
    CreateDirectoryTool,
    WriteTextFileTool,
    MovePathTool,
    DeletePathTool,
)
from app.tools.registry import ToolRegistry
from app.tools.executor import ToolExecutor
from app.tools.models import ToolPermission
from app.agent.models import ToolCall
from app.approval.models import PendingActionStatus
from app.config.settings import settings


@pytest.fixture
def temp_roots():
    """Create isolated temporary directories for filesystem roots."""
    temp_dir = Path(tempfile.mkdtemp())
    roots = {
        "desktop": temp_dir / "Desktop",
        "documents": temp_dir / "Documents",
        "downloads": temp_dir / "Downloads",
        "workspace": temp_dir / "Workspace",
    }
    for r in roots.values():
        r.mkdir(parents=True, exist_ok=True)
    yield roots
    shutil.rmtree(temp_dir)


@pytest.fixture
def policy(temp_roots):
    return FilesystemPolicy(custom_roots=temp_roots)


@pytest.fixture
def resolver(policy):
    return FilesystemResolver(policy)


@pytest.fixture
def service(policy, resolver):
    return FilesystemService(
        policy=policy,
        resolver=resolver,
        list_max_entries=10,
        write_max_chars=1000,
        relative_path_max_length=100,
    )


# =====================================================================
# FILESYSTEM POLICY TESTS
# =====================================================================

def test_policy_allowed_roots(policy, temp_roots):
    """Verify that logical roots are correctly mapped and registered."""
    roots = policy.get_roots()
    assert len(roots) == 4
    for key in ["desktop", "documents", "downloads", "workspace"]:
        assert key in roots
        assert roots[key] == temp_roots[key].resolve()


def test_policy_unknown_root(policy):
    """Verify that unknown roots are rejected."""
    assert policy.is_valid_root("unknown") is False
    assert policy.get_root_path("unknown") is None


def test_policy_blocked_extensions(policy):
    """Verify blocked script/executable extension checking."""
    assert policy.is_blocked_extension("test.exe") is True
    assert policy.is_blocked_extension("script.ps1") is True
    assert policy.is_blocked_extension("module.py") is True
    assert policy.is_blocked_extension("index.js") is True
    assert policy.is_blocked_extension("plain.txt") is False
    assert policy.is_blocked_extension("readme.md") is False


# =====================================================================
# FILESYSTEM TARGET TESTS
# =====================================================================

def test_target_metadata_immutability():
    """Verify that FilesystemTarget properties are read-only and metadata copy is frozen."""
    t = FilesystemTarget(
        root="desktop",
        relative_path="notes.txt",
        resolved_path=Path("C:/dummy/notes.txt"),
        exists=True,
        entry_type="FILE",
    )
    assert t.root == "desktop"
    assert t.relative_path == "notes.txt"
    
    meta = t.metadata
    meta["exists"] = False
    assert t.metadata["exists"] is True  # Metadata dict must be defensively copied


# =====================================================================
# FILESYSTEM RESOLVER PATH SECURITY TESTS
# =====================================================================

def test_resolver_valid_nested_resolution(resolver, temp_roots):
    """Verify valid nested resolution within allowed roots."""
    target = resolver.resolve("desktop", "invoices/notes.txt")
    assert target.root == "desktop"
    assert target.relative_path == "invoices/notes.txt"
    assert target.resolved_path == temp_roots["desktop"] / "invoices/notes.txt"
    assert target.exists is False
    assert target.entry_type == "MISSING"


def test_resolver_absolute_path_rejection(resolver):
    """Verify absolute paths are rejected."""
    with pytest.raises(InvalidPathError, match="cannot start with absolute"):
        resolver.resolve("desktop", "/absolute/path")
    with pytest.raises(InvalidPathError, match="cannot start with absolute"):
        resolver.resolve("desktop", "\\absolute\\path")


def test_resolver_drive_qualified_rejection(resolver):
    """Verify drive-qualified path patterns are rejected."""
    with pytest.raises(InvalidPathError, match="cannot contain drive-qualified"):
        resolver.resolve("desktop", "C:invoices/notes.txt")
    with pytest.raises(InvalidPathError, match="cannot contain drive-qualified"):
        resolver.resolve("desktop", "D:\\invoices")


def test_resolver_unc_rejection(resolver):
    """Verify UNC paths are rejected."""
    with pytest.raises(UnsupportedPathError, match="UNC and network paths"):
        resolver.resolve("desktop", "//server/share")
    with pytest.raises(UnsupportedPathError, match="UNC and network paths"):
        resolver.resolve("desktop", "\\\\server\\share")


def test_resolver_device_rejection(resolver):
    """Verify device paths are rejected."""
    with pytest.raises(UnsupportedPathError, match="Device paths"):
        resolver.resolve("desktop", "\\\\.\\PhysicalDrive0")
    with pytest.raises(UnsupportedPathError, match="Device paths"):
        resolver.resolve("desktop", "\\\\?\\C:\\")


def test_resolver_nul_byte_rejection(resolver):
    """Verify null bytes are strictly rejected."""
    with pytest.raises(InvalidPathError, match="null bytes"):
        resolver.resolve("desktop", "path\x00file.txt")


def test_resolver_traversal_escape_rejection(resolver, temp_roots):
    """Verify directory traversal outside trusted roots is caught."""
    with pytest.raises(PathEscapeError, match="outside root"):
        resolver.resolve("desktop", "../outside.txt")
    with pytest.raises(PathEscapeError, match="outside root"):
        resolver.resolve("desktop", "invoices/../../outside.txt")


def test_resolver_symlink_escape_rejection(resolver, temp_roots):
    """Verify traversal escapes using symlinks are caught."""
    # Create symlink pointing outside
    outside_dir = temp_roots["documents"]
    symlink_target = temp_roots["desktop"] / "escape_link"
    try:
        os.symlink(str(outside_dir), str(symlink_target), target_is_directory=True)
    except OSError:
        pytest.skip("Symlinks are not supported or user lacks permissions on Windows.")

    with pytest.raises(PathEscapeError, match="outside root"):
        resolver.resolve("desktop", "escape_link/file.txt")


# =====================================================================
# FILESYSTEM SERVICE OPERATIONS TESTS
# =====================================================================

def test_service_create_directory(service, temp_roots):
    """Verify directory creation is correct and idempotent."""
    assert service.create_directory("desktop", "invoices/2026") is True
    created_path = temp_roots["desktop"] / "invoices/2026"
    assert created_path.exists()
    assert created_path.is_dir()

    # Idempotence check
    assert service.create_directory("desktop", "invoices/2026") is True


def test_service_create_directory_file_collision(service, temp_roots):
    """Verify directory creation fails on existing files."""
    file_path = temp_roots["desktop"] / "dummy.txt"
    file_path.write_text("dummy")

    with pytest.raises(PathAlreadyExistsError):
        service.create_directory("desktop", "dummy.txt")


def test_service_write_text_file(service, temp_roots):
    """Verify UTF-8 atomic file writing with cleanup."""
    assert service.write_text_file("desktop", "notes.txt", "Hello World! 😊") is True
    file_path = temp_roots["desktop"] / "notes.txt"
    assert file_path.exists()
    assert file_path.read_text(encoding="utf-8") == "Hello World! 😊"


def test_service_write_text_file_blocked_extensions(service):
    """Verify blocked extension checks on write."""
    with pytest.raises(BlockedExtensionError):
        service.write_text_file("desktop", "script.exe", "content")
    with pytest.raises(BlockedExtensionError):
        service.write_text_file("desktop", "script.py", "content")


def test_service_write_text_file_oversized(service):
    """Verify content size checks on write."""
    oversized = "a" * 2000
    with pytest.raises(ContentTooLargeError):
        service.write_text_file("desktop", "big.txt", oversized)


def test_service_write_text_file_missing_parent(service):
    """Verify missing parent directories raise error on write."""
    with pytest.raises(PathNotFoundError):
        service.write_text_file("desktop", "nonexistent_dir/notes.txt", "content")


def test_service_list_directory(service, temp_roots):
    """Verify bounded and sorted non-recursive directory lists."""
    (temp_roots["desktop"] / "dir_b").mkdir()
    (temp_roots["desktop"] / "dir_a").mkdir()
    (temp_roots["desktop"] / "file_b.txt").write_text("b")
    (temp_roots["desktop"] / "file_a.txt").write_text("a")

    res = service.list_directory("desktop")
    entries = res["entries"]
    assert len(entries) == 4
    # Dirs first sorted case-insensitively
    assert entries[0]["name"] == "dir_a"
    assert entries[0]["entry_type"] == "DIRECTORY"
    assert entries[1]["name"] == "dir_b"
    assert entries[1]["entry_type"] == "DIRECTORY"
    # Files sorted case-insensitively
    assert entries[2]["name"] == "file_a.txt"
    assert entries[2]["entry_type"] == "FILE"
    assert entries[3]["name"] == "file_b.txt"
    assert entries[3]["entry_type"] == "FILE"


def test_service_move_path(service, temp_roots):
    """Verify safe path move actions with collision rejections."""
    # Write source
    (temp_roots["desktop"] / "src.txt").write_text("payload")
    
    assert service.move_path("desktop", "src.txt", "documents", "dest.txt") is True
    assert not (temp_roots["desktop"] / "src.txt").exists()
    assert (temp_roots["documents"] / "dest.txt").exists()
    assert (temp_roots["documents"] / "dest.txt").read_text() == "payload"


def test_service_move_path_collision(service, temp_roots):
    """Verify path move fails if destination already exists."""
    (temp_roots["desktop"] / "src.txt").write_text("src")
    (temp_roots["documents"] / "dest.txt").write_text("dest")

    with pytest.raises(PathAlreadyExistsError):
        service.move_path("desktop", "src.txt", "documents", "dest.txt")


def test_service_delete_path_file(service, temp_roots):
    """Verify file deletion works."""
    (temp_roots["desktop"] / "file.txt").write_text("payload")
    assert service.delete_path("desktop", "file.txt") is True
    assert not (temp_roots["desktop"] / "file.txt").exists()


def test_service_delete_path_empty_directory(service, temp_roots):
    """Verify empty directory deletion works."""
    (temp_roots["desktop"] / "folder").mkdir()
    assert service.delete_path("desktop", "folder") is True
    assert not (temp_roots["desktop"] / "folder").exists()


def test_service_delete_path_nonempty_directory_error(service, temp_roots):
    """Verify directory deletion raises DirectoryNotEmptyError without recursive flag."""
    (temp_roots["desktop"] / "folder").mkdir()
    (temp_roots["desktop"] / "folder/file.txt").write_text("payload")

    with pytest.raises(DirectoryNotEmptyError):
        service.delete_path("desktop", "folder")


def test_service_delete_path_recursive(service, temp_roots):
    """Verify recursive directory deletion works."""
    (temp_roots["desktop"] / "folder").mkdir()
    (temp_roots["desktop"] / "folder/file.txt").write_text("payload")

    assert service.delete_path("desktop", "folder", recursive=True) is True
    assert not (temp_roots["desktop"] / "folder").exists()


# =====================================================================
# FILESYSTEM TOOLS SCHEMA & PERMISSION TESTS
# =====================================================================

def test_filesystem_tools_schemas_and_permissions(service):
    """Verify schemas, parameters, and permission levels for filesystem tools."""
    inspect_tool = InspectPathTool(service)
    list_tool = ListDirectoryTool(service)
    create_tool = CreateDirectoryTool(service)
    write_tool = WriteTextFileTool(service)
    move_tool = MovePathTool(service)
    delete_tool = DeletePathTool(service)

    # Permission checks
    assert inspect_tool.permission_level == ToolPermission.SAFE
    assert list_tool.permission_level == ToolPermission.SAFE
    assert create_tool.permission_level == ToolPermission.CONFIRMATION
    assert write_tool.permission_level == ToolPermission.CONFIRMATION
    assert move_tool.permission_level == ToolPermission.CONFIRMATION
    assert delete_tool.permission_level == ToolPermission.CONFIRMATION

    # Argument validation schema check (no absolute path arguments)
    for tool in [inspect_tool, list_tool, create_tool, write_tool, move_tool, delete_tool]:
        schema = tool.get_schema()
        props = schema["parameters"]["properties"]
        assert "path" not in props
        assert "absolute_path" not in props
        assert "root" in props or "source_root" in props


def test_approval_integration_write_file_mutation(policy, resolver, service, temp_roots):
    """Verify that writing a file suspends on confirmation, and only executes on approval."""
    from app.tools.registry import ToolRegistry
    from app.tools.executor import ToolExecutor
    from app.approval.repository import SQLiteApprovalRepository
    from app.approval.manager import ApprovalManager

    # Use in-memory or temp SQLite DB
    db_file = temp_roots["workspace"] / "test_approval.db"
    repo = SQLiteApprovalRepository(database_path=db_file)
    manager = ApprovalManager(repository=repo, timeout_seconds=10)

    registry = ToolRegistry()
    registry.register(WriteTextFileTool(service))
    executor = ToolExecutor(registry, manager)

    target_file = temp_roots["desktop"] / "notes.txt"

    # 1. Mutation not executed before approval
    tc = ToolCall(tool_name="write_text_file", arguments={"root": "desktop", "relative_path": "notes.txt", "content": "hello"})
    res1 = executor.execute(tc)
    assert res1.success is False
    assert res1.metadata.get("confirmation_required") is True
    pending_id = res1.metadata.get("pending_action_id")
    assert pending_id is not None
    assert not target_file.exists()

    # 2. Rejection blocks mutation
    manager.reject(pending_id)
    res_rej = executor.execute(tc, approval_action_id=pending_id)
    assert res_rej.success is False
    assert "REJECTED" in res_rej.error or "authorization failed" in res_rej.error
    assert not target_file.exists()

    # 3. Expiration blocks mutation
    res2 = executor.execute(tc)
    pending_id2 = res2.metadata.get("pending_action_id")
    repo.update_status(pending_id2, PendingActionStatus.EXPIRED)
    res_exp = executor.execute(tc, approval_action_id=pending_id2)
    assert res_exp.success is False
    assert "EXPIRED" in res_exp.error or "authorization failed" in res_exp.error

    # 4. Content mismatch blocked
    res3 = executor.execute(tc)
    pending_id3 = res3.metadata.get("pending_action_id")
    manager.approve(pending_id3)
    tc_mismatched = ToolCall(tool_name="write_text_file", arguments={"root": "desktop", "relative_path": "notes.txt", "content": "mismatched"})
    res_mis = executor.execute(tc_mismatched, approval_action_id=pending_id3)
    assert res_mis.success is False
    assert "mismatch" in res_mis.error or "authorization failed" in res_mis.error
    assert not target_file.exists()

    # 5. Success executing approved action
    res4 = executor.execute(tc)
    pending_id4 = res4.metadata.get("pending_action_id")
    manager.approve(pending_id4)
    res_exec = executor.execute(tc, approval_action_id=pending_id4)
    assert res_exec.success is True
    assert target_file.exists()
    assert target_file.read_text(encoding="utf-8") == "hello"

    # 6. Replay blocks duplicate mutation
    res_rep = executor.execute(tc, approval_action_id=pending_id4)
    assert res_rep.success is False
    assert "Replay blocked" in res_rep.error or "authorization failed" in res_rep.error

