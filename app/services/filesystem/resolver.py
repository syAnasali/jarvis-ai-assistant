"""Path security and resolution engine for bounded filesystem access."""

import os
import re
from pathlib import Path
from typing import Optional
from app.services.filesystem.policy import FilesystemPolicy
from app.services.filesystem.models import FilesystemTarget
from app.core.exceptions import (
    InvalidRootError,
    InvalidPathError,
    PathEscapeError,
    UnsupportedPathError,
)


class FilesystemResolver:
    """Validates and resolves logical roots and relative paths safely."""

    def __init__(self, policy: FilesystemPolicy) -> None:
        """Initializes the resolver with a filesystem security policy."""
        self._policy = policy

    def resolve(self, root: str, relative_path: Optional[str]) -> FilesystemTarget:
        """Strictly validates and resolves a logical root and relative path.

        Raises:
            InvalidRootError: If root is invalid.
            InvalidPathError: If relative path is invalid/contains illegal components.
            UnsupportedPathError: If path contains UNC/device patterns.
            PathEscapeError: If path containment or traversal check fails.
        """
        # 1. Validate root
        if not root or not self._policy.is_valid_root(root):
            raise InvalidRootError(f"Invalid or unregistered root: '{root}'")

        root_path = self._policy.get_root_path(root)
        if not root_path:
            raise InvalidRootError(f"Failed to retrieve path for root: '{root}'")
        
        # 2. Normalize and check relative path
        if relative_path is None:
            relative_path = ""
        
        if not isinstance(relative_path, str):
            raise InvalidPathError("Relative path must be a string.")

        # Reject null bytes
        if "\x00" in relative_path:
            raise InvalidPathError("Relative path contains null bytes.")

        # Reject UNC or device paths
        raw_strip = relative_path.strip()
        if "device" in relative_path.lower() or "\\\\.\\" in relative_path or "\\\\?\\" in relative_path:
            raise UnsupportedPathError("Device paths are strictly prohibited.")
        if raw_strip.startswith("//") or raw_strip.startswith("\\\\"):
            raise UnsupportedPathError("UNC and network paths are strictly prohibited.")

        # Strip surrounding spaces and replace any duplicate slashes
        clean_rel = raw_strip.replace("\\", "/").replace("//", "/")
        
        # Reject absolute path indicators
        if clean_rel.startswith("/") or clean_rel.startswith("\\"):
            raise InvalidPathError("Relative path cannot start with absolute path slashes.")

        # Reject drive-qualified paths (e.g. C: or D:)
        if re.match(r"^[a-zA-Z]:", clean_rel):
            raise InvalidPathError("Relative path cannot contain drive-qualified specifiers.")
        if "device" in clean_rel.lower() or "\\\\.\\" in clean_rel or "\\\\?\\" in clean_rel:
            raise UnsupportedPathError("Device paths are strictly prohibited.")

        # Construct target path
        target_path = root_path / clean_rel

        # Resolve paths to handle dot segments and symlinks
        # On Windows, resolve(strict=False) resolves as much as possible.
        try:
            resolved_target = target_path.resolve()
        except Exception as e:
            raise InvalidPathError(f"Failed to resolve path components: {e}")

        # Check containment
        root_path_str = str(root_path.resolve()).lower()
        resolved_target_str = str(resolved_target).lower()

        # Target must be inside the root path
        if not (resolved_target_str == root_path_str or resolved_target_str.startswith(root_path_str + os.sep)):
            raise PathEscapeError(f"Directory traversal escape detected: target is outside root '{root}'")

        # Also inspect intermediate parents to detect symlink escapes for non-existent targets
        current = target_path
        while current != root_path:
            if current.exists():
                try:
                    res_current = current.resolve()
                    res_current_str = str(res_current).lower()
                    if not (res_current_str == root_path_str or res_current_str.startswith(root_path_str + os.sep)):
                        raise PathEscapeError(f"Junction or symlink traversal escape detected: parent resolves outside root '{root}'")
                except Exception:
                    pass
            current = current.parent

        # Determine target state
        exists = target_path.exists()
        entry_type = "MISSING"
        if exists:
            if target_path.is_dir():
                entry_type = "DIRECTORY"
            elif target_path.is_file():
                entry_type = "FILE"

        return FilesystemTarget(
            root=root.lower(),
            relative_path=clean_rel,
            resolved_path=target_path,
            exists=exists,
            entry_type=entry_type,
        )
