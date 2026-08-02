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
            # Resolve standard active environment roots
            user_profile = os.getenv("USERPROFILE")
            home_path = Path(user_profile) if user_profile else Path.home()
            
            # Windows shell folders resolution
            if os.name == "nt":
                import winreg
                reg_keys = {
                    "desktop": "Desktop",
                    "documents": "Personal",
                    "downloads": "{374DE290-123F-4565-9164-39C4925E467B}",
                    "pictures": "My Pictures",
                    "videos": "My Video",
                    "music": "My Music",
                }
                for key_name, reg_val in reg_keys.items():
                    try:
                        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as key:
                            val, _ = winreg.QueryValueEx(key, reg_val)
                            self._roots[key_name] = Path(os.path.expandvars(val)).resolve()
                    except Exception:
                        try:
                            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as key:
                                val, _ = winreg.QueryValueEx(key, reg_val)
                                self._roots[key_name] = Path(val).resolve()
                        except Exception:
                            # Fallback
                            fallback_dirs = {
                                "desktop": "Desktop",
                                "documents": "Documents",
                                "downloads": "Downloads",
                                "pictures": "Pictures",
                                "videos": "Videos",
                                "music": "Music",
                            }
                            self._roots[key_name] = (home_path / fallback_dirs[key_name]).resolve()
            else:
                # Non-Windows fallbacks
                self._roots["desktop"] = (home_path / "Desktop").resolve()
                self._roots["documents"] = (home_path / "Documents").resolve()
                self._roots["downloads"] = (home_path / "Downloads").resolve()
                self._roots["pictures"] = (home_path / "Pictures").resolve()
                self._roots["videos"] = (home_path / "Videos").resolve()
                self._roots["music"] = (home_path / "Music").resolve()

            # Home and Temp and Workspace
            self._roots["home"] = home_path.resolve()
            import tempfile
            self._roots["temp"] = Path(tempfile.gettempdir()).resolve()
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
