"""Dependency Service Container."""

from typing import Dict, Any


class ServiceContainer:
    """Simple dictionary-based service locator container for registering singletons."""

    def __init__(self) -> None:
        """Initializes the ServiceContainer."""
        self._services: Dict[str, Any] = {}

    def register(self, name: str, service: Any) -> None:
        """Registers a singleton service in the container.

        Args:
            name: Identifier key for the service.
            service: Service instance to register.
        """
        self._services[name] = service

    def get(self, name: str) -> Any:
        """Retrieves a registered service by name.

        Args:
            name: Identifier key for the service.

        Returns:
            The service instance.

        Raises:
            KeyError: If the service is not registered.
        """
        if name not in self._services:
            raise KeyError(f"Service '{name}' is not registered in the container.")
        return self._services[name]

    def has(self, name: str) -> bool:
        """Checks if a service is registered.

        Args:
            name: Identifier key to check.

        Returns:
            True if registered, False otherwise.
        """
        return name in self._services
