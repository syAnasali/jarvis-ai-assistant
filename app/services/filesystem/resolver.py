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
        # Determine path input
        rel_str = (relative_path or "").strip()

        # Reject null bytes
        if "\x00" in rel_str:
            raise InvalidPathError("Relative path contains null bytes.")

        # Reject UNC or device paths in relative_path
        if "device" in rel_str.lower() or "\\\\.\\" in rel_str or "\\\\?\\" in rel_str:
            raise UnsupportedPathError("Device paths are strictly prohibited.")
        if rel_str.startswith("//") or rel_str.startswith("\\\\"):
            raise UnsupportedPathError("UNC and network paths are strictly prohibited.")

        # Check if relative_path is absolute or starts with a drive letter / absolute slash
        if rel_str and (os.path.isabs(rel_str) or re.match(r"^[a-zA-Z]:[\\/]", rel_str) or rel_str.startswith("/") or rel_str.startswith("\\")):
            target_path = Path(rel_str)
        else:
            # Check if relative_path starts with a drive letter but no slash (drive-qualified relative)
            if rel_str and re.match(r"^[a-zA-Z]:", rel_str):
                raise InvalidPathError("Relative path cannot contain drive-qualified specifiers.")

            # Check if relative_path starts with a virtual alias prefix
            parts = Path(rel_str).parts if rel_str else ()
            if parts and parts[0].lower() in self._policy.get_roots():
                alias = parts[0].lower()
                alias_path = self._policy.get_root_path(alias)
                rest = Path(*parts[1:]) if len(parts) > 1 else Path(".")
                target_path = alias_path / rest
            else:
                # Resolve relative to root name
                root_name = (root or "workspace").lower()
                root_path = self._policy.get_root_path(root_name)
                if not root_path:
                    # Fallback to workspace
                    root_path = self._policy.get_root_path("workspace")
                    root_name = "workspace"
                
                if rel_str:
                    target_path = root_path / rel_str.replace("\\", "/").replace("//", "/")
                else:
                    target_path = root_path

        # Resolve paths to handle dot segments and symlinks
        try:
            resolved_target = target_path.resolve()
        except Exception:
            try:
                resolved_target = target_path.resolve(strict=False)
            except Exception as e:
                raise InvalidPathError(f"Failed to resolve path components: {e}")

        # Check containment against at least one allowed root in policy
        resolved_target_str = str(resolved_target).lower()
        within_any = False
        matching_root = None

        for name, rp in self._policy.get_roots().items():
            rp_str = str(rp.resolve()).lower()
            if resolved_target_str == rp_str or resolved_target_str.startswith(rp_str + os.sep):
                within_any = True
                matching_root = name
                break

        if not within_any:
            if rel_str.startswith("/") or rel_str.startswith("\\"):
                raise InvalidPathError("Relative path cannot start with absolute path slashes.")
            if re.match(r"^[a-zA-Z]:", rel_str):
                raise InvalidPathError("Relative path cannot contain drive-qualified specifiers.")
            raise PathEscapeError("Directory traversal escape detected: target is outside root permitted virtual locations.")

        # Also inspect intermediate parents to detect symlink escapes for non-existent targets
        current = target_path
        matched_root_path = self._policy.get_root_path(matching_root)
        while current != matched_root_path and current.parent != current:
            if current.exists():
                try:
                    res_current = current.resolve()
                    res_current_str = str(res_current).lower()
                    parent_within = False
                    for name, rp in self._policy.get_roots().items():
                        rp_str = str(rp.resolve()).lower()
                        if res_current_str == rp_str or res_current_str.startswith(rp_str + os.sep):
                            parent_within = True
                            break
                    if not parent_within:
                        raise PathEscapeError("Junction or symlink traversal escape detected: parent resolves outside root permitted virtual locations.")
                except Exception:
                    pass
            current = current.parent

        # Determine target state
        exists = resolved_target.exists()
        entry_type = "MISSING"
        if exists:
            if resolved_target.is_dir():
                entry_type = "DIRECTORY"
            elif resolved_target.is_file():
                entry_type = "FILE"

        # Construct clean relative path relative to matched root
        try:
            clean_rel = str(resolved_target.relative_to(matched_root_path)).replace("\\", "/")
        except ValueError:
            clean_rel = str(resolved_target).replace("\\", "/")

        return FilesystemTarget(
            root=matching_root.lower() if matching_root else (root or "workspace").lower(),
            relative_path=clean_rel,
            resolved_path=resolved_target,
            exists=exists,
            entry_type=entry_type,
        )
