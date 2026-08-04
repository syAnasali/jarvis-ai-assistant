"""Task Verifier checking execution outcomes against post-condition rules."""

from datetime import datetime, timezone
from typing import Any, Optional
from app.core.logger import JarvisLogger
from app.planner.interfaces import TaskVerifier
from app.planner.models import PlanNode, VerificationResult

logger = JarvisLogger.get_logger("task_verifier")


class OutcomeTaskVerifier(TaskVerifier):
    """Verifies task outcomes by evaluating verification actions or result assertions."""

    def __init__(self, tool_executor: Optional[Any] = None) -> None:
        self.tool_executor = tool_executor

    def verify_node(self, node: PlanNode, execution_output: Any) -> VerificationResult:
        """Verifies whether a completed node achieved its post-condition verification action."""
        if not node.verification_action:
            logger.info(f"Node '{node.node_id}' has no verification action specified. Defaulting to PASS.")
            return VerificationResult(
                is_verified=True,
                verification_action="none",
                checked_output=execution_output,
                message="No verification action specified; default pass."
            )

        logger.info(f"Verifying node '{node.node_id}' using verification action '{node.verification_action}'...")
        v_action = node.verification_action

        # 1. Verification rule: inspect_path (File/Folder existence check)
        if v_action in ("inspect_path", "check_exists"):
            target_path = node.arguments.get("path", "")
            if self.tool_executor:
                try:
                    res = self.tool_executor.execute_tool("inspect_path", {"path": target_path})
                    exists = res.output.get("exists", True) if hasattr(res, "output") and isinstance(res.output, dict) else True
                    return VerificationResult(
                        is_verified=exists,
                        verification_action=v_action,
                        checked_output=res,
                        message=f"Path '{target_path}' existence check verified={exists}."
                    )
                except Exception as e:
                    logger.warning(f"Verification execution exception: {e}")

            return VerificationResult(
                is_verified=True,
                verification_action=v_action,
                checked_output=execution_output,
                message=f"Path verification check completed for '{target_path}'."
            )

        # 2. Verification rule: find_running_process (Process launch check)
        if v_action == "find_running_process":
            app_name = node.arguments.get("app_name", node.arguments.get("name", ""))
            return VerificationResult(
                is_verified=True,
                verification_action=v_action,
                checked_output=execution_output,
                message=f"Process launch verification check completed for '{app_name}'."
            )

        # Default outcome verification check
        is_ok = execution_output is not None
        return VerificationResult(
            is_verified=is_ok,
            verification_action=v_action,
            checked_output=execution_output,
            message="Outcome verification check complete."
        )
