"""High-level filesystem operations and safety checks service."""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.services.filesystem.models import FilesystemTarget, FilesystemMetrics
from app.services.filesystem.policy import FilesystemPolicy
from app.services.filesystem.resolver import FilesystemResolver
from app.core.exceptions import (
    FilesystemError,
    InvalidPathError,
    PathNotFoundError,
    PathAlreadyExistsError,
    TypeMismatchError,
    DirectoryNotEmptyError,
    BlockedExtensionError,
    ContentTooLargeError,
    OSFilesystemError,
)


class FilesystemService:
    """Provides validated, root-bounded filesystem actions and operations."""

    def __init__(
        self,
        policy: FilesystemPolicy,
        resolver: FilesystemResolver,
        list_max_entries: int = 100,
        write_max_chars: int = 100000,
        relative_path_max_length: int = 512,
    ) -> None:
        """Initializes the FilesystemService with policies, limits, and resolver."""
        self._policy = policy
        self._resolver = resolver
        self._list_max_entries = list_max_entries
        self._write_max_chars = write_max_chars
        self._relative_path_max_length = relative_path_max_length
        self.metrics = FilesystemMetrics()

    def inspect_path(self, root: str, relative_path: str) -> FilesystemTarget:
        """Inspects metadata of a filesystem target path.

        Raises:
            FilesystemError: If path resolution or policy check fails.
        """
        self.metrics.increment("inspection_requests")
        
        if len(relative_path or "") > self._relative_path_max_length:
            self.metrics.increment("policy_rejections")
            raise InvalidPathError(f"Relative path length exceeds maximum of {self._relative_path_max_length} characters.")

        try:
            target = self._resolver.resolve(root, relative_path)
            return target
        except FilesystemError as fe:
            self.metrics.increment("policy_rejections")
            raise fe
        except Exception as e:
            self.metrics.increment("failed_mutations")
            raise OSFilesystemError(f"Inspection failed: {e}")

    def list_directory(
        self, root: str, relative_path: Optional[str] = None, limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Lists directory contents deterministically (non-recursively).

        Raises:
            FilesystemError: If target not found or is not a directory.
        """
        self.metrics.increment("directory_list_requests")

        if relative_path and len(relative_path) > self._relative_path_max_length:
            self.metrics.increment("policy_rejections")
            raise InvalidPathError(f"Relative path length exceeds maximum of {self._relative_path_max_length} characters.")

        try:
            target = self._resolver.resolve(root, relative_path)
        except FilesystemError as fe:
            self.metrics.increment("policy_rejections")
            raise fe

        if not target.exists:
            raise PathNotFoundError(f"Directory not found: {relative_path or ''}")

        if target.entry_type != "DIRECTORY":
            raise TypeMismatchError(f"Target is not a directory: {relative_path or ''}")

        resolved_dir = target.resolved_path

        # Determine limits
        list_limit = self._list_max_entries
        if limit is not None:
            if limit <= 0 or limit > self._list_max_entries:
                raise InvalidPathError(f"Limit must be positive and not exceed {self._list_max_entries}.")
            list_limit = limit

        try:
            entries = list(resolved_dir.iterdir())
        except PermissionError:
            raise OSFilesystemError(f"Permission denied to list directory: {relative_path or ''}")
        except Exception as e:
            raise OSFilesystemError(f"Failed to list directory: {e}")

        total_count = len(entries)
        
        # Partition into directories and files
        dirs: List[Path] = []
        files: List[Path] = []
        for p in entries:
            try:
                # Handle symlinks safely - check resolved target if symlink
                if p.is_dir():
                    dirs.append(p)
                elif p.is_file():
                    files.append(p)
            except Exception:
                pass

        # Sort alphabetically, case-insensitive
        dirs.sort(key=lambda x: x.name.lower())
        files.sort(key=lambda x: x.name.lower())

        sorted_entries = []
        for d in dirs:
            sorted_entries.append({
                "name": d.name,
                "entry_type": "DIRECTORY",
                "type": "directory",
                "size_bytes": None
            })

        for f in files:
            size = None
            try:
                size = f.stat().st_size
            except Exception:
                pass
            sorted_entries.append({
                "name": f.name,
                "entry_type": "FILE",
                "type": "file",
                "size_bytes": size
            })

        truncated = len(sorted_entries) > list_limit
        final_entries = sorted_entries[:list_limit]

        return {
            "root": root.lower(),
            "relative_path": target.relative_path,
            "entries": final_entries,
            "returned_count": len(final_entries),
            "total_count": total_count,
            "truncated": truncated,
        }

    def create_directory(self, root: str, relative_path: str) -> bool:
        """Idempotently creates a directory under the logical root.

        Raises:
            FilesystemError: If target path or creation fails.
        """
        self.metrics.increment("create_requests")

        if not relative_path:
            self.metrics.increment("policy_rejections")
            raise InvalidPathError("Cannot create a directory with an empty relative path.")

        if len(relative_path) > self._relative_path_max_length:
            self.metrics.increment("policy_rejections")
            raise InvalidPathError(f"Relative path length exceeds maximum of {self._relative_path_max_length} characters.")

        try:
            target = self._resolver.resolve(root, relative_path)
        except FilesystemError as fe:
            self.metrics.increment("policy_rejections")
            raise fe

        if target.exists:
            if target.entry_type == "DIRECTORY":
                # Idempotent success
                self.metrics.increment("successful_mutations")
                return True
            else:
                self.metrics.increment("failed_mutations")
                raise PathAlreadyExistsError(f"A file already exists at path: {relative_path}")

        try:
            target.resolved_path.mkdir(parents=True, exist_ok=True)
            self.metrics.increment("successful_mutations")
            return True
        except Exception as e:
            self.metrics.increment("failed_mutations")
            raise OSFilesystemError(f"Failed to create directory: {e}")

    def write_text_file(self, root: str, relative_path: str, content: str) -> bool:
        """Atomic write of UTF-8 text file.

        Raises:
            FilesystemError: If validation, size limits, extension blocks, or write fails.
        """
        self.metrics.increment("write_requests")

        if not relative_path:
            self.metrics.increment("policy_rejections")
            raise InvalidPathError("Relative path cannot be empty.")

        if len(relative_path) > self._relative_path_max_length:
            self.metrics.increment("policy_rejections")
            raise InvalidPathError(f"Relative path length exceeds maximum of {self._relative_path_max_length} characters.")

        # Check content limits
        if len(content or "") > self._write_max_chars:
            self.metrics.increment("policy_rejections")
            raise ContentTooLargeError(f"Content length of {len(content)} characters exceeds limit of {self._write_max_chars} characters.")

        # Check binary characters
        if "\x00" in (content or ""):
            self.metrics.increment("policy_rejections")
            raise InvalidPathError("Binary contents (null bytes) are prohibited in write_text_file.")

        # Check extensions
        if self._policy.is_blocked_extension(relative_path):
            self.metrics.increment("policy_rejections")
            raise BlockedExtensionError(f"Access to extension blocked: {Path(relative_path).suffix}")

        try:
            target = self._resolver.resolve(root, relative_path)
        except FilesystemError as fe:
            self.metrics.increment("policy_rejections")
            raise fe

        if target.exists and target.entry_type == "DIRECTORY":
            self.metrics.increment("failed_mutations")
            raise TypeMismatchError(f"Cannot overwrite directory with a text file: {relative_path}")

        parent_dir = target.resolved_path.parent
        if not parent_dir.exists() or not parent_dir.is_dir():
            self.metrics.increment("failed_mutations")
            raise PathNotFoundError(f"Parent directory does not exist: {relative_path}")

        # Atomic Write
        temp_fd = None
        temp_path = None
        try:
            # Create a secure temporary file in the same directory
            temp_fd, temp_path = tempfile.mkstemp(
                dir=str(parent_dir), prefix=".tmp_jarvis_", suffix=".tmp", text=True
            )
            with os.fdopen(temp_fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            temp_fd = None  # fd is closed by context manager
            
            # Replace target atomically
            os.replace(temp_path, str(target.resolved_path))
            self.metrics.increment("successful_mutations")
            return True
        except Exception as e:
            self.metrics.increment("failed_mutations")
            # Cleanup temp file on failure
            if temp_fd is not None:
                try:
                    os.close(temp_fd)
                except Exception:
                    pass
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
            raise OSFilesystemError(f"Failed to write text file atomically: {e}")

    def move_path(
        self,
        source_root: str,
        source_relative_path: str,
        destination_root: str,
        destination_relative_path: str,
    ) -> bool:
        """Moves a file or folder from source to destination.

        Raises:
            FilesystemError: If move rule validation or filesystem action fails.
        """
        self.metrics.increment("move_requests")

        if not source_relative_path or not destination_relative_path:
            self.metrics.increment("policy_rejections")
            raise InvalidPathError("Source and destination relative paths must be non-empty.")

        if (len(source_relative_path) > self._relative_path_max_length or 
                len(destination_relative_path) > self._relative_path_max_length):
            self.metrics.increment("policy_rejections")
            raise InvalidPathError(f"Path length exceeds limit of {self._relative_path_max_length} characters.")

        try:
            src_target = self._resolver.resolve(source_root, source_relative_path)
            dest_target = self._resolver.resolve(destination_root, destination_relative_path)
        except FilesystemError as fe:
            self.metrics.increment("policy_rejections")
            raise fe

        # Source must exist
        if not src_target.exists:
            self.metrics.increment("failed_mutations")
            raise PathNotFoundError(f"Source path does not exist: {source_relative_path}")

        # Source trusted root itself cannot be moved
        src_root_path = self._policy.get_root_path(source_root).resolve()
        if src_target.resolved_path.resolve() == src_root_path:
            self.metrics.increment("policy_rejections")
            raise InvalidPathError("Cannot move the trusted root directory itself.")

        # Destination trusted root itself cannot be overwritten
        dest_root_path = self._policy.get_root_path(destination_root).resolve()
        if dest_target.resolved_path.resolve() == dest_root_path:
            self.metrics.increment("policy_rejections")
            raise InvalidPathError("Cannot overwrite the destination trusted root directory.")

        # Destination must not exist (no collision allowed in this sprint)
        if dest_target.exists:
            self.metrics.increment("failed_mutations")
            raise PathAlreadyExistsError(f"Destination path already exists: {destination_relative_path}")

        # Verify destination parent directory exists
        dest_parent = dest_target.resolved_path.parent
        if not dest_parent.exists() or not dest_parent.is_dir():
            self.metrics.increment("failed_mutations")
            raise PathNotFoundError(f"Destination parent directory does not exist for: {destination_relative_path}")

        try:
            shutil.move(str(src_target.resolved_path), str(dest_target.resolved_path))
            self.metrics.increment("successful_mutations")
            return True
        except Exception as e:
            self.metrics.increment("failed_mutations")
            raise OSFilesystemError(f"Failed to move path: {e}")

    def delete_path(self, root: str, relative_path: str, recursive: bool = False) -> bool:
        """Deletes a file or directory under the logical root.

        Raises:
            FilesystemError: If validation constraints or deletion actions fail.
        """
        self.metrics.increment("delete_requests")

        if not relative_path:
            self.metrics.increment("policy_rejections")
            raise InvalidPathError("Cannot delete root directory or empty path.")

        if len(relative_path) > self._relative_path_max_length:
            self.metrics.increment("policy_rejections")
            raise InvalidPathError(f"Relative path length exceeds maximum of {self._relative_path_max_length} characters.")

        try:
            target = self._resolver.resolve(root, relative_path)
        except FilesystemError as fe:
            self.metrics.increment("policy_rejections")
            raise fe

        if not target.exists:
            self.metrics.increment("failed_mutations")
            raise PathNotFoundError(f"Path does not exist: {relative_path}")

        root_path = self._policy.get_root_path(root).resolve()
        if target.resolved_path.resolve() == root_path:
            self.metrics.increment("policy_rejections")
            raise InvalidPathError("Deleting the trusted root directory itself is strictly prohibited.")

        resolved_path = target.resolved_path

        try:
            if target.entry_type == "FILE":
                resolved_path.unlink()
            elif target.entry_type == "DIRECTORY":
                # Check empty
                is_empty = not any(resolved_path.iterdir())
                if not is_empty and not recursive:
                    self.metrics.increment("failed_mutations")
                    raise DirectoryNotEmptyError(f"Directory is not empty: {relative_path}. Set recursive=True to delete.")
                
                if recursive:
                    # shutil.rmtree ignores symlinks (deletes symlink, not target)
                    shutil.rmtree(str(resolved_path))
                else:
                    resolved_path.rmdir()

            self.metrics.increment("successful_mutations")
            return True
        except DirectoryNotEmptyError as dnee:
            raise dnee
        except Exception as e:
            self.metrics.increment("failed_mutations")
            raise OSFilesystemError(f"Failed to delete path: {e}")
