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


class ResolveApplicationTool(BaseTool):
    """Tool to resolve a user application query to a specific launchable application."""

    @property
    def name(self) -> str:
        return "resolve_application"

    @property
    def description(self) -> str:
        return (
            "Resolve a user application name query to a trusted launchable application ID. "
            "Returns RESOLVED with the application details, NOT_FOUND if no application matches, "
            "or AMBIGUOUS with a list of matching candidate applications to ask the user to clarify."
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
                        "description": "The name or alias of the application to resolve (e.g., 'VS Code', 'Notepad', 'Calculator')."
                    }
                },
                "required": ["query"]
            }
        }

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        query = kwargs.get("query")
        if not query or not isinstance(query, str) or not query.strip():
            raise ToolExecutionError("Query must be a non-empty string.")

        from app.services.applications.resolver import ApplicationResolver
        resolver = ApplicationResolver()
        resolution = resolver.resolve(query)

        res_dict = {
            "query": resolution.query,
            "status": resolution.status,
            "match_type": resolution.match_type,
        }

        if resolution.status == "RESOLVED" and resolution.application:
            res_dict["application"] = {
                "application_id": resolution.application.application_id,
                "name": resolution.application.name,
                "version": resolution.application.version,
                "publisher": resolution.application.publisher
            }
        elif resolution.status == "AMBIGUOUS":
            res_dict["candidates"] = [
                {
                    "application_id": cand.application_id,
                    "name": cand.name,
                    "version": cand.version,
                    "publisher": cand.publisher
                }
                for cand in resolution.candidates
            ]

        return res_dict


class LaunchApplicationTool(BaseTool):
    """Tool to launch a previously resolved application using its trusted ID."""

    @property
    def name(self) -> str:
        return "launch_application"

    @property
    def description(self) -> str:
        return (
            "Launch a trusted application by its deterministic application ID. "
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
                    "application_id": {
                        "type": "string",
                        "description": "The trusted deterministic ID of the application (obtained from resolve_application)."
                    }
                },
                "required": ["application_id"]
            }
        }

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        app_id = kwargs.get("application_id")
        if not app_id or not isinstance(app_id, str) or not app_id.strip():
            raise ToolExecutionError("Application ID must be a non-empty string.")

        from app.services.applications.resolver import ApplicationResolver
        from app.services.applications.launcher import ApplicationLauncher

        resolver = ApplicationResolver()
        app = resolver.get_by_id(app_id)
        if not app:
            # Fall back to resolving the ID as a query/name/alias
            resolution = resolver.resolve(app_id)
            if resolution.status == "RESOLVED" and resolution.application:
                app = resolution.application
            else:
                raise ToolExecutionError(f"Application ID '{app_id}' could not be resolved or is unknown.")

        launcher = ApplicationLauncher()
        return launcher.launch(app)
