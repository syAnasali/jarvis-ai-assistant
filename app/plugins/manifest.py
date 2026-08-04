"""Plugin Manifest Parser and Validator for plugin.yaml and plugin.json files."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.core.logger import JarvisLogger
from app.plugins.exceptions import PluginManifestError
from app.plugins.models import PluginManifest, PluginPermission

logger = JarvisLogger.get_logger("plugin_manifest")


class PluginManifestParser:
    """Parses and validates plugin manifest metadata files."""

    @classmethod
    def parse_manifest_file(cls, manifest_path: str) -> PluginManifest:
        """Parses a plugin.yaml or plugin.json file into a validated PluginManifest model."""
        p = Path(manifest_path)
        if not p.exists():
            raise PluginManifestError(f"Plugin manifest file not found: '{manifest_path}'.")

        logger.info(f"Parsing plugin manifest '{manifest_path}'...")
        try:
            content = p.read_text(encoding="utf-8")
            if p.suffix.lower() in (".yaml", ".yml"):
                data = cls._parse_yaml(content)
            else:
                data = json.loads(content)
        except Exception as e:
            raise PluginManifestError(f"Failed to parse manifest file '{manifest_path}': {e}") from e

        return cls.parse_manifest_dict(data, str(p.resolve()))

    @classmethod
    def parse_manifest_dict(cls, data: Dict[str, Any], manifest_path: str = "") -> PluginManifest:
        """Validates dictionary representation of a plugin manifest."""
        if not isinstance(data, dict):
            raise PluginManifestError("Plugin manifest root must be a key-value dictionary.")

        # Required fields check
        required_keys = ["id", "name", "version", "entrypoint"]
        for rk in required_keys:
            if rk not in data or not str(data[rk]).strip():
                raise PluginManifestError(f"Plugin manifest missing required field '{rk}'.")

        plugin_id = str(data["id"]).strip()
        name = str(data["name"]).strip()
        version = str(data["version"]).strip()
        entrypoint = str(data["entrypoint"]).strip()

        # Parse permissions
        raw_perms = data.get("permissions", [])
        parsed_perms: List[PluginPermission] = []
        if isinstance(raw_perms, list):
            for perm_str in raw_perms:
                try:
                    parsed_perms.append(PluginPermission(str(perm_str).lower()))
                except ValueError:
                    logger.warning(f"Plugin '{plugin_id}' declared unknown permission '{perm_str}'. Ignoring.")

        # Parse lists
        dependencies = [str(x) for x in data.get("dependencies", [])] if isinstance(data.get("dependencies"), list) else []
        tools = [str(x) for x in data.get("tools", [])] if isinstance(data.get("tools"), list) else []
        voice_commands = [str(x) for x in data.get("voice_commands", [])] if isinstance(data.get("voice_commands"), list) else []

        manifest = PluginManifest(
            id=plugin_id,
            name=name,
            version=version,
            entrypoint=entrypoint,
            author=str(data.get("author", "Unknown")),
            description=str(data.get("description", "")),
            minimum_jarvis_version=str(data.get("minimum_jarvis_version", "1.0.0")),
            permissions=parsed_perms,
            dependencies=dependencies,
            tools=tools,
            voice_commands=voice_commands,
            manifest_path=manifest_path,
            raw_metadata=data
        )

        logger.info(f"Manifest for plugin '{plugin_id}' (v{version}) validated successfully.")
        return manifest

    @classmethod
    def _parse_yaml(cls, text: str) -> Dict[str, Any]:
        """Simple YAML parser fallback for key-value pair manifests."""
        try:
            import yaml
            return yaml.safe_load(text) or {}
        except ImportError:
            # Fallback simple key-value parser for basic yaml files
            result: Dict[str, Any] = {}
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    k, v = line.split(":", 1)
                    k = k.strip()
                    v = v.strip().strip("\"'")
                    if v.startswith("[") and v.endswith("]"):
                        items = [x.strip().strip("\"'") for x in v[1:-1].split(",") if x.strip()]
                        result[k] = items
                    else:
                        result[k] = v
            return result
