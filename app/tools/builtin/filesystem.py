import os
import fnmatch
from pathlib import Path
from typing import Any, Dict, Optional
from app.tools.base import BaseTool
from app.tools.models import ToolPermission
from app.core.exceptions import ToolExecutionError, FilesystemError
from app.services.filesystem.service import FilesystemService

# Sensitive filename denylist patterns
SENSITIVE_FILENAME_PATTERNS = [
    ".env",
    ".env.*",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    "service-account*.json",
    "*.pem",
    "*.key"
]

def is_sensitive_path(path_str: str) -> bool:
    """Checks if the resolved absolute path targets a denylisted sensitive file."""
    try:
        p = Path(path_str).name.lower()
        for pattern in SENSITIVE_FILENAME_PATTERNS:
            if fnmatch.fnmatch(p, pattern.lower()):
                return True
    except Exception:
        pass
    return False

def validate_and_resolve_path(path_str: str, expected_type: str | None = None) -> str:
    """Validates, expands, and resolves a path string safely.

    Args:
        path_str: The raw path string.
        expected_type: 'file', 'directory', or None.

    Returns:
        str: Safe resolved absolute path string.

    Raises:
        ToolExecutionError: If validation fails.
    """
    if not path_str or not isinstance(path_str, str):
        raise ToolExecutionError("Path must be a non-empty string.")

    if "\x00" in path_str:
        raise ToolExecutionError("Path contains invalid characters (null bytes).")

    try:
        expanded = os.path.expanduser(path_str)
        resolved = os.path.abspath(expanded)
    except Exception as e:
        raise ToolExecutionError(f"Failed to resolve path: {e}")

    if not os.path.exists(resolved):
        raise ToolExecutionError(f"Path does not exist: {path_str}")

    if expected_type == "file":
        if not os.path.isfile(resolved):
            raise ToolExecutionError(f"Path is not a regular file: {path_str}")
    elif expected_type == "directory":
        if not os.path.isdir(resolved):
            raise ToolExecutionError(f"Path is not a directory: {path_str}")

    # Check sensitive policy
    if is_sensitive_path(resolved):
        raise ToolExecutionError(f"Access to sensitive file blocked: {os.path.basename(resolved)}")

    return resolved



class InspectPathTool(BaseTool):
    """Tool to inspect metadata of a filesystem target path."""

    def __init__(self, service: Optional[FilesystemService] = None) -> None:
        """Initializes the InspectPathTool with an optional FilesystemService."""
        if service is None:
            from app.services.filesystem.policy import FilesystemPolicy
            from app.services.filesystem.resolver import FilesystemResolver
            policy = FilesystemPolicy()
            service = FilesystemService(policy, FilesystemResolver(policy))
        self._service = service

    @property
    def name(self) -> str:
        return "inspect_path"

    @property
    def description(self) -> str:
        return (
            "Inspect the metadata of a path under a logical root. Returns model-safe information "
            "such as existence, type (FILE or DIRECTORY), size in bytes, and last modified timestamp."
        )

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.SAFE

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "root": {
                        "type": "string",
                        "description": "The trusted logical root directory (e.g., 'desktop', 'documents', 'downloads', 'workspace')."
                    },
                    "relative_path": {
                        "type": "string",
                        "description": "The relative path to inspect within the logical root."
                    }
                },
                "required": ["root", "relative_path"]
            }
        }

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        root = kwargs.get("root")
        relative_path = kwargs.get("relative_path")
        
        try:
            target = self._service.inspect_path(root, relative_path)
            return target.metadata
        except FilesystemError as fe:
            raise ToolExecutionError(str(fe))
        except Exception as e:
            raise ToolExecutionError(f"Inspection failed: {e}")


class ListDirectoryTool(BaseTool):
    """Tool to list contents of a directory without recursion."""

    def __init__(self, service: Optional[FilesystemService] = None) -> None:
        """Initializes the ListDirectoryTool."""
        if service is None:
            from app.services.filesystem.policy import FilesystemPolicy
            from app.services.filesystem.resolver import FilesystemResolver
            policy = FilesystemPolicy()
            service = FilesystemService(policy, FilesystemResolver(policy))
        self._service = service

    @property
    def name(self) -> str:
        return "list_directory"

    @property
    def description(self) -> str:
        return (
            "List the contents of a directory under a logical root (directories first, then files, "
            "sorted alphabetically) without recursing. Returns name, type, and size."
        )

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.SAFE

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "root": {
                        "type": "string",
                        "description": "The trusted logical root directory (e.g., 'desktop', 'documents', 'downloads', 'workspace')."
                    },
                    "relative_path": {
                        "type": "string",
                        "description": "Optional relative subdirectory path inside the logical root to list. Defaults to the root directory itself."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Optional maximum number of entries to return."
                    }
                },
                "required": ["root"]
            }
        }

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        root = kwargs.get("root")
        relative_path = kwargs.get("relative_path")
        limit = kwargs.get("limit")

        try:
            return self._service.list_directory(root, relative_path, limit)
        except FilesystemError as fe:
            raise ToolExecutionError(str(fe))
        except Exception as e:
            raise ToolExecutionError(f"List directory failed: {e}")


class CreateDirectoryTool(BaseTool):
    """Tool to create a directory under a logical root."""

    def __init__(self, service: Optional[FilesystemService] = None) -> None:
        """Initializes the CreateDirectoryTool."""
        if service is None:
            from app.services.filesystem.policy import FilesystemPolicy
            from app.services.filesystem.resolver import FilesystemResolver
            policy = FilesystemPolicy()
            service = FilesystemService(policy, FilesystemResolver(policy))
        self._service = service

    @property
    def name(self) -> str:
        return "create_directory"

    @property
    def description(self) -> str:
        return (
            "Create a directory under a logical root. Supports creating parent directories. "
            "Requires explicit human confirmation before execution."
        )

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
                    "root": {
                        "type": "string",
                        "description": "The trusted logical root directory (e.g., 'desktop', 'documents', 'downloads', 'workspace')."
                    },
                    "relative_path": {
                        "type": "string",
                        "description": "The relative directory path to create."
                    }
                },
                "required": ["root", "relative_path"]
            }
        }

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        root = kwargs.get("root")
        relative_path = kwargs.get("relative_path")

        try:
            success = self._service.create_directory(root, relative_path)
            return {"success": success, "message": f"Directory created successfully under '{root}': {relative_path}"}
        except FilesystemError as fe:
            raise ToolExecutionError(str(fe))
        except Exception as e:
            raise ToolExecutionError(f"Directory creation failed: {e}")


class WriteTextFileTool(BaseTool):
    """Tool to write a UTF-8 encoded text file under a logical root."""

    def __init__(self, service: Optional[FilesystemService] = None) -> None:
        """Initializes the WriteTextFileTool."""
        if service is None:
            from app.services.filesystem.policy import FilesystemPolicy
            from app.services.filesystem.resolver import FilesystemResolver
            policy = FilesystemPolicy()
            service = FilesystemService(policy, FilesystemResolver(policy))
        self._service = service

    @property
    def name(self) -> str:
        return "write_text_file"

    @property
    def description(self) -> str:
        return (
            "Write character content to a text file under a logical root using UTF-8 encoding. "
            "Strictly rejects executable extensions and non-text indicators. "
            "Requires explicit human confirmation before execution."
        )

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
                    "root": {
                        "type": "string",
                        "description": "The trusted logical root directory (e.g., 'desktop', 'documents', 'downloads', 'workspace')."
                    },
                    "relative_path": {
                        "type": "string",
                        "description": "The relative path of the file to write."
                    },
                    "content": {
                        "type": "string",
                        "description": "The text content to write into the file."
                    }
                },
                "required": ["root", "relative_path", "content"]
            }
        }

    def get_approval_metadata(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Check if target already exists to determine if it is an overwrite."""
        root = arguments.get("root", "")
        relative_path = arguments.get("relative_path", "")
        try:
            target = self._service.inspect_path(root, relative_path)
            return {"overwrite": target.exists}
        except Exception:
            return {"overwrite": False}

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        root = kwargs.get("root")
        relative_path = kwargs.get("relative_path")
        content = kwargs.get("content")

        try:
            success = self._service.write_text_file(root, relative_path, content)
            return {"success": success, "message": f"File written successfully under '{root}': {relative_path}"}
        except FilesystemError as fe:
            raise ToolExecutionError(str(fe))
        except Exception as e:
            raise ToolExecutionError(f"File write failed: {e}")


class MovePathTool(BaseTool):
    """Tool to move files or directories under logical roots."""

    def __init__(self, service: Optional[FilesystemService] = None) -> None:
        """Initializes the MovePathTool."""
        if service is None:
            from app.services.filesystem.policy import FilesystemPolicy
            from app.services.filesystem.resolver import FilesystemResolver
            policy = FilesystemPolicy()
            service = FilesystemService(policy, FilesystemResolver(policy))
        self._service = service

    @property
    def name(self) -> str:
        return "move_path"

    @property
    def description(self) -> str:
        return (
            "Move a file or directory from a source logical root and path to a destination logical root and path. "
            "Fails if a destination collision occurs. "
            "Requires explicit human confirmation before execution."
        )

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
                    "source_root": {
                        "type": "string",
                        "description": "The trusted logical root directory for the source."
                    },
                    "source_relative_path": {
                        "type": "string",
                        "description": "The relative source path to move."
                    },
                    "destination_root": {
                        "type": "string",
                        "description": "The trusted logical root directory for the destination."
                    },
                    "destination_relative_path": {
                        "type": "string",
                        "description": "The relative destination path."
                    }
                },
                "required": ["source_root", "source_relative_path", "destination_root", "destination_relative_path"]
            }
        }

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        source_root = kwargs.get("source_root")
        source_relative_path = kwargs.get("source_relative_path")
        destination_root = kwargs.get("destination_root")
        destination_relative_path = kwargs.get("destination_relative_path")

        try:
            success = self._service.move_path(
                source_root, source_relative_path, destination_root, destination_relative_path
            )
            return {"success": success, "message": f"Successfully moved '{source_relative_path}' to '{destination_relative_path}'."}
        except FilesystemError as fe:
            raise ToolExecutionError(str(fe))
        except Exception as e:
            raise ToolExecutionError(f"Move failed: {e}")


class DeletePathTool(BaseTool):
    """Tool to delete files or directories under a logical root."""

    def __init__(self, service: Optional[FilesystemService] = None) -> None:
        """Initializes the DeletePathTool."""
        if service is None:
            from app.services.filesystem.policy import FilesystemPolicy
            from app.services.filesystem.resolver import FilesystemResolver
            policy = FilesystemPolicy()
            service = FilesystemService(policy, FilesystemResolver(policy))
        self._service = service

    @property
    def name(self) -> str:
        return "delete_path"

    @property
    def description(self) -> str:
        return (
            "Delete a file or directory under a logical root. Non-empty directories require recursive=true. "
            "Requires explicit human confirmation before execution."
        )

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
                    "root": {
                        "type": "string",
                        "description": "The trusted logical root directory (e.g., 'desktop', 'documents', 'downloads', 'workspace')."
                    },
                    "relative_path": {
                        "type": "string",
                        "description": "The relative path to delete."
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Set to true to recursively delete non-empty directories."
                    }
                },
                "required": ["root", "relative_path"]
            }
        }

    def get_approval_metadata(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Check target directory status to support clean CLI presentation."""
        root = arguments.get("root", "")
        relative_path = arguments.get("relative_path", "")
        try:
            target = self._service.inspect_path(root, relative_path)
            return {"is_dir": target.entry_type == "DIRECTORY"}
        except Exception:
            return {"is_dir": False}

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        root = kwargs.get("root")
        relative_path = kwargs.get("relative_path")
        recursive = kwargs.get("recursive", False)

        try:
            success = self._service.delete_path(root, relative_path, recursive)
            return {"success": success, "message": f"Successfully deleted target under '{root}': {relative_path}"}
        except FilesystemError as fe:
            raise ToolExecutionError(str(fe))
        except Exception as e:
            raise ToolExecutionError(f"Delete failed: {e}")
