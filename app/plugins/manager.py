"""Plugin Manager coordinating discovery, loading, unloading, hot-reloading, and health reporting."""

from typing import Any, Dict, List, Optional
from app.core.logger import JarvisLogger
from app.plugins.events import PluginEventBus
from app.plugins.lifecycle import PluginLifecycleCoordinator
from app.plugins.loader import DynamicPluginLoader
from app.plugins.models import PluginEvent, PluginInfo, PluginStatus
from app.plugins.registry import PluginRegistry

logger = JarvisLogger.get_logger("plugin_manager")


class PluginManager:
    """Central manager for plugin discovery, loading, hot-reloading, enabling/disabling, and health reporting."""

    def __init__(
        self,
        plugins_dir: str = "plugins",
        loader: Optional[DynamicPluginLoader] = None,
        registry: Optional[PluginRegistry] = None,
        event_bus: Optional[PluginEventBus] = None,
        coordinator: Optional[PluginLifecycleCoordinator] = None,
        tool_registry: Optional[Any] = None,
        memory_manager: Optional[Any] = None,
        voice_pipeline: Optional[Any] = None,
        vision_pipeline: Optional[Any] = None,
        knowledge_manager: Optional[Any] = None,
        planner_manager: Optional[Any] = None
    ) -> None:
        self.plugins_dir = plugins_dir
        self.loader = loader or DynamicPluginLoader(plugins_dir=plugins_dir)
        self.registry = registry or PluginRegistry()
        self.event_bus = event_bus or PluginEventBus()
        self.coordinator = coordinator or PluginLifecycleCoordinator(
            event_bus=self.event_bus,
            tool_registry=tool_registry,
            memory_manager=memory_manager,
            voice_pipeline=voice_pipeline,
            vision_pipeline=vision_pipeline,
            knowledge_manager=knowledge_manager,
            planner_manager=planner_manager
        )

        self._is_initialized = False

    def initialize(self) -> None:
        """Initializes PluginManager and loads all discovered plugins."""
        if self._is_initialized:
            return
        logger.info("Initializing PluginManager...")
        self.discover_and_load_all()
        self.event_bus.emit(PluginEvent(event_type="assistant_started", source_plugin_id="system"))
        self._is_initialized = True
        logger.info("PluginManager initialized successfully.")

    def discover_and_load_all(self) -> List[PluginInfo]:
        """Discovers, sorts, and loads all available plugins with fault isolation."""
        manifests = self.loader.discover_manifests()
        sorted_manifests = self.loader.resolve_dependencies(manifests)
        loaded_plugins: List[PluginInfo] = []

        for manifest in sorted_manifests:
            info = PluginInfo(manifest=manifest, status=PluginStatus.VALIDATED)
            self.registry.register_plugin(info)
            try:
                plugin_cls = self.loader.load_plugin_class(manifest)
                instance = plugin_cls()
                self.coordinator.initialize_plugin(info, instance)
                loaded_plugins.append(info)
            except Exception as e:
                logger.error(f"Fault Isolation: Failed to load plugin '{manifest.id}': {e}")
                self.registry.update_status(manifest.id, PluginStatus.FAILED, error_message=str(e))

        return loaded_plugins

    def load_plugin(self, manifest_path: str) -> PluginInfo:
        """Loads an individual plugin by manifest file path."""
        from app.plugins.manifest import PluginManifestParser
        manifest = PluginManifestParser.parse_manifest_file(manifest_path)
        info = PluginInfo(manifest=manifest, status=PluginStatus.VALIDATED)
        self.registry.register_plugin(info)

        plugin_cls = self.loader.load_plugin_class(manifest)
        instance = plugin_cls()
        self.coordinator.initialize_plugin(info, instance)
        return info

    def unload_plugin(self, plugin_id: str) -> None:
        """Unloads and shuts down a plugin by ID."""
        info = self.registry.get_plugin(plugin_id)
        if info:
            self.coordinator.shutdown_plugin(info)

    def reload_plugin(self, plugin_id: str) -> PluginInfo:
        """Hot-reloads an active or failed plugin without restarting Jarvis."""
        logger.info(f"Hot-reloading plugin '{plugin_id}'...")
        info = self.registry.get_plugin(plugin_id)
        if not info:
            raise KeyError(f"Cannot reload unknown plugin '{plugin_id}'.")

        manifest_path = info.manifest.manifest_path
        self.unload_plugin(plugin_id)
        return self.load_plugin(manifest_path)

    def list_plugins(self) -> List[PluginInfo]:
        """Lists all registered plugins."""
        return self.registry.list_plugins()

    def enable_plugin(self, plugin_id: str) -> None:
        """Enables a disabled plugin."""
        info = self.registry.get_plugin(plugin_id)
        if info and info.status == PluginStatus.DISABLED:
            self.reload_plugin(plugin_id)

    def disable_plugin(self, plugin_id: str) -> None:
        """Disables an active plugin."""
        self.unload_plugin(plugin_id)

    def health_report(self) -> Dict[str, Any]:
        """Generates a health report across all registered plugins."""
        plugins = self.list_plugins()
        report: Dict[str, Any] = {
            "total_plugins": len(plugins),
            "active_plugins": sum(1 for p in plugins if p.status == PluginStatus.ACTIVE),
            "failed_plugins": sum(1 for p in plugins if p.status == PluginStatus.FAILED),
            "disabled_plugins": sum(1 for p in plugins if p.status == PluginStatus.DISABLED),
            "plugin_statuses": {}
        }

        for p in plugins:
            h_stat = p.plugin_instance.health_check() if p.plugin_instance else {"status": "inactive"}
            report["plugin_statuses"][p.manifest.id] = {
                "name": p.manifest.name,
                "version": p.manifest.version,
                "status": p.status.value,
                "health": h_stat,
                "error": p.error_message
            }

        return report

    def shutdown(self) -> None:
        """Shuts down all active plugins upon system exit."""
        logger.info("Shutting down PluginManager...")
        self.event_bus.emit(PluginEvent(event_type="assistant_shutdown", source_plugin_id="system"))
        for info in self.list_plugins():
            if info.status == PluginStatus.ACTIVE:
                self.coordinator.shutdown_plugin(info)
        self._is_initialized = False
        logger.info("PluginManager shutdown complete.")
