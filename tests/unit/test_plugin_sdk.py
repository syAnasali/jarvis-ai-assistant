"""Unit tests for JarvisPluginSDK."""

import pytest
from app.plugins.sdk import JarvisPluginSDK
from app.plugins.events import PluginEventBus
from app.plugins.manifest import PluginManifestParser
from app.plugins.models import PluginPermission
from app.plugins.exceptions import PluginPermissionError


def test_plugin_sdk_facades():
    data = {
        "id": "sdk_plugin",
        "name": "SDK Test Plugin",
        "version": "1.0.0",
        "entrypoint": "main.py:Plugin",
        "permissions": ["voice", "memory"]
    }
    manifest = PluginManifestParser.parse_manifest_dict(data)
    bus = PluginEventBus()

    sdk = JarvisPluginSDK(manifest=manifest, event_bus=bus)
    assert sdk.settings["plugin_id"] == "sdk_plugin"

    # Voice permission granted
    sdk.voice.speak("Hello")

    # Vision permission denied
    with pytest.raises(PluginPermissionError):
        sdk.vision.capture("Screen")
