"""Plugin Lifecycle Coordinator handling startup and shutdown sequences."""

from datetime import datetime, timezone
from typing import Any, Optional
from app.core.logger import JarvisLogger
from app.plugins.events import PluginEventBus
from app.plugins.interfaces import Plugin
from app.plugins.models import PluginEvent, PluginInfo, PluginStatus
from app.plugins.sdk import JarvisPluginSDK

logger = JarvisLogger.get_logger("plugin_lifecycle")


class PluginLifecycleCoordinator:
    """Manages full lifecycle startup, initialization, registration, and shutdown for plugins."""

    def __init__(
        self,
        event_bus: PluginEventBus,
        tool_registry: Optional[Any] = None,
        memory_manager: Optional[Any] = None,
        voice_pipeline: Optional[Any] = None,
        vision_pipeline: Optional[Any] = None,
        knowledge_manager: Optional[Any] = None,
        planner_manager: Optional[Any] = None
    ) -> None:
        self.event_bus = event_bus
        self.tool_registry = tool_registry
        self.memory_manager = memory_manager
        self.voice_pipeline = voice_pipeline
        self.vision_pipeline = vision_pipeline
        self.knowledge_manager = knowledge_manager
        self.planner_manager = planner_manager

    def initialize_plugin(self, info: PluginInfo, plugin_instance: Plugin) -> JarvisPluginSDK:
        """Initializes a plugin instance, runs registration hooks, and marks status ACTIVE."""
        logger.info(f"Initializing plugin '{info.manifest.id}'...")
        sdk = JarvisPluginSDK(
            manifest=info.manifest,
            event_bus=self.event_bus,
            tool_registry=self.tool_registry,
            memory_manager=self.memory_manager,
            voice_pipeline=self.voice_pipeline,
            vision_pipeline=self.vision_pipeline,
            knowledge_manager=self.knowledge_manager,
            planner_manager=self.planner_manager
        )

        try:
            # 1. Core plugin initialization
            plugin_instance.initialize(sdk)

            # 2. Capability Registration Hooks
            plugin_instance.register_tools(sdk)
            plugin_instance.register_voice_commands(sdk)
            plugin_instance.register_memory_hooks(sdk)
            plugin_instance.register_planner_hooks(sdk)
            plugin_instance.register_events(sdk)

            info.plugin_instance = plugin_instance
            info.status = PluginStatus.ACTIVE
            info.loaded_at = datetime.now(timezone.utc)
            info.error_message = None

            logger.info(f"Plugin '{info.manifest.id}' initialized and activated successfully.")
            return sdk
        except Exception as e:
            logger.error(f"Error during plugin '{info.manifest.id}' lifecycle initialization: {e}")
            info.status = PluginStatus.FAILED
            info.error_message = str(e)
            raise

    def shutdown_plugin(self, info: PluginInfo) -> None:
        """Shuts down a plugin instance and releases resources."""
        if not info.plugin_instance:
            return

        logger.info(f"Shutting down plugin '{info.manifest.id}'...")
        try:
            info.plugin_instance.shutdown()
        except Exception as e:
            logger.error(f"Error during plugin '{info.manifest.id}' shutdown: {e}")
        finally:
            info.plugin_instance = None
            info.status = PluginStatus.DISABLED
            logger.info(f"Plugin '{info.manifest.id}' shutdown complete.")
