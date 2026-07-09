"""Built-in Windows application discovery tools."""

from typing import Any, Dict, List
from app.tools.base import BaseTool
from app.tools.models import ToolPermission
from app.core.exceptions import ToolExecutionError
from app.config.settings import settings

def discover_installed_applications() -> List[Dict[str, Any]]:
    """Traverses the Windows registry to locate installed applications.

    Returns:
        List[Dict[str, Any]]: Deduplicated list of applications sorted by name.
    """
    apps: List[Dict[str, Any]] = []
    try:
        import winreg
    except ImportError:
        # Graceful fallback on non-Windows development/test environments
        return []

    # Windows registry Uninstall subkeys to traverse
    targets = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
    ]

    seen_names = set()

    for hkey, subkey in targets:
        # Try opening the key with 64-bit view first, then default
        try:
            key = winreg.OpenKey(hkey, subkey, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
        except OSError:
            try:
                key = winreg.OpenKey(hkey, subkey, 0, winreg.KEY_READ)
            except OSError:
                continue

        try:
            subkeys_num, _, _ = winreg.QueryInfoKey(key)
            for i in range(subkeys_num):
                try:
                    name_key = winreg.EnumKey(key, i)
                    with winreg.OpenKey(key, name_key) as app_key:
                        try:
                            display_name, _ = winreg.QueryValueEx(app_key, "DisplayName")
                            if not display_name or not isinstance(display_name, str) or not display_name.strip():
                                continue
                            
                            display_name = display_name.strip()
                            name_lower = display_name.lower()
                            
                            if name_lower not in seen_names:
                                seen_names.add(name_lower)
                                
                                version = ""
                                publisher = ""
                                try:
                                    version, _ = winreg.QueryValueEx(app_key, "DisplayVersion")
                                except OSError:
                                    pass
                                try:
                                    publisher, _ = winreg.QueryValueEx(app_key, "Publisher")
                                except OSError:
                                    pass

                                apps.append({
                                    "name": display_name,
                                    "version": str(version).strip() if version else "",
                                    "publisher": str(publisher).strip() if publisher else ""
                                })
                        except OSError:
                            continue
                except OSError:
                    continue
        except OSError:
            continue
        finally:
            winreg.CloseKey(key)

    apps.sort(key=lambda x: x["name"].lower())
    return apps


class ListInstalledApplicationsTool(BaseTool):
    """Tool to list all installed applications on the Windows machine."""

    @property
    def name(self) -> str:
        return "list_installed_applications"

    @property
    def description(self) -> str:
        return (
            "Retrieve a list of installed applications discovered in the Windows registry, "
            "sorted by name. Includes versions and publishers where available."
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
                    "limit": {
                        "type": "integer",
                        "description": f"Optional maximum number of results to return. Default {settings.tool_default_list_limit}, maximum 500."
                    }
                },
                "required": []
            }
        }

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        limit = kwargs.get("limit")
        if limit is None:
            limit = 100
        else:
            if limit <= 0 or limit > 500:
                raise ToolExecutionError("Limit must be between 1 and 500.")

        try:
            apps = discover_installed_applications()
        except Exception as e:
            raise ToolExecutionError(f"Failed to scan registry for applications: {e}")

        # Explicit sorting
        apps.sort(key=lambda x: x["name"].lower())
        truncated = len(apps) > limit
        final_apps = apps[:limit]

        return {
            "applications": final_apps,
            "returned_count": len(final_apps),
            "truncated": truncated
        }


class FindInstalledApplicationTool(BaseTool):
    """Tool to search installed applications using case-insensitive query matching."""

    @property
    def name(self) -> str:
        return "find_installed_application"

    @property
    def description(self) -> str:
        return (
            "Search for installed applications using a case-insensitive name query. "
            "Matches against publisher and application names."
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
                    "query": {
                        "type": "string",
                        "description": "Case-insensitive query string (e.g. 'Ollama', 'Python')."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Optional maximum number of matching results to return. Default 100, maximum 500."
                    }
                },
                "required": ["query"]
            }
        }

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        query = kwargs.get("query")
        if not query or not isinstance(query, str) or not query.strip():
            raise ToolExecutionError("Query must be a non-empty string.")

        limit = kwargs.get("limit")
        if limit is None:
            limit = 100
        else:
            if limit <= 0 or limit > 500:
                raise ToolExecutionError("Limit must be between 1 and 500.")

        query_lower = query.lower().strip()
        try:
            all_apps = discover_installed_applications()
        except Exception as e:
            raise ToolExecutionError(f"Failed to query registry for applications: {e}")

        matches = []
        for app in all_apps:
            name = app.get("name") or ""
            pub = app.get("publisher") or ""
            if query_lower in name.lower() or query_lower in pub.lower():
                matches.append(app)

        # Explicit sorting
        matches.sort(key=lambda x: x["name"].lower())
        truncated = len(matches) > limit
        final_matches = matches[:limit]

        return {
            "query": query,
            "matches": final_matches,
            "match_count": len(final_matches),
            "truncated": truncated
        }
