"""Execution mode router based on request analysis."""

from app.agent.models import AgentRequest
from app.planning.models import ExecutionMode, PlanningDecision


class ExecutionRouter:
    """Deterministic heuristic router for classifying requests as DIRECT or PLANNED."""

    def route(self, request: AgentRequest) -> PlanningDecision:
        """Analyzes the agent request using lightweight heuristics to decide execution mode.

        Args:
            request: The incoming user AgentRequest.

        Returns:
            PlanningDecision: The routing decision.
        """
        text = request.text.lower().strip()
        score = 0.0
        signals = []

        # Connectors indicating sequential multi-part steps
        connectors = ["then", "after that", "finally", "afterwards"]
        for conn in connectors:
            if conn in text:
                score += 0.4
                signals.append(f"connector:{conn}")

        # Planning / analytical verbs
        verbs = ["compare", "evaluate", "analyze", "summarize", "recommend", "gather", "inspect"]
        for verb in verbs:
            # Match word boundary
            if f" {verb}" in f" {text}" or text.startswith(verb):
                score += 0.3
                signals.append(f"verb:{verb}")

        # Check for 'check' verb specifically
        if "check" in text:
            if f" check" in f" {text}" or text.startswith("check"):
                # 'check' is scored lower to prevent false positives on simple queries like "check the time"
                score += 0.15
                signals.append("verb:check")

        # Conjunction indicators with multiple verbs
        if "and" in text:
            # Check if any planning verb is present
            all_verbs = verbs + ["check"]
            has_planning_verb = any(f" {v}" in f" {text}" or text.startswith(v) for v in all_verbs)
            if has_planning_verb:
                # Count distinct planning verbs found
                verbs_found = sum(1 for v in all_verbs if f" {v}" in f" {text}" or text.startswith(v))
                if verbs_found >= 2 or any(c in text for c in connectors):
                    score += 0.25
                    signals.append("multi_action_conjunction")

        # Decide execution mode
        confidence = min(max(score, 0.0), 1.0)
        metadata = {
            "signals": list(signals),
            "score": score
        }

        if score >= 0.5:
            mode = ExecutionMode.PLANNED
            reason = f"Request contains planning signals: {', '.join(signals)}"
        else:
            mode = ExecutionMode.DIRECT
            reason = "Single-part or simple request"

        return PlanningDecision(
            mode=mode,
            confidence=confidence,
            reason=reason,
            metadata=metadata
        )
