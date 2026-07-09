"""Domain models for installed applications."""

import re
import os
import hashlib
from typing import Dict, Any
from dataclasses import dataclass, field

@dataclass(frozen=True)
class InstalledApplication:
    """Immutable domain model representing a discovered Windows application."""
    name: str
    executable_path: str
    version: str = ""
    publisher: str = ""
    source: str = ""
    application_id: str = field(init=False)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Normalize path
        norm_path = os.path.normpath(os.path.expandvars(self.executable_path.strip(' \t\n\r"\'')))
        # We must use object.__setattr__ because the dataclass is frozen
        object.__setattr__(self, "executable_path", norm_path)
        
        # Generate deterministic application_id from name and normalized path
        slug = re.sub(r'[^a-z0-9]+', '_', self.name.lower()).strip('_')
        h = hashlib.md5(norm_path.lower().encode('utf-8')).hexdigest()[:8]
        app_id = f"app_{slug}_{h}"
        object.__setattr__(self, "application_id", app_id)
        
        # Defensively copy metadata and make it read-only
        from types import MappingProxyType
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
