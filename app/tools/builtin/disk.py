"""Built-in disk inspection tools."""

import os
import shutil
from typing import Any, Dict
from app.tools.base import BaseTool
from app.tools.models import ToolPermission
from app.core.exceptions import ToolExecutionError
from app.tools.builtin.filesystem import validate_and_resolve_path

class GetDiskUsageTool(BaseTool):
    """Tool to inspect disk space metrics for a specified target path."""

    @property
    def name(self) -> str:
        return "get_disk_usage"

    @property
    def description(self) -> str:
        return (
            "Retrieve disk space information (total, used, free, and used percentage) "
            "for a given path directory. Defaults to the system drive."
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
                        "description": "Optional path directory on the target drive to inspect. Defaults to the system drive."
                    }
                },
                "required": []
            }
        }

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        # Handle optional path argument and resolve default SystemDrive
        path = kwargs.get("path")
        if path is None:
            path = os.getenv("SystemDrive", "C:") + "\\"

        # Validate path
        resolved = validate_and_resolve_path(path)

        try:
            total, used, free = shutil.disk_usage(resolved)
        except Exception as e:
            raise ToolExecutionError(f"Failed to inspect disk usage: {e}")

        used_percent = (used / total * 100.0) if total > 0 else 0.0

        return {
            "path": resolved,
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": free,
            "used_percent": round(used_percent, 2)
        }
