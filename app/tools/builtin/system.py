"""Built-in system tools."""

import platform
from datetime import datetime
from typing import Dict, Any
from app.tools.base import BaseTool
from app.tools.models import ToolPermission


class CurrentTimeTool(BaseTool):
    """Tool to retrieve the current local date and time."""

    @property
    def name(self) -> str:
        return "get_current_time"

    @property
    def description(self) -> str:
        return "Return the current local date and time."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.SAFE

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }

    def execute(self, **kwargs: Any) -> Dict[str, str]:
        """Returns the current date, time, timezone, and ISO timestamp.

        Args:
            kwargs: Unused keyword arguments.

        Returns:
            Dict[str, str]: Dictionary mapping time components.
        """
        now = datetime.now().astimezone()
        return {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "timezone": now.tzname() or "Local",
            "iso_datetime": now.isoformat()
        }


class SystemInfoTool(BaseTool):
    """Tool to retrieve basic non-sensitive operating system and Python runtime information."""

    @property
    def name(self) -> str:
        return "get_system_info"

    @property
    def description(self) -> str:
        return "Return basic non-sensitive operating system and Python runtime information."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.SAFE

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }

    def execute(self, **kwargs: Any) -> Dict[str, str]:
        """Returns non-sensitive platform diagnostic information.

        Args:
            kwargs: Unused keyword arguments.

        Returns:
            Dict[str, str]: System specification mappings.
        """
        return {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version()
        }
