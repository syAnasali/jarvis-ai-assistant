"""Built-in filesystem tools and safety validation helpers."""

import os
import fnmatch
from pathlib import Path
from typing import Any, Dict, List
from app.tools.base import BaseTool
from app.tools.models import ToolPermission
from app.core.exceptions import ToolExecutionError
from app.config.settings import settings

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


class ListDirectoryTool(BaseTool):
    """Tool to list contents of a directory without recursion."""

    @property
    def name(self) -> str:
        return "list_directory"

    @property
    def description(self) -> str:
        return (
            "List the contents of a directory (directories first, then files, sorted alphabetically) "
            "without recursing. Only provides basic metadata like name, type, and size."
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
                    "path": {
                        "type": "string",
                        "description": "The directory path to list entries for."
                    },
                    "limit": {
                        "type": "integer",
                        "description": f"Optional maximum number of entries to return. Default {settings.tool_default_list_limit}, maximum {settings.tool_max_list_limit}."
                    }
                },
                "required": ["path"]
            }
        }

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        path = kwargs.get("path")
        resolved = validate_and_resolve_path(path, expected_type="directory")

        limit = kwargs.get("limit")
        if limit is None:
            limit = settings.tool_default_list_limit
        else:
            if limit <= 0 or limit > settings.tool_max_list_limit:
                raise ToolExecutionError(f"Limit must be between 1 and {settings.tool_max_list_limit}.")

        try:
            raw_entries = os.listdir(resolved)
        except PermissionError:
            raise ToolExecutionError(f"Permission denied: {path}")
        except Exception as e:
            raise ToolExecutionError(f"Failed to list directory: {e}")

        total_count = len(raw_entries)
        dirs = []
        files = []

        for name in raw_entries:
            entry_path = os.path.join(resolved, name)
            try:
                if os.path.isdir(entry_path):
                    dirs.append(name)
                elif os.path.isfile(entry_path):
                    files.append(name)
            except Exception:
                pass

        dirs.sort(key=str.lower)
        files.sort(key=str.lower)

        sorted_entries = []
        for d in dirs:
            sorted_entries.append({"name": d, "type": "directory", "size_bytes": None})
        for f in files:
            size = None
            try:
                size = os.path.getsize(os.path.join(resolved, f))
            except Exception:
                pass
            sorted_entries.append({"name": f, "type": "file", "size_bytes": size})

        truncated = len(sorted_entries) > limit
        final_entries = sorted_entries[:limit]

        return {
            "path": resolved,
            "entries": final_entries,
            "returned_count": len(final_entries),
            "total_count": total_count,
            "truncated": truncated
        }


class ReadTextFileTool(BaseTool):
    """Tool to safely read character-bounded content from regular text files."""

    @property
    def name(self) -> str:
        return "read_text_file"

    @property
    def description(self) -> str:
        return (
            "Read content from a user-requested local text file. Automatically rejects binary files, "
            "unsupported extensions, files larger than 2MB, and credential/private key files."
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
                    "path": {
                        "type": "string",
                        "description": "The path to the text file to read."
                    },
                    "max_characters": {
                        "type": "integer",
                        "description": f"Optional character limit to return. Default {settings.tool_default_text_characters}, maximum {settings.tool_max_text_characters}."
                    }
                },
                "required": ["path"]
            }
        }

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        path = kwargs.get("path")
        resolved = validate_and_resolve_path(path, expected_type="file")

        # Centralized extension check
        ext = os.path.splitext(resolved)[1].lower()
        allowed_extensions = {
            ".txt", ".md", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
            ".csv", ".log", ".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css"
        }
        if ext not in allowed_extensions:
            raise ToolExecutionError(f"Unsupported file extension: {ext}. Only common text extensions are allowed.")

        try:
            file_size = os.path.getsize(resolved)
        except Exception as e:
            raise ToolExecutionError(f"Failed to get file size: {e}")

        if file_size > settings.tool_max_text_file_bytes:
            raise ToolExecutionError(f"File size ({file_size} bytes) exceeds limit of {settings.tool_max_text_file_bytes} bytes.")

        max_chars = kwargs.get("max_characters")
        if max_chars is None:
            max_chars = settings.tool_default_text_characters
        else:
            if max_chars <= 0 or max_chars > settings.tool_max_text_characters:
                raise ToolExecutionError(f"max_characters must be between 1 and {settings.tool_max_text_characters}.")

        try:
            with open(resolved, "rb") as f:
                raw_bytes = f.read()
        except PermissionError:
            raise ToolExecutionError(f"Permission denied: {path}")
        except Exception as e:
            raise ToolExecutionError(f"Failed to read file: {e}")

        if b"\x00" in raw_bytes:
            raise ToolExecutionError("Binary content detected. Only text files are supported.")

        # Safe text decoding strategy
        try:
            content = raw_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                content = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                content = raw_bytes.decode("utf-8", errors="replace")

        truncated = len(content) > max_chars
        final_content = content[:max_chars]

        return {
            "path": resolved,
            "content": final_content,
            "characters_returned": len(final_content),
            "truncated": truncated,
            "file_size_bytes": file_size
        }
