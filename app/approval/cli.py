"""Terminal approval helper for confirmation tool calls."""

import sys
from typing import Any, Dict, Optional


def prompt_user_approval(
    tool_name: str,
    reason: str,
    arguments: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """Displays action details and prompts the user for explicit approval in the CLI.

    KeyboardInterrupt or EOF defaults to rejection.
    """
    metadata = metadata or {}

    if tool_name == "launch_application":
        app_id = arguments.get("application_id", "")
        from app.services.applications.resolver import ApplicationResolver
        resolver = ApplicationResolver()
        app = resolver.get_by_id(app_id)
        app_name = app.name if app else "Unknown Application"

        sys.stdout.write("\n==========================================================\n")
        sys.stdout.write("Jarvis wants to perform an action requiring confirmation.\n\n")
        sys.stdout.write("Action:\n")
        sys.stdout.write(f"  Launch application: {app_name}\n")
        sys.stdout.write("==========================================================\n")
        sys.stdout.flush()

    elif tool_name in ("create_directory", "write_text_file", "move_path", "delete_path"):
        sys.stdout.write("\n==========================================================\n")
        sys.stdout.write("Jarvis wants to perform an action requiring confirmation.\n\n")
        sys.stdout.write("Action:\n")

        if tool_name == "create_directory":
            root = arguments.get("root", "")
            rel = arguments.get("relative_path", "")
            path_str = f"{root}\\{rel}".replace("/", "\\").replace("\\\\", "\\")
            sys.stdout.write(f"  Create directory: {path_str}\n")

        elif tool_name == "write_text_file":
            root = arguments.get("root", "")
            rel = arguments.get("relative_path", "")
            path_str = f"{root}\\{rel}".replace("/", "\\").replace("\\\\", "\\")
            action_verb = "Overwrite text file" if metadata.get("overwrite") else "Create text file"
            sys.stdout.write(f"  {action_verb}: {path_str}\n")

        elif tool_name == "move_path":
            src_root = arguments.get("source_root", "")
            src_rel = arguments.get("source_relative_path", "")
            dest_root = arguments.get("destination_root", "")
            dest_rel = arguments.get("destination_relative_path", "")
            src_str = f"{src_root}\\{src_rel}".replace("/", "\\").replace("\\\\", "\\")
            dest_str = f"{dest_root}\\{dest_rel}".replace("/", "\\").replace("\\\\", "\\")
            sys.stdout.write(f"  Move: {src_str}\n")
            sys.stdout.write(f"  To: {dest_str}\n")

        elif tool_name == "delete_path":
            root = arguments.get("root", "")
            rel = arguments.get("relative_path", "")
            path_str = f"{root}\\{rel}".replace("/", "\\").replace("\\\\", "\\")
            is_dir = metadata.get("is_dir", False)
            recursive = arguments.get("recursive", False)
            if is_dir:
                if recursive:
                    action_desc = f"Recursively delete directory: {path_str}"
                else:
                    action_desc = f"Delete empty directory: {path_str}"
            else:
                action_desc = f"Delete file: {path_str}"
            sys.stdout.write(f"  {action_desc}\n")

        sys.stdout.write("==========================================================\n")
        sys.stdout.flush()

    elif tool_name in ("focus_window", "type_text", "press_key", "press_hotkey", "click_screen"):
        sys.stdout.write("\n==========================================================\n")
        sys.stdout.write("Jarvis wants to perform an action requiring confirmation.\n\n")
        sys.stdout.write("Action:\n")

        if tool_name == "focus_window":
            win_title = metadata.get("window_title", "Unknown Window")
            proc_name = metadata.get("process_name", "Unknown Process")
            sys.stdout.write(f"  Focus window: {win_title}\n")
            sys.stdout.write(f"  Process: {proc_name}\n")

        elif tool_name == "type_text":
            win_title = metadata.get("expected_foreground_window_title", "Unknown Window")
            char_count = metadata.get("character_count", 0)
            preview = metadata.get("preview", "")
            sys.stdout.write(f"  Type text into: {win_title}\n")
            sys.stdout.write(f"  Characters: {char_count}\n")
            sys.stdout.write(f"  Preview: {preview}\n")

        elif tool_name == "press_key":
            win_title = metadata.get("expected_foreground_window_title", "Unknown Window")
            key = arguments.get("key", "")
            sys.stdout.write(f"  Press key: {key.capitalize()}\n")
            sys.stdout.write(f"  Target window: {win_title}\n")

        elif tool_name == "press_hotkey":
            win_title = metadata.get("expected_foreground_window_title", "Unknown Window")
            keys = arguments.get("keys", [])
            shortcut_str = "+".join(str(k).capitalize() for k in keys)
            sys.stdout.write(f"  Press shortcut: {shortcut_str}\n")
            sys.stdout.write(f"  Target window: {win_title}\n")

        elif tool_name == "click_screen":
            win_title = metadata.get("expected_foreground_window_title", "Unknown Window")
            x = arguments.get("x", 0)
            y = arguments.get("y", 0)
            button = arguments.get("button", "left")
            sys.stdout.write(f"  Click {button.lower()} mouse button\n")
            sys.stdout.write(f"  Position: ({x}, {y})\n")
            sys.stdout.write(f"  Target window: {win_title}\n")

        sys.stdout.write("==========================================================\n")
        sys.stdout.flush()

    else:
        sys.stdout.write("\n==========================================================\n")
        sys.stdout.write("Jarvis wants to perform an action requiring confirmation.\n\n")
        sys.stdout.write("Action:\n")
        sys.stdout.write(f"  Tool: {tool_name}\n")
        sys.stdout.write(f"  Reason: {reason}\n")
        sys.stdout.write("  Arguments:\n")

        for key, val in arguments.items():
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
