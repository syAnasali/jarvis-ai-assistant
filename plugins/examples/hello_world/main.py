"""Hello World Example Plugin for Jarvis Plugin SDK."""

from typing import Any, Dict
from app.plugins.interfaces import Plugin
from app.plugins.models import PluginEvent
from app.plugins.sdk import JarvisPluginSDK
from app.tools.base import BaseTool
from app.tools.models import ToolPermission, ToolResult


class HelloWorldTool(BaseTool):
    """Example tool provided by Hello World plugin."""

    name = "hello_world_tool"
    description = "Returns a friendly greeting message."
    permission_level = ToolPermission.SAFE

    parameters = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "User name", "default": "User"}
        },
        "required": []
    }

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level.value,
            "parameters": self.parameters
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        user_name = kwargs.get("name", "User")
        return ToolResult(tool_name=self.name, success=True, output={"greeting": f"Hello, {user_name}! Welcome to Jarvis Plugin SDK."})


class HelloWorldPlugin(Plugin):
    """Plugin implementation for Hello World example."""

    def initialize(self, sdk: JarvisPluginSDK) -> None:
        self.sdk = sdk
        sdk.logger.info("HelloWorldPlugin initialized successfully.")

    def shutdown(self) -> None:
        if hasattr(self, "sdk"):
            self.sdk.logger.info("HelloWorldPlugin shutdown complete.")

    def register_tools(self, sdk: JarvisPluginSDK) -> None:
        sdk.tools.register(HelloWorldTool())

    def register_events(self, sdk: JarvisPluginSDK) -> None:
        sdk.events.subscribe("assistant_started", self.on_assistant_started)

    def on_assistant_started(self, event: PluginEvent) -> None:
        self.sdk.logger.info(f"HelloWorldPlugin received event: {event.event_type}")
