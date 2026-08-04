"""Diagnostic script testing PluginPermissionSandbox permission checks."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, ".")

from app.plugins.exceptions import PluginPermissionError
from app.plugins.manifest import PluginManifestParser
from app.plugins.models import PluginPermission
from app.plugins.sandbox import PluginPermissionSandbox


def main() -> None:
    print("==================================================")
    print("Testing Plugin Permission Sandbox Diagnostics")
    print("==================================================")

    manifest_dict = {
        "id": "perm_test_plugin",
        "name": "Permission Test Plugin",
        "version": "1.0.0",
        "entrypoint": "main.py:Plugin",
        "permissions": ["voice", "memory"]
    }
    manifest = PluginManifestParser.parse_manifest_dict(manifest_dict)
    sandbox = PluginPermissionSandbox(manifest, strict_mode=True)

    # Granted permission check
    sandbox.check_permission(PluginPermission.VOICE)
    print("PASS: Granted permission check passed.")

    # Denied permission check
    try:
        sandbox.check_permission(PluginPermission.VISION)
        print("FAIL: Vision permission was not denied.")
        assert False
    except PluginPermissionError:
        print("PASS: Undeclared vision permission correctly blocked.")

    print("\nALL PERMISSION SANDBOX DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
