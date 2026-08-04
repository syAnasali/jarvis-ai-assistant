"""Unit tests for PluginPermissionSandbox."""

import pytest
from app.plugins.sandbox import PluginPermissionSandbox
from app.plugins.manifest import PluginManifestParser
from app.plugins.models import PluginPermission
from app.plugins.exceptions import PluginPermissionError


def test_sandbox_permission_enforcement():
    data = {
        "id": "sandbox_plugin",
        "name": "Sandbox Test Plugin",
        "version": "1.0.0",
        "entrypoint": "main.py:Plugin",
        "permissions": ["voice"]
    }
    manifest = PluginManifestParser.parse_manifest_dict(data)
    sandbox = PluginPermissionSandbox(manifest, strict_mode=True)

    assert sandbox.has_permission(PluginPermission.VOICE) is True
    assert sandbox.has_permission(PluginPermission.VISION) is False

    sandbox.check_permission(PluginPermission.VOICE)

    with pytest.raises(PluginPermissionError):
        sandbox.check_permission(PluginPermission.VISION)
