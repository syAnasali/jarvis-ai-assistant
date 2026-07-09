"""Terminal approval helper for confirmation tool calls."""

import sys
from typing import Any, Dict


def prompt_user_approval(tool_name: str, reason: str, arguments: Dict[str, Any]) -> bool:
    """Displays action details and prompts the user for explicit approval in the CLI.

    KeyboardInterrupt or EOF defaults to rejection.
    """
    sys.stdout.write("\n==========================================================\n")
    sys.stdout.write("Jarvis wants to perform an action requiring confirmation.\n\n")
    sys.stdout.write("Action:\n")
    sys.stdout.write(f"  Tool: {tool_name}\n")
    sys.stdout.write(f"  Reason: {reason}\n")
    sys.stdout.write("  Arguments:\n")
    
    for key, val in arguments.items():
        # Basic mask to prevent printing obvious secrets in terminal
        key_lower = key.lower()
        if any(s in key_lower for s in ("password", "secret", "token", "key", "auth")):
            display_val = "********"
        else:
            display_val = str(val)
        sys.stdout.write(f"    {key}: {display_val}\n")
        
    sys.stdout.write("==========================================================\n")
    sys.stdout.flush()

    try:
        user_input = input("\nApprove this action? [y/N]: ").strip().lower()
        return user_input in ("y", "yes")
    except (KeyboardInterrupt, EOFError):
        sys.stdout.write("\nAction approval interrupted. Defaulting to reject.\n")
        sys.stdout.flush()
        return False
