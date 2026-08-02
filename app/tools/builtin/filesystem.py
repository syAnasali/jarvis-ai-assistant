import os
import fnmatch
from pathlib import Path
from typing import Any, Dict, Optional
from app.tools.base import BaseTool
from app.tools.models import ToolPermission
from app.core.exceptions import ToolExecutionError, FilesystemError, ToolValidationError
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
            "such as existence, type (FILE or DIRECTORY), size in bytes, and last modified timestamp.\n"
            "When to use: Use ONLY when you need to check if a file/directory exists, check its size, or verify its type.\n"
            "When NOT to use: NEVER use to read file content (use 'read_text_file' or 'view_file' if available). NEVER use to list directory contents.\n"
            "Realistic examples: inspect_path(root='desktop', relative_path='projects/jarvis')"
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
            "sorted alphabetically) without recursing. Returns name, type, and size.\n"
            "When to use: Use ONLY when you need to enumerate the files/folders directly inside a folder.\n"
            "When NOT to use: NEVER use to search for files recursively across the entire system. NEVER use to check file content.\n"
            "Realistic examples: list_directory(root='desktop', relative_path='projects')"
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
            "Create a directory (folder) under a logical root. Supports creating parent directories.\n"
            "When to use: Use ONLY when creating folders/directories.\n"
            "When NOT to use: NEVER use for creating files. NEVER use if the target path ends with a file extension (e.g., .txt, .py, .json, .md, .csv, .pdf, etc.).\n"
            "Realistic examples: create_directory(root='desktop', relative_path='projects/jarvis')"
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

    def validate_arguments(self, arguments: Dict[str, Any]) -> None:
        super().validate_arguments(arguments)
        relative_path = arguments.get("relative_path", "")
        basename = os.path.basename(relative_path)
        if "." in basename and not basename.startswith("."):
            raise ToolValidationError(
                f"Validation failed: 'create_directory' must only be used for folders/directories. "
                f"Paths ending with file extensions are invalid. Got: {relative_path}"
            )

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
            "Write character content to a text file under a logical root using UTF-8 encoding.\n"
            "When to use: Use ONLY when the user explicitly provides content to write/save to a file.\n"
            "When NOT to use: NEVER use for creating empty files (use 'create_file' instead). NEVER use for folders/directories.\n"
            "Realistic examples: write_text_file(root='desktop', relative_path='notes.txt', content='Meeting notes: ...')"
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

    def validate_arguments(self, arguments: Dict[str, Any]) -> None:
        super().validate_arguments(arguments)
        relative_path = arguments.get("relative_path", "")
        content = arguments.get("content", None)

        if relative_path.endswith("/") or relative_path.endswith("\\") or "." not in os.path.basename(relative_path):
            raise ToolValidationError(
                f"Validation failed: 'write_text_file' must target a file path, never a directory. Got: {relative_path}"
            )

        if content is None or (isinstance(content, str) and not content.strip()):
            raise ToolValidationError(
                "Validation failed: 'write_text_file' requires non-empty content to write. "
                "Use 'create_file' to create an empty file."
            )

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
            "Move or rename a file or directory from a source logical root and path to a destination logical root and path. "
            "Fails if a destination collision occurs.\n"
            "When to use: Use ONLY when you need to rename a file/folder or move it to a different path/directory.\n"
            "When NOT to use: NEVER use to copy files/folders. NEVER use if you want to overwrite a destination file without checking.\n"
            "Realistic examples: move_path(src_root='desktop', src_path='old.txt', dest_root='desktop', dest_path='new.txt')"
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
            "Delete a file or directory under a logical root. Non-empty directories require recursive=true.\n"
            "When to use: Use ONLY when you need to remove a file or folder from the filesystem permanently.\n"
            "When NOT to use: NEVER use if you just want to empty a file's content but keep the file (write empty string instead). NEVER use to delete system-critical folders.\n"
            "Realistic examples: delete_path(root='desktop', relative_path='temp_data.csv')"
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


class CreateFileTool(BaseTool):
    """Tool to create a new empty file under a logical root."""

    def __init__(self, service: Optional[FilesystemService] = None) -> None:
        """Initializes the CreateFileTool."""
        if service is None:
            from app.services.filesystem.policy import FilesystemPolicy
            from app.services.filesystem.resolver import FilesystemResolver
            policy = FilesystemPolicy()
            service = FilesystemService(policy, FilesystemResolver(policy))
        self._service = service

    @property
    def name(self) -> str:
        return "create_file"

    @property
    def description(self) -> str:
        return (
            "Create a new empty file under a logical root.\n"
            "When to use: Use ONLY when creating a new, empty file.\n"
            "When NOT to use: NEVER use for folders/directories. NEVER use if you already have content to write (use 'write_text_file' instead).\n"
            "Realistic examples: create_file(root='desktop', relative_path='notes.txt')"
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
                        "description": "The relative file path to create."
                    }
                },
                "required": ["root", "relative_path"]
            }
        }

    def validate_arguments(self, arguments: Dict[str, Any]) -> None:
        super().validate_arguments(arguments)
        relative_path = arguments.get("relative_path", "")

        if not relative_path.strip() or relative_path.endswith("/") or relative_path.endswith("\\") or not os.path.basename(relative_path).strip() or "." not in os.path.basename(relative_path):
            raise ToolValidationError(
                f"Validation failed: 'create_file' must only be used for files, never for folders. Got: {relative_path}"
            )

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        root = kwargs.get("root")
        relative_path = kwargs.get("relative_path")

        try:
            success = self._service.write_text_file(root, relative_path, "")
            return {"success": success, "message": f"Empty file created successfully under '{root}': {relative_path}"}
        except FilesystemError as fe:
            raise ToolExecutionError(str(fe))
        except Exception as e:
            raise ToolExecutionError(f"File creation failed: {e}")
