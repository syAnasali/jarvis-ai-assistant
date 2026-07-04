"""Base tool contract interface and validations."""

from abc import ABC, abstractmethod
from typing import Any, Dict
from app.tools.models import ToolPermission
from app.core.exceptions import ToolExecutionError


class BaseTool(ABC):
    """Abstract base class representing an executable system tool."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name identifier of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A description of what the tool accomplishes and its inputs."""
        pass

    @property
    @abstractmethod
    def permission_level(self) -> ToolPermission:
        """The safety classification permission level of the tool."""
        pass

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Returns the provider-neutral JSON-Schema representation of the tool."""
        pass

    @abstractmethod
    def execute(self, **kwargs: Any) -> Any:
        """Executes the tool's core logic with validated arguments."""
        pass

    def validate_arguments(self, arguments: Dict[str, Any]) -> None:
        """Validates input arguments against the tool parameters schema.

        Args:
            arguments: Arguments dictionary to validate.

        Raises:
            ToolExecutionError: If validation fails.
        """
        if not isinstance(arguments, dict):
            raise ToolExecutionError("Arguments must be provided as a dictionary.")

        schema = self.get_schema()
        parameters = schema.get("parameters", {})
        required = parameters.get("required", [])
        properties = parameters.get("properties", {})

        # Check for missing required arguments
        for req_arg in required:
            if req_arg not in arguments:
                raise ToolExecutionError(f"Missing required argument: '{req_arg}'.")

        # Check argument types
        for arg_name, arg_val in arguments.items():
            if arg_name not in properties:
                raise ToolExecutionError(f"Unexpected argument: '{arg_name}'.")

            param_def = properties[arg_name]
            expected_type_name = param_def.get("type")
            
            if expected_type_name == "string" and not isinstance(arg_val, str):
                raise ToolExecutionError(f"Argument '{arg_name}' must be of type string.")
            elif expected_type_name == "integer" and not isinstance(arg_val, int):
                raise ToolExecutionError(f"Argument '{arg_name}' must be of type integer.")
            elif expected_type_name == "number" and not isinstance(arg_val, (int, float)):
                raise ToolExecutionError(f"Argument '{arg_name}' must be of type number.")
            elif expected_type_name == "boolean" and not isinstance(arg_val, bool):
                raise ToolExecutionError(f"Argument '{arg_name}' must be of type boolean.")
            elif expected_type_name == "array" and not isinstance(arg_val, list):
                raise ToolExecutionError(f"Argument '{arg_name}' must be of type array.")
            elif expected_type_name == "object" and not isinstance(arg_val, dict):
                raise ToolExecutionError(f"Argument '{arg_name}' must be of type object.")
