"""Recovery Engine handling task failure strategies, retries, rollbacks, and user prompts."""

from typing import Optional
from app.core.logger import JarvisLogger
from app.planner.interfaces import RecoveryEngine
from app.planner.models import PlanNode, RecoveryAction, VerificationResult

logger = JarvisLogger.get_logger("recovery_engine")


class AutonomousRecoveryEngine(RecoveryEngine):
    """Determines appropriate recovery action when node execution or verification fails."""

    def determine_recovery(
        self,
        node: PlanNode,
        error_text: str,
        verification: Optional[VerificationResult] = None
    ) -> RecoveryAction:
        """Evaluates node failure state and determines recovery strategy."""
        logger.info(f"Determining recovery strategy for node '{node.node_id}' (retry_count={node.retry_count}/{node.max_retries})...")

        # 1. Automatic retry if retries remaining
        if node.retry_count < node.max_retries:
            logger.info(f"Recovery strategy chosen for '{node.node_id}': RETRY (attempt {node.retry_count + 1}).")
            return RecoveryAction(
                action_type="RETRY",
                target_node_id=node.node_id,
                reason=f"Step failed with error: {error_text}. Retrying attempt {node.retry_count + 1}."
            )

        # 2. Alternative tool fallback strategy if specified in node metadata
        alt_tool = node.metadata.get("alternative_tool")
        if alt_tool:
            logger.info(f"Recovery strategy chosen for '{node.node_id}': ALTERNATIVE_TOOL ('{alt_tool}').")
            return RecoveryAction(
                action_type="ALTERNATIVE_TOOL",
                target_node_id=node.node_id,
                alternative_action=alt_tool,
                alternative_arguments=dict(node.arguments),
                reason=f"Retries exhausted. Switching to alternative tool '{alt_tool}'."
            )

        # 3. Rollback action if node declares rollback_action
        if node.rollback_action:
            logger.info(f"Recovery strategy chosen for '{node.node_id}': ROLLBACK ('{node.rollback_action}').")
            return RecoveryAction(
                action_type="ROLLBACK",
                target_node_id=node.node_id,
                alternative_action=node.rollback_action,
                reason="Verification failed after retries. Executing rollback strategy."
            )

        # 4. Prompt user if unresolvable failure
        logger.warning(f"Recovery strategy chosen for '{node.node_id}': USER_PROMPT.")
        return RecoveryAction(
            action_type="USER_PROMPT",
            target_node_id=node.node_id,
            reason=f"Node '{node.node_id}' failed: {error_text}. User intervention required."
        )
