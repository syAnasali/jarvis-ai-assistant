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

    def __init__(self, registry: ToolRegistry, approval_manager: Any = None) -> None:
        """Initializes the ToolExecutor with a ToolRegistry.

        Args:
            registry: The ToolRegistry containing available tools.
            approval_manager: Optional ApprovalManager instance.
        """
        self._registry = registry
        self._approval_manager = approval_manager

    def execute(self, tool_call: ToolCall, approval_action_id: str | None = None) -> ToolResult:
        """Resolves and executes a tool call if permissions allow.

        Args:
            tool_call: The ToolCall instance to execute.
            approval_action_id: Optional ID of the approved PendingAction.

        Returns:
            ToolResult: The normalized result of the execution.
        """
        name = tool_call.tool_name
        arguments = tool_call.arguments
        logger.info(f"Tool execution requested: '{name}' (approval_id={approval_action_id})")

        try:
            # 1. Resolve tool
            tool = self._registry.get(name)

            # 2. Check permission level
            logger.info(f"Tool permission evaluated: '{name}' level={tool.permission_level.name}")
            if tool.permission_level == ToolPermission.CONFIRMATION:
                if approval_action_id is not None and self._approval_manager is not None:
                    # Validate and consume approval first
                    try:
                        self._approval_manager.consume_approved_action(approval_action_id, name, arguments)
                    except Exception as e:
                        logger.warning(f"Failed to authorize and consume approved action '{approval_action_id}': {e}")
                        return ToolResult(
                            tool_name=name,
                            success=False,
                            error=f"Tool execution authorization failed: {e}",
                            metadata={"permission_level": tool.permission_level.value}
                        )
                    logger.info(f"Action '{approval_action_id}' successfully consumed. Proceeding with tool execution.")
                else:
                    if self._approval_manager is None:
                        logger.warning(f"Tool execution blocked: '{name}' requires confirmation, but no approval manager is available.")
                        return ToolResult(
                            tool_name=name,
                            success=False,
                            error=f"Execution of tool '{name}' was blocked because it requires confirmation.",
                            metadata={"permission_level": tool.permission_level.value}
                        )
                    
                    metadata = {}
                    if hasattr(tool, "get_approval_metadata"):
                        try:
                            metadata = tool.get_approval_metadata(arguments)
                        except Exception as e:
                            logger.error(f"Failed to generate approval metadata: {e}")

                    from app.approval.policy import generate_approval_reason
                    reason = generate_approval_reason(tool)
                    action = self._approval_manager.create_pending_action(
                        tool_name=name,
                        arguments=arguments,
                        permission_level=tool.permission_level,
                        reason=reason,
                        metadata=metadata
                    )
                    logger.warning(f"Tool execution suspended: '{name}' requires confirmation. PendingAction ID: {action.action_id}")
                    return ToolResult(
                        tool_name=name,
                        success=False,
                        error=f"Execution of tool '{name}' was blocked because it requires confirmation. PendingAction ID: {action.action_id}",
                        metadata={
                            "confirmation_required": True,
                            "pending_action_id": action.action_id,
                            "tool_name": name,
                            "permission_level": tool.permission_level.value,
                            "reason": reason
                        }
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
            if hasattr(tool, "current_approval_action_id"):
                tool.current_approval_action_id = approval_action_id
            try:
                output = tool.execute(**arguments)
            finally:
                if hasattr(tool, "current_approval_action_id"):
                    tool.current_approval_action_id = None
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
