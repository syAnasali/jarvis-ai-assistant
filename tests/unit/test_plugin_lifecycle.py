"""Unit tests for PluginLifecycleCoordinator."""

import pytest
from app.plugins.lifecycle import PluginLifecycleCoordinator
from app.plugins.events import PluginEventBus
from app.plugins.manifest import PluginManifestParser
from app.plugins.models import PluginInfo, PluginStatus
from app.plugins.interfaces import Plugin
from app.plugins.sdk import JarvisPluginSDK


class DummyPlugin(Plugin):
    def initialize(self, sdk: JarvisPluginSDK) -> None:
        self.initialized = True

    def shutdown(self) -> None:
        self.initialized = False


def test_plugin_lifecycle_coordinator():
    bus = PluginEventBus()
    coord = PluginLifecycleCoordinator(event_bus=bus)

    data = {"id": "dummy", "name": "Dummy", "version": "1.0", "entrypoint": "m.py:P"}
    manifest = PluginManifestParser.parse_manifest_dict(data)
    info = PluginInfo(manifest=manifest)

    p_instance = DummyPlugin()
    coord.initialize_plugin(info, p_instance)

    assert info.status == PluginStatus.ACTIVE
    assert p_instance.initialized is True

    coord.shutdown_plugin(info)
    assert info.status == PluginStatus.DISABLED
    assert info.plugin_instance is None
