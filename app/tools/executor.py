"""Execution runtime for resolving, validating, and executing tools."""

import time
from typing import Any, Dict
from app.tools.registry import ToolRegistry
from app.tools.models import ToolPermission, ToolResult
from app.agent.models import ToolCall
from app.core.exceptions import ToolExecutionError
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("tool_executor")


class ToolExecutor:
    """Handles controlled validation and execution of registered system tools."""

    def __init__(self, registry: ToolRegistry) -> None:
        """Initializes the ToolExecutor with a ToolRegistry.

        Args:
            registry: The ToolRegistry containing available tools.
        """
        self._registry = registry

    def execute(self, tool_call: ToolCall) -> ToolResult:
        """Resolves and executes a tool call if permissions allow.

        Args:
            tool_call: The ToolCall instance to execute.

        Returns:
            ToolResult: The normalized result of the execution.
        """
        name = tool_call.tool_name
        arguments = tool_call.arguments
        logger.info(f"Tool execution requested: '{name}'")

        try:
            # 1. Resolve tool
            tool = self._registry.get(name)

            # 2. Check permission level
            logger.info(f"Tool permission evaluated: '{name}' level={tool.permission_level.name}")
            if tool.permission_level == ToolPermission.CONFIRMATION:
                logger.warning(f"Tool execution blocked: '{name}' requires confirmation.")
                return ToolResult(
                    tool_name=name,
                    success=False,
                    error=f"Execution of tool '{name}' was blocked because it requires confirmation.",
                    metadata={"permission_level": tool.permission_level.value}
                )
            elif tool.permission_level == ToolPermission.RESTRICTED:
                logger.warning(f"Tool execution blocked: '{name}' is restricted.")
                return ToolResult(
                    tool_name=name,
                    success=False,
                    error=f"Execution of tool '{name}' was blocked because restricted tools cannot be executed.",
                    metadata={"permission_level": tool.permission_level.value}
                )

            # 3. Validate arguments
            tool.validate_arguments(arguments)

            # 4. Execute tool
            logger.info(f"Tool execution started: '{name}'")
            start_time = time.perf_counter()
            output = tool.execute(**arguments)
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(f"Tool execution completed: '{name}' in {duration_ms:.2f} ms")

            return ToolResult(
                tool_name=name,
                success=True,
                output=output,
                metadata={
                    "execution_time_ms": duration_ms,
                    "permission_level": tool.permission_level.value
                }
            )

        except ToolExecutionError as tee:
            logger.error(f"Tool execution failed (validation/registry): {tee}")
            return ToolResult(
                tool_name=name,
                success=False,
                error=str(tee),
                metadata={}
            )
        except Exception as e:
            logger.error(f"Tool execution failed (runtime): {e}")
            return ToolResult(
                tool_name=name,
                success=False,
                error=f"Runtime error during tool execution: {e}",
                metadata={}
            )
