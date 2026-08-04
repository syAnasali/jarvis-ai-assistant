"""Immutable domain models and dataclasses for the Plugin Architecture."""

import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Dict, List, Optional, Set


class PluginStatus(Enum):
    """Lifecycle status of a plugin."""
    DISCOVERED = "DISCOVERED"
    VALIDATED = "VALIDATED"
    LOADED = "LOADED"
    INITIALIZED = "INITIALIZED"
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    FAILED = "FAILED"


class PluginPermission(Enum):
    """Permissions requested by plugins."""
    FILESYSTEM = "filesystem"
    DESKTOP = "desktop"
    VOICE = "voice"
    VISION = "vision"
    KNOWLEDGE = "knowledge"
    PLANNER = "planner"
    NETWORK = "network"
    MEMORY = "memory"
    CONFIRMATION = "confirmation"


@dataclass(frozen=True)
class PluginManifest:
    """Represents a validated plugin manifest file (plugin.yaml / plugin.json)."""
    id: str
    name: str
    version: str
    entrypoint: str
    author: str = "Unknown"
    description: str = ""
    minimum_jarvis_version: str = "1.0.0"
    permissions: List[PluginPermission] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    voice_commands: List[str] = field(default_factory=list)
    manifest_path: str = ""
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("PluginManifest id cannot be empty.")
        if not self.name.strip():
            raise ValueError("PluginManifest name cannot be empty.")
        if not self.entrypoint.strip():
            raise ValueError("PluginManifest entrypoint cannot be empty.")

        copied_perms = tuple(self.permissions)
        copied_deps = tuple(self.dependencies)
        copied_tools = tuple(self.tools)
        copied_voice = tuple(self.voice_commands)
        copied_raw = MappingProxyType(copy.deepcopy(self.raw_metadata))

        object.__setattr__(self, "permissions", copied_perms)
        object.__setattr__(self, "dependencies", copied_deps)
        object.__setattr__(self, "tools", copied_tools)
        object.__setattr__(self, "voice_commands", copied_voice)
        object.__setattr__(self, "raw_metadata", copied_raw)


@dataclass(frozen=True)
class PluginEvent:
    """Represents a publish/subscribe event payload."""
    event_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    source_plugin_id: str = "system"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.event_type.strip():
            raise ValueError("PluginEvent event_type cannot be empty.")
        if self.timestamp.tzinfo is None:
            raise ValueError("PluginEvent timestamp must be timezone-aware.")
        copied_payload = MappingProxyType(copy.deepcopy(self.payload))
        object.__setattr__(self, "payload", copied_payload)


@dataclass
class PluginInfo:
    """Maintains metadata, state, and active instance reference for a plugin."""
    manifest: PluginManifest
    status: PluginStatus = PluginStatus.DISCOVERED
    plugin_instance: Optional[Any] = None
    loaded_at: Optional[datetime] = None
    error_message: Optional[str] = None
    health_status: Dict[str, Any] = field(default_factory=dict)
