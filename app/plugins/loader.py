"""Dynamic Plugin Loader with topological dependency resolution and fault isolation."""

import importlib.util
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Type
from app.core.logger import JarvisLogger
from app.plugins.exceptions import PluginDependencyError, PluginLoadError, PluginManifestError
from app.plugins.interfaces import Plugin
from app.plugins.manifest import PluginManifestParser
from app.plugins.models import PluginInfo, PluginManifest, PluginStatus

logger = JarvisLogger.get_logger("plugin_loader")


class DynamicPluginLoader:
    """Discovers, parses manifests, resolves dependencies, and dynamically instantiates plugins."""

    def __init__(self, plugins_dir: str = "plugins") -> None:
        self.plugins_dir = plugins_dir

    def discover_manifests(self) -> List[PluginManifest]:
        """Scans plugins directory for valid plugin.yaml / plugin.json manifests."""
        p_dir = Path(self.plugins_dir)
        manifests: List[PluginManifest] = []
        if not p_dir.exists() or not p_dir.is_dir():
            logger.warning(f"Plugins directory '{self.plugins_dir}' does not exist.")
            return manifests

        logger.info(f"Scanning plugins directory '{self.plugins_dir}'...")
        for item in p_dir.iterdir():
            if item.is_dir():
                manifest_file = self._find_manifest_file(item)
                if manifest_file:
                    try:
                        manifest = PluginManifestParser.parse_manifest_file(str(manifest_file))
                        manifests.append(manifest)
                    except Exception as e:
                        logger.error(f"Failed to parse manifest in directory '{item.name}': {e}")

        logger.info(f"Discovered {len(manifests)} valid plugin manifests.")
        return manifests

    def resolve_dependencies(self, manifests: List[PluginManifest]) -> List[PluginManifest]:
        """Sorts manifests in topological dependency order."""
        manifest_map: Dict[str, PluginManifest] = {m.id: m for m in manifests}
        in_degree: Dict[str, int] = {m.id: 0 for m in manifests}
        adj: Dict[str, List[str]] = {m.id: [] for m in manifests}

        for m in manifests:
            for dep in m.dependencies:
                if dep in manifest_map:
                    adj[dep].append(m.id)
                    in_degree[m.id] += 1
                else:
                    logger.warning(f"Plugin '{m.id}' has unresolved dependency '{dep}'.")

        queue: List[str] = [m_id for m_id, deg in in_degree.items() if deg == 0]
        sorted_manifests: List[PluginManifest] = []

        while queue:
            curr = queue.pop(0)
            sorted_manifests.append(manifest_map[curr])
            for nxt in adj[curr]:
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)

        if len(sorted_manifests) < len(manifests):
            missing_ids = set(manifest_map.keys()) - set(m.id for m in sorted_manifests)
            logger.warning(f"Circular dependency detected among plugins: {missing_ids}. Appending remaining.")
            for m_id in missing_ids:
                sorted_manifests.append(manifest_map[m_id])

        return sorted_manifests

    def load_plugin_class(self, manifest: PluginManifest) -> Type[Plugin]:
        """Dynamically imports entrypoint module and locates Plugin subclass."""
        logger.info(f"Loading plugin entrypoint for '{manifest.id}' ({manifest.entrypoint})...")
        manifest_path = Path(manifest.manifest_path)
        plugin_dir = manifest_path.parent

        entry_parts = manifest.entrypoint.split(":")
        module_file_rel = entry_parts[0]
        class_name = entry_parts[1] if len(entry_parts) > 1 else "PluginImpl"

        module_file = plugin_dir / module_file_rel
        if not module_file.exists():
            raise PluginLoadError(f"Plugin '{manifest.id}' entrypoint file not found: '{module_file}'.")

        module_name = f"jarvis_plugin_{manifest.id}"
        try:
            # Ensure plugin directory is on sys.path for internal imports
            if str(plugin_dir) not in sys.path:
                sys.path.insert(0, str(plugin_dir))

            spec = importlib.util.spec_from_file_location(module_name, str(module_file))
            if not spec or not spec.loader:
                raise PluginLoadError(f"Could not load module spec for '{module_file}'.")

            mod = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = mod
            spec.loader.exec_module(mod)

            # Find Plugin subclass in loaded module
            if hasattr(mod, class_name):
                cls = getattr(mod, class_name)
                if isinstance(cls, type) and issubclass(cls, Plugin):
                    return cls

            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if isinstance(attr, type) and issubclass(attr, Plugin) and attr is not Plugin:
                    return attr

            raise PluginLoadError(f"No Plugin subclass found in '{module_file}'.")
        except Exception as e:
            raise PluginLoadError(f"Failed to load entrypoint for plugin '{manifest.id}': {e}") from e

    def _find_manifest_file(self, plugin_dir: Path) -> Optional[Path]:
        """Locates plugin.yaml, plugin.yml, or plugin.json inside a plugin directory."""
        candidates = ["plugin.yaml", "plugin.yml", "plugin.json"]
        for c in candidates:
            f = plugin_dir / c
            if f.exists():
                return f
        return None
