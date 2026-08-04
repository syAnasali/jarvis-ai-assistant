"""Unit tests for DynamicPluginLoader."""

import pytest
from app.plugins.loader import DynamicPluginLoader
from app.plugins.manifest import PluginManifestParser


def test_plugin_loader_dependency_sorting():
    loader = DynamicPluginLoader()

    m1_dict = {"id": "plugin_b", "name": "B", "version": "1.0", "entrypoint": "m.py:P", "dependencies": ["plugin_a"]}
    m2_dict = {"id": "plugin_a", "name": "A", "version": "1.0", "entrypoint": "m.py:P"}

    m1 = PluginManifestParser.parse_manifest_dict(m1_dict)
    m2 = PluginManifestParser.parse_manifest_dict(m2_dict)

    sorted_manifests = loader.resolve_dependencies([m1, m2])
    assert [m.id for m in sorted_manifests] == ["plugin_a", "plugin_b"]
