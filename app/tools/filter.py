"""Dynamic tool schema filtering based on request intent."""

import re
from typing import Any, Dict, List
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("tool_filter")


class ToolFilter:
    """Filters registered tool schemas to inject only query-relevant tools into LLM prompts."""

    CATEGORY_MAP = {
        "time": ["get_current_time"],
        "system": ["get_system_info", "get_disk_usage", "list_running_processes", "find_running_process"],
        "application": ["list_installed_applications", "find_installed_application", "resolve_application", "launch_application"],
        "filesystem": ["inspect_path", "list_directory", "create_directory", "create_file", "write_text_file", "move_path", "delete_path"],
        "desktop": ["get_active_window", "list_visible_windows", "focus_window", "type_text", "press_key", "press_hotkey", "click_screen"],
    }

    KEYWORD_PATTERNS = {
        "time": [r"\btime\b", r"\bdate\b", r"\bclock\b", r"\bhour\b", r"\bnow\b", r"\bday\b"],
        "system": [r"\bsystem\b", r"\bdisk\b", r"\bprocess\b", r"\bcpu\b", r"\bram\b", r"\bmemory\b", r"\busage\b", r"\bspecs\b"],
        "application": [r"\bopen\b", r"\blaunch\b", r"\bstart\b", r"\bapp\b", r"\bapplication\b", r"\bnotepad\b", r"\bchrome\b", r"\bcalc\b", r"\bcalculator\b", r"\bfind app\b", r"\binstalled\b"],
        "filesystem": [r"\bfolder\b", r"\bfile\b", r"\bdirectory\b", r"\bdesktop\b", r"\bdownloads\b", r"\bdocuments\b", r"\bpath\b", r"\bwrite\b", r"\bread\b", r"\bdelete\b", r"\bmove\b", r"\binspect\b", r"\bcreate\b", r"\blist dir\b"],
        "desktop": [r"\bwindow\b", r"\bfocus\b", r"\btype\b", r"\bclick\b", r"\bkey\b", r"\bhotkey\b", r"\bscreen\b", r"\bpress\b", r"\bactive window\b"],
    }

    GENERAL_CHAT_PATTERNS = [
        r"^\s*(hello|hi|hey|how are you|thanks|thank you|good morning|good evening|who are you)\b"
    ]

    @classmethod
    def select_relevant_tools(cls, query: str, schemas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filters available tool schemas down to those relevant to the query.

        Args:
            query: The incoming user request text.
            schemas: List of all registered tool schema dictionaries.

        Returns:
            List[Dict[str, Any]]: Filtered list of relevant tool schemas.
        """
        if not query or not schemas:
            return []

        q_lower = query.lower().strip()

        # 1. Pure general conversation check
        is_general_chat = False
        for pat in cls.GENERAL_CHAT_PATTERNS:
            if re.search(pat, q_lower):
                is_general_chat = True
                break

        if is_general_chat:
            logger.info("Query matched general conversation pattern. Injecting 0 tool schemas.")
            return []

        # 2. Match standard categories and tool names
        matched_categories = set()
        for category, patterns in cls.KEYWORD_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, q_lower):
                    matched_categories.add(category)
                    break

        allowed_tool_names = set()
        for cat in matched_categories:
            allowed_tool_names.update(cls.CATEGORY_MAP.get(cat, []))

        # Check tool names directly mentioned in query
        for schema in schemas:
            tool_name = schema.get("name", "") or schema.get("function", {}).get("name", "")
            if tool_name and tool_name.lower() in q_lower:
                allowed_tool_names.add(tool_name)

        filtered_schemas = []
        for schema in schemas:
            tool_name = schema.get("name", "") or schema.get("function", {}).get("name", "")
            if tool_name in allowed_tool_names:
                filtered_schemas.append(schema)

        # 3. Fallback for unclassified / test queries (non-conversational text without specific keywords)
        if not filtered_schemas and not is_general_chat:
            logger.info(f"Query '{query}' not explicitly matched to a standard category; passing all {len(schemas)} registered schemas.")
            return schemas

        logger.info(f"Dynamic tool filter: {len(filtered_schemas)} / {len(schemas)} schemas injected for categories {list(matched_categories)}.")
        return filtered_schemas
