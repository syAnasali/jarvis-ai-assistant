"""Unit tests for PluginManifestParser."""

import pytest
from app.plugins.manifest import PluginManifestParser
from app.plugins.exceptions import PluginManifestError
from app.plugins.models import PluginPermission


def test_manifest_dict_validation():
    data = {
        "id": "my_plugin",
        "name": "My Test Plugin",
        "version": "1.2.0",
        "entrypoint": "main.py:Plugin",
        "permissions": ["voice", "memory"],
        "dependencies": ["other_plugin"]
    }
    manifest = PluginManifestParser.parse_manifest_dict(data)
    assert manifest.id == "my_plugin"
    assert manifest.version == "1.2.0"
    assert PluginPermission.VOICE in manifest.permissions
    assert "other_plugin" in manifest.dependencies


def test_manifest_dict_missing_required_field():
    data = {"name": "Incomplete Plugin", "version": "1.0.0"}
    with pytest.raises(PluginManifestError):
        PluginManifestParser.parse_manifest_dict(data)
