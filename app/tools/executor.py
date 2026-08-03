"""Execution runtime for resolving, validating, and executing tools with timeout and recovery protection."""

import time
import concurrent.futures
from typing import Any, Dict
from app.tools.registry import ToolRegistry
from app.tools.models import ToolPermission, ToolResult
from app.agent.models import ToolCall
from app.config.settings import settings
from app.core.exceptions import ToolExecutionError, ToolValidationError, ToolTimeoutError, ToolCancelledError
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("tool_executor")


class ToolExecutor:
    """Handles controlled validation, timeout protection, cancellation, and execution of registered system tools."""

    def __init__(self, registry: ToolRegistry, approval_manager: Any = None) -> None:
        """Initializes the ToolExecutor with a ToolRegistry.

        Args:
            registry: The ToolRegistry containing available tools.
            approval_manager: Optional ApprovalManager instance.
        """
        self._registry = registry
        self._approval_manager = approval_manager
        self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="tool_exec")
        self._cancel_requested = False
        self._timeouts_count = 0
        self._cancellations_count = 0

    @property
    def timeouts_count(self) -> int:
        return self._timeouts_count

    @property
    def cancellations_count(self) -> int:
        return self._cancellations_count

    def cancel_execution(self) -> None:
        """Flags cancellation for active/pending tool execution."""
        self._cancel_requested = True
        logger.warning("Tool execution cancellation requested.")

    def reset_cancellation(self) -> None:
        """Resets the cancellation flag."""
        self._cancel_requested = False

    def shutdown(self) -> None:
        """Gracefully halts the tool executor worker pool."""
        try:
            self._pool.shutdown(wait=False, cancel_futures=True)
        except Exception as e:
            logger.error(f"Error shutting down tool executor pool: {e}")

    def execute(self, tool_call: ToolCall, approval_action_id: str | None = None) -> ToolResult:
        """Resolves and executes a tool call if permissions allow with timeout and cancellation protection.

        Args:
            tool_call: The ToolCall instance to execute.
            approval_action_id: Optional ID of the approved PendingAction.

        Returns:
            ToolResult: The normalized result of the execution.
        """
        name = tool_call.tool_name
        arguments = tool_call.arguments
        logger.info(f"Tool execution requested: '{name}' (approval_id={approval_action_id})")

        if self._cancel_requested:
            self._cancellations_count += 1
            self.reset_cancellation()
            logger.warning(f"Tool execution cancelled before launch: '{name}'")
            return ToolResult(
                tool_name=name,
                success=False,
                error=f"Execution of tool '{name}' was cancelled.",
                metadata={"cancelled": True}
            )

        try:
            # 1. Resolve tool
            tool = self._registry.get(name)

            # 2. Validate arguments BEFORE checking permission level
            tool.validate_arguments(arguments)
            
            # 3. Check permission level
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
                    logger.info(f"Pending action created: action_id={action.action_id} tool_name={name}")
                    logger.info(f"Waiting for approval: action_id={action.action_id} tool={name}")
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

            # 4. Execute tool with timeout protection
            logger.info(f"Tool execution started: tool_name={name}")
            logger.info(f"Tool execution started: '{name}'")
            start_time = time.perf_counter()
            if hasattr(tool, "current_approval_action_id"):
                tool.current_approval_action_id = approval_action_id

            timeout_sec = getattr(tool, "timeout_seconds", None) or settings.tool_execution_timeout

            def _run_tool():
                return tool.execute(**arguments)

            try:
                future = self._pool.submit(_run_tool)
                output = future.result(timeout=timeout_sec)
            except concurrent.futures.TimeoutError:
                self._timeouts_count += 1
                logger.error(f"Tool execution timed out after {timeout_sec}s: tool_name={name}")
                raise ToolTimeoutError(f"Tool '{name}' execution timed out after {timeout_sec} seconds.")
            finally:
                if hasattr(tool, "current_approval_action_id"):
                    tool.current_approval_action_id = None
                if hasattr(tool, "cleanup"):
                    try:
                        tool.cleanup()
                    except Exception as cl_err:
                        logger.error(f"Error during tool cleanup for '{name}': {cl_err}")

            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(f"Tool execution completed: tool_name={name}")
            logger.info(f"Tool execution completed: '{name}' in {duration_ms:.2f} ms")
            
            if name in ("create_file", "write_text_file", "move_path", "delete_path", "create_directory", "inspect_path", "list_directory", "read_text_file"):
                logger.info(f"Filesystem result: {output}")

            return ToolResult(
                tool_name=name,
                success=True,
                output=output,
                metadata={
                    "execution_time_ms": duration_ms,
                    "permission_level": tool.permission_level.value
                }
            )

        except ToolTimeoutError as tto:
            return ToolResult(
                tool_name=name,
                success=False,
                error=str(tto),
                metadata={"timeout": True, "partial_failure": True}
            )
        except ToolCancelledError as tce:
            return ToolResult(
                tool_name=name,
                success=False,
                error=str(tce),
                metadata={"cancelled": True, "partial_failure": True}
            )
        except ToolValidationError as tve:
            logger.error(f"Tool validation failed: {tve}")
            if name in ("create_file", "write_text_file", "move_path", "delete_path", "create_directory", "inspect_path", "list_directory", "read_text_file"):
                logger.info(f"Filesystem result: error={tve}")
            return ToolResult(
                tool_name=name,
                success=False,
                error=str(tve),
                metadata={"validation_failed": True}
            )
        except ToolExecutionError as tee:
            logger.error(f"Tool execution failed (validation/registry): {tee}")
            if name in ("create_file", "write_text_file", "move_path", "delete_path", "create_directory", "inspect_path", "list_directory", "read_text_file"):
                logger.info(f"Filesystem result: error={tee}")
            return ToolResult(
                tool_name=name,
                success=False,
                error=str(tee),
                metadata={"partial_failure": True}
            )
        except Exception as e:
            logger.error(f"Tool execution failed (runtime): {e}")
            if name in ("create_file", "write_text_file", "move_path", "delete_path", "create_directory", "inspect_path", "list_directory", "read_text_file"):
                logger.info(f"Filesystem result: error={e}")
            return ToolResult(
                tool_name=name,
                success=False,
                error=f"Runtime error during tool execution: {e}",
                metadata={"partial_failure": True}
            )
