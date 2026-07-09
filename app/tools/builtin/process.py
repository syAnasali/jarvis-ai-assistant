"""Built-in process inspection tools."""

import psutil
from typing import Any, Dict, List
from app.tools.base import BaseTool
from app.tools.models import ToolPermission
from app.core.exceptions import ToolExecutionError
from app.config.settings import settings

class ListRunningProcessesTool(BaseTool):
    """Tool to inspect active running processes on the system."""

    @property
    def name(self) -> str:
        return "list_running_processes"

    @property
    def description(self) -> str:
        return (
            "Retrieve a list of running processes on the local machine sorted by PID. "
            "Exposes only PID, process name, and executable path if accessible."
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
                        "description": f"Optional maximum number of processes to return. Default {settings.tool_default_list_limit}, maximum 200."
                    }
                },
                "required": []
            }
        }

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        limit = kwargs.get("limit")
        if limit is None:
            limit = 50
        else:
            if limit <= 0 or limit > 200:
                raise ToolExecutionError("Limit must be between 1 and 200.")

        processes: List[Dict[str, Any]] = []
        try:
            for p in psutil.process_iter(attrs=["pid", "name", "exe"]):
                try:
                    info = p.info
                    processes.append({
                        "pid": info.get("pid"),
                        "name": info.get("name") or "",
                        "executable_path": info.get("exe") or ""
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception:
                    continue
        except Exception as e:
            raise ToolExecutionError(f"Failed to enumerate processes: {e}")

        # Deterministic sorting by PID
        processes.sort(key=lambda x: x["pid"] if x["pid"] is not None else -1)

        truncated = len(processes) > limit
        final_processes = processes[:limit]

        return {
            "processes": final_processes,
            "returned_count": len(final_processes),
            "truncated": truncated
        }


class FindRunningProcessTool(BaseTool):
    """Tool to search running processes using case-insensitive query matching."""

    @property
    def name(self) -> str:
        return "find_running_process"

    @property
    def description(self) -> str:
        return (
            "Search running processes by name using a case-insensitive query. "
            "Matches against process names and executable file names."
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
                        "description": "Case-insensitive query search pattern (e.g. 'ollama')."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Optional maximum number of matching results to return. Default 50, maximum 200."
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
            limit = 50
        else:
            if limit <= 0 or limit > 200:
                raise ToolExecutionError("Limit must be between 1 and 200.")

        query_lower = query.lower().strip()
        matches: List[Dict[str, Any]] = []

        try:
            for p in psutil.process_iter(attrs=["pid", "name", "exe"]):
                try:
                    info = p.info
                    name = info.get("name") or ""
                    exe = info.get("exe") or ""
                    
                    if query_lower in name.lower() or query_lower in exe.lower():
                        matches.append({
                            "pid": info.get("pid"),
                            "name": name,
                            "executable_path": exe
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception:
                    continue
        except Exception as e:
            raise ToolExecutionError(f"Failed to search processes: {e}")

        matches.sort(key=lambda x: x["pid"] if x["pid"] is not None else -1)

        truncated = len(matches) > limit
        final_matches = matches[:limit]

        return {
            "query": query,
            "matches": final_matches,
            "match_count": len(final_matches),
            "truncated": truncated
        }
