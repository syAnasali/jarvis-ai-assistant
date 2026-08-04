"""Weather Mock Example Plugin for Jarvis Plugin SDK."""

from typing import Any, Dict
from app.plugins.interfaces import Plugin
from app.plugins.sdk import JarvisPluginSDK
from app.tools.base import BaseTool
from app.tools.models import ToolPermission, ToolResult


class GetWeatherForecastTool(BaseTool):
    """Mock weather forecast tool."""

    name = "get_weather_forecast"
    description = "Returns current mock weather forecast for a target city."
    permission_level = ToolPermission.SAFE

    parameters = {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name", "default": "Tokyo"}
        },
        "required": ["city"]
    }

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level.value,
            "parameters": self.parameters
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        city = kwargs.get("city", "Tokyo")
        return ToolResult(
            tool_name=self.name,
            success=True,
            output={
                "city": city,
                "temperature_celsius": 22.5,
                "condition": "Sunny with light breeze",
                "humidity": "55%"
            }
        )


class WeatherMockPlugin(Plugin):
    """Plugin implementation for Weather Mock example."""

    def initialize(self, sdk: JarvisPluginSDK) -> None:
        self.sdk = sdk

    def shutdown(self) -> None:
        pass

    def register_tools(self, sdk: JarvisPluginSDK) -> None:
        sdk.tools.register(GetWeatherForecastTool())
