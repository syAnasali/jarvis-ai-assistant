"""Internal diagnostic utilities for developer inspection."""

from typing import Any, Dict, List
from app.core.container import ServiceContainer


class DiagnosticsProvider:
    """Provides internal inspection utilities for application components."""

    @staticmethod
    def get_registered_tools_info(container: ServiceContainer) -> List[Dict[str, Any]]:
        """Returns details of all registered tools."""
        if not container.has("tool_registry"):
            return []
        registry = container.get("tool_registry")
        tools_info = []
        for name, tool in registry._tools.items():
            tools_info.append({
                "name": name,
                "permission_level": tool.permission_level.value,
                "description": tool.description.split("\n")[0]
            })
        return sorted(tools_info, key=lambda x: x["name"])

    @staticmethod
    def get_loaded_config_info(container: ServiceContainer) -> Dict[str, Any]:
        """Returns non-sensitive active configuration settings."""
        if not container.has("settings"):
            return {}
        settings = container.get("settings")
        res = {}
        for field_name in settings.model_fields.keys():
            val = getattr(settings, field_name)
            # Mask sensitive fields
            if any(k in field_name.lower() for k in ("password", "secret", "token", "key", "auth")):
                val = "********"
            res[field_name] = str(val)
        return res

    @staticmethod
    def get_provider_status_info(container: ServiceContainer) -> Dict[str, Any]:
        """Returns LLM provider and scheduler status."""
        status = {}
        if container.has("llm_manager"):
            llm_manager = container.get("llm_manager")
            status["active_provider"] = llm_manager.active_provider_name
            status["active_model"] = llm_manager.active_model_name
        if container.has("inference_scheduler"):
            scheduler = container.get("inference_scheduler")
            status["scheduler_queue_depth"] = scheduler.queue_depth
            status["scheduler_is_active"] = scheduler.is_active
        return status

    @staticmethod
    def get_memory_stats_info(container: ServiceContainer) -> Dict[str, Any]:
        """Returns memory repository statistics."""
        if not container.has("memory_repository"):
            return {}
        repo = container.get("memory_repository")
        try:
            memories = repo.get_all()
            return {
                "total_memories": len(memories),
                "categories": list(set(m.category for m in memories))
            }
        except Exception:
            return {"total_memories": 0, "categories": []}

    @staticmethod
    def get_planner_stats_info(container: ServiceContainer) -> Dict[str, Any]:
        """Returns planner status and configuration."""
        if not container.has("settings"):
            return {}
        settings = container.get("settings")
        return {
            "planning_enabled": settings.planning_enabled,
            "max_steps": settings.planning_max_steps,
            "max_retries": settings.planning_max_retries
        }

    @staticmethod
    def get_conversation_stats_info(container: ServiceContainer) -> Dict[str, Any]:
        """Returns conversation repository statistics."""
        if not container.has("conversation_repository"):
            return {}
        repo = container.get("conversation_repository")
        try:
            sessions = repo.list_sessions()
            return {
                "total_sessions": len(sessions),
                "active_session": str(container.get("conversation_active_session").session_id) if container.has("conversation_active_session") else None
            }
        except Exception:
            return {"total_sessions": 0}

    @staticmethod
    def get_prompt_diagnostics_info(container: ServiceContainer) -> Dict[str, Any]:
        """Returns prompt and context optimization configuration and status."""
        if not container.has("settings"):
            return {}
        settings = container.get("settings")
        return {
            "max_context_messages": settings.conversation_context_max_messages,
            "max_context_characters": settings.conversation_context_max_characters,
            "dynamic_tool_filtering": True,
            "memory_deduplication": True,
            "static_prompt_caching": True,
            "concise_planner_prompts": True
        }

    @staticmethod
    def get_recovery_diagnostics_info(container: ServiceContainer) -> Dict[str, Any]:
        """Returns runtime reliability and recovery diagnostics."""
        recovery_info = {
            "retry_count": 0,
            "recovery_success": 0,
            "provider_reconnects": 0,
            "timeouts": 0,
            "cancellations": 0
        }
        if container.has("llm_manager"):
            llm_manager = container.get("llm_manager")
            recovery_info["retry_count"] = getattr(llm_manager, "retry_count", 0)
            recovery_info["recovery_success"] = getattr(llm_manager, "recovery_success_count", 0)
            recovery_info["provider_reconnects"] = getattr(llm_manager, "provider_reconnect_count", 0)
        if container.has("tool_executor"):
            executor = container.get("tool_executor")
            recovery_info["timeouts"] = getattr(executor, "timeouts_count", 0)
            recovery_info["cancellations"] = getattr(executor, "cancellations_count", 0)
        return recovery_info

    @classmethod
    def get_all_diagnostics(cls, container: ServiceContainer) -> Dict[str, Any]:
        """Collects a complete internal developer diagnostics report."""
        return {
            "tools": cls.get_registered_tools_info(container),
            "config": cls.get_loaded_config_info(container),
            "provider": cls.get_provider_status_info(container),
            "memory": cls.get_memory_stats_info(container),
            "planner": cls.get_planner_stats_info(container),
            "conversation": cls.get_conversation_stats_info(container),
            "prompt": cls.get_prompt_diagnostics_info(container),
            "recovery": cls.get_recovery_diagnostics_info(container)
        }
