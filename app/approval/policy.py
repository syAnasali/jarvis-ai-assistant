"""Security policy and confirmation reasoning helper functions."""

from typing import Any
from app.tools.base import BaseTool
from app.tools.models import ToolPermission


def requires_approval(tool: BaseTool) -> bool:
    """Checks if a tool requires explicit approval under current system policies."""
    return tool.permission_level == ToolPermission.CONFIRMATION


def generate_approval_reason(tool: BaseTool) -> str:
    """Generates a concise, deterministic description for why approval is required.

    Avoids trusting unrestricted LLM explanations.
    """
    # Check if tool defines a custom confirmation description
    if hasattr(tool, "confirmation_description") and isinstance(tool.confirmation_description, str):
        if tool.confirmation_description.strip():
            return tool.confirmation_description.strip()

    # Fallback to deterministic description based on name, description, and permission level
    desc = tool.description.strip()
    # Truncate description if too long
    if len(desc) > 100:
        desc = desc[:97] + "..."
    return f"Request to run '{tool.name}' requires explicit approval (level: {tool.permission_level.value}). Reason: {desc}"
