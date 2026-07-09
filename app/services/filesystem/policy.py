"""Security policy and trusted root folder resolution for the filesystem."""

import os
from pathlib import Path
from typing import Dict, Optional, Set


class FilesystemPolicy:
    """Centralized security policy for root-bounded filesystem access."""

    BLOCKED_EXTENSIONS: Set[str] = {
        ".exe",
        ".com",
        ".bat",
        ".cmd",
        ".ps1",
        ".vbs",
        ".js",
        ".py",
        ".msi",
        ".dll",
        ".scr",
    }

    def __init__(self, custom_roots: Optional[Dict[str, Path]] = None) -> None:
        """Initializes the security policy.

        Args:
            custom_roots: Optional dictionary mapping root names to Path.
                          Used for isolated testing/diagnostics.
        """
        self._roots: Dict[str, Path] = {}
        if custom_roots is not None:
            # Clean and resolve custom paths
            for name, path in custom_roots.items():
                self._roots[name.lower()] = Path(path).resolve()
        else:
            # Resolve standard active Windows environment roots
            user_profile = os.getenv("USERPROFILE")
            if user_profile:
                user_path = Path(user_profile)
                self._roots["desktop"] = (user_path / "Desktop").resolve()
                self._roots["documents"] = (user_path / "Documents").resolve()
                self._roots["downloads"] = (user_path / "Downloads").resolve()
            else:
                # Fallbacks in case USERPROFILE is missing in non-Windows/CI env
                home = os.getenv("HOME") or os.path.expanduser("~")
                home_path = Path(home)
                self._roots["desktop"] = (home_path / "Desktop").resolve()
                self._roots["documents"] = (home_path / "Documents").resolve()
                self._roots["downloads"] = (home_path / "Downloads").resolve()

            self._roots["workspace"] = Path(os.getcwd()).resolve()

    def get_roots(self) -> Dict[str, Path]:
        """Returns the dictionary of active logical roots mapped to resolved absolute Paths."""
        return self._roots.copy()

    def is_valid_root(self, root_name: str) -> bool:
        """Checks if a logical root name is registered in the policy."""
        if not root_name:
            return False
        return root_name.lower() in self._roots

    def get_root_path(self, root_name: str) -> Optional[Path]:
        """Retrieves the resolved Path for a logical root name."""
        if not root_name:
            return None
        return self._roots.get(root_name.lower())

    def is_blocked_extension(self, filename: str) -> bool:
        """Checks if a filename matches any of the blocked extensions case-insensitively."""
        if not filename:
            return False
        suffix = Path(filename).suffix.lower()
        return suffix in self.BLOCKED_EXTENSIONS
