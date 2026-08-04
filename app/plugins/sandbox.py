"""Plugin Permission Sandbox enforcing permission boundaries for SDK capability calls."""

from typing import List, Set
from app.core.logger import JarvisLogger
from app.plugins.exceptions import PluginPermissionError
from app.plugins.models import PluginManifest, PluginPermission

logger = JarvisLogger.get_logger("plugin_sandbox")


class PluginPermissionSandbox:
    """Validates and enforces permission boundaries for plugin SDK invocations."""

    def __init__(self, manifest: PluginManifest, strict_mode: bool = True) -> None:
        self.manifest = manifest
        self.strict_mode = strict_mode
        self.granted_permissions: Set[PluginPermission] = set(manifest.permissions)

    def check_permission(self, permission: PluginPermission) -> None:
        """Verifies if the plugin has declared the target permission."""
        if permission not in self.granted_permissions:
            msg = (
                f"Plugin '{self.manifest.id}' attempted action requiring permission "
                f"'{permission.value}', but it was not declared in its manifest."
            )
            logger.error(msg)
            if self.strict_mode:
                raise PluginPermissionError(msg)

    def has_permission(self, permission: PluginPermission) -> bool:
        """Returns True if the plugin holds the target permission."""
        return permission in self.granted_permissions
