"""Exception hierarchy for the Provider-Neutral Plugin SDK & Extension Framework."""

from app.core.exceptions import JarvisError


class PluginError(JarvisError):
    """Base exception class for all plugin subsystem errors."""
    pass


class PluginManifestError(PluginError):
    """Raised when a plugin manifest (plugin.yaml / plugin.json) is missing or malformed."""
    pass


class PluginPermissionError(PluginError):
    """Raised when a plugin attempts an SDK action without required declared permissions."""
    pass


class PluginLoadError(PluginError):
    """Raised when a plugin fails during dynamic module loading or entrypoint instantiation."""
    pass


class PluginDependencyError(PluginError):
    """Raised when a plugin dependency is missing, incompatible, or circular."""
    pass


class PluginLifecycleError(PluginError):
    """Raised during plugin initialization, execution, or shutdown failure."""
    pass
