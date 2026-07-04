"""Registry for discovering and managing system tools."""

from typing import Dict, List, Any
from app.tools.base import BaseTool
from app.core.exceptions import ToolExecutionError
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("tool_registry")


class ToolRegistry:
    """Registry managing available BaseTool instances."""

    def __init__(self) -> None:
        """Initializes an empty ToolRegistry."""
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Registers a tool in the registry.

        Args:
            tool: The BaseTool instance to register.

        Raises:
            ToolExecutionError: If a tool with the same name is already registered.
        """
        name = tool.name
        if name in self._tools:
            raise ToolExecutionError(f"Tool with name '{name}' is already registered.")
        self._tools[name] = tool
        logger.info(f"Tool registered: '{name}'")

    def remove(self, name: str) -> None:
        """Removes a tool from the registry.

        Args:
            name: The name of the tool to remove.

        Raises:
            ToolExecutionError: If the tool does not exist in the registry.
        """
        if name not in self._tools:
            raise ToolExecutionError(f"Cannot remove unregistered tool: '{name}'.")
        del self._tools[name]
        logger.info(f"Tool removed: '{name}'")

    def get(self, name: str) -> BaseTool:
        """Retrieves a registered tool by its name.

        Args:
            name: The name of the tool.

        Returns:
            BaseTool: The registered tool instance.

        Raises:
            ToolExecutionError: If the tool is not registered.
        """
        if name not in self._tools:
            raise ToolExecutionError(f"Tool '{name}' is not registered.")
        return self._tools[name]

    def has(self, name: str) -> bool:
        """Checks if a tool with the given name is registered.

        Args:
            name: The name of the tool.

        Returns:
            bool: True if registered, False otherwise.
        """
        return name in self._tools

    def list_tools(self) -> List[str]:
        """Lists the names of all registered tools.

        Returns:
            List[str]: List of registered tool names.
        """
        return list(self._tools.keys())

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Returns schema specifications for all registered tools.

        Returns:
            List[Dict[str, Any]]: List of tool schemas.
        """
        return [tool.get_schema() for tool in self._tools.values()]
