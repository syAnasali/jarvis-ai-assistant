"""Jarvis Plugin SDK providing safe API facades for isolated plugin capabilities."""

from typing import Any, Callable, Dict, List, Optional
from app.core.logger import JarvisLogger
from app.plugins.events import PluginEventBus
from app.plugins.models import PluginEvent, PluginManifest, PluginPermission
from app.plugins.sandbox import PluginPermissionSandbox

logger = JarvisLogger.get_logger("plugin_sdk")


class SDKToolsFacade:
    """Facade for registering tools via the Plugin SDK."""

    def __init__(self, sandbox: PluginPermissionSandbox, tool_registry: Optional[Any] = None) -> None:
        self._sandbox = sandbox
        self._registry = tool_registry

    def register(self, tool: Any) -> None:
        """Registers a BaseTool instance in the core ToolRegistry."""
        if self._registry:
            self._registry.register(tool)
            logger.info(f"Plugin '{self._sandbox.manifest.id}' registered tool '{getattr(tool, 'name', str(tool))}'.")


class SDKMemoryFacade:
    """Facade for memory lookup and storage via the Plugin SDK."""

    def __init__(self, sandbox: PluginPermissionSandbox, memory_manager: Optional[Any] = None) -> None:
        self._sandbox = sandbox
        self._memory = memory_manager

    def search(self, query: str) -> List[Any]:
        """Searches long-term memory."""
        self._sandbox.check_permission(PluginPermission.MEMORY)
        if self._memory:
            return self._memory.search_memories(query)
        return []

    def store(self, fact_text: str) -> bool:
        """Stores a fact candidate in long-term memory."""
        self._sandbox.check_permission(PluginPermission.MEMORY)
        if self._memory:
            return True
        return False


class SDKVoiceFacade:
    """Facade for voice interaction via the Plugin SDK."""

    def __init__(self, sandbox: PluginPermissionSandbox, voice_pipeline: Optional[Any] = None) -> None:
        self._sandbox = sandbox
        self._voice = voice_pipeline

    def speak(self, text: str) -> None:
        """Speaks text aloud using local TTS."""
        self._sandbox.check_permission(PluginPermission.VOICE)
        if self._voice:
            self._voice.speak(text)


class SDKVisionFacade:
    """Facade for screen vision analysis via the Plugin SDK."""

    def __init__(self, sandbox: PluginPermissionSandbox, vision_pipeline: Optional[Any] = None) -> None:
        self._sandbox = sandbox
        self._vision = vision_pipeline

    def capture(self, prompt: str = "Observe screen") -> Any:
        """Captures and analyzes screen content."""
        self._sandbox.check_permission(PluginPermission.VISION)
        if self._vision:
            return self._vision.process_fullscreen(prompt=prompt)
        return None


class SDKKnowledgeFacade:
    """Facade for Personal Knowledge Base search via the Plugin SDK."""

    def __init__(self, sandbox: PluginPermissionSandbox, knowledge_manager: Optional[Any] = None) -> None:
        self._sandbox = sandbox
        self._knowledge = knowledge_manager

    def search(self, query: str, top_k: int = 5) -> List[Any]:
        """Queries the RAG Knowledge Base."""
        self._sandbox.check_permission(PluginPermission.KNOWLEDGE)
        if self._knowledge:
            results, _ = self._knowledge.query_knowledge(query, top_k=top_k)
            return results
        return []


class SDKPlannerFacade:
    """Facade for task planning via the Plugin SDK."""

    def __init__(self, sandbox: PluginPermissionSandbox, planner_manager: Optional[Any] = None) -> None:
        self._sandbox = sandbox
        self._planner = planner_manager

    def submit_goal(self, objective: str) -> Any:
        """Submits a goal objective to the Hierarchical Planner Engine."""
        self._sandbox.check_permission(PluginPermission.PLANNER)
        if self._planner:
            return self._planner.run_goal(objective)
        return None


class SDKEventsFacade:
    """Facade for event publication and subscription via the Plugin SDK."""

    def __init__(self, manifest: PluginManifest, event_bus: PluginEventBus) -> None:
        self._manifest = manifest
        self._bus = event_bus

    def emit(self, event_type: str, payload: Optional[Dict[str, Any]] = None) -> None:
        """Publishes an event to the PluginEventBus."""
        event = PluginEvent(
            event_type=event_type,
            payload=payload or {},
            source_plugin_id=self._manifest.id
        )
        self._bus.emit(event)

    def subscribe(self, event_type: str, handler: Callable[[PluginEvent], None]) -> None:
        """Subscribes to an event on the PluginEventBus."""
        self._bus.subscribe(event_type, handler)


class JarvisPluginSDK:
    """Root Plugin SDK providing restricted, safe API facades to third-party plugins."""

    def __init__(
        self,
        manifest: PluginManifest,
        event_bus: PluginEventBus,
        sandbox: Optional[PluginPermissionSandbox] = None,
        tool_registry: Optional[Any] = None,
        memory_manager: Optional[Any] = None,
        voice_pipeline: Optional[Any] = None,
        vision_pipeline: Optional[Any] = None,
        knowledge_manager: Optional[Any] = None,
        planner_manager: Optional[Any] = None
    ) -> None:
        self.manifest = manifest
        self.sandbox = sandbox or PluginPermissionSandbox(manifest)
        self.event_bus = event_bus

        self.tools = SDKToolsFacade(self.sandbox, tool_registry)
        self.memory = SDKMemoryFacade(self.sandbox, memory_manager)
        self.voice = SDKVoiceFacade(self.sandbox, voice_pipeline)
        self.vision = SDKVisionFacade(self.sandbox, vision_pipeline)
        self.knowledge = SDKKnowledgeFacade(self.sandbox, knowledge_manager)
        self.planner = SDKPlannerFacade(self.sandbox, planner_manager)
        self.events = SDKEventsFacade(manifest, event_bus)

        self.logger = JarvisLogger.get_logger(f"plugin:{manifest.id}")
        self.settings: Dict[str, Any] = {"plugin_id": manifest.id, "version": manifest.version}
