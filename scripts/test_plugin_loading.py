"""Diagnostic script testing plugin discovery, manifest validation, and loading."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, ".")

from app.plugins.manager import PluginManager


def main() -> None:
    print("==================================================")
    print("Testing Plugin Loading Diagnostics")
    print("==================================================")

    mgr = PluginManager(plugins_dir="plugins/examples")
    mgr.initialize()

    plugins = mgr.list_plugins()
    print(f"Loaded Plugins Count: {len(plugins)}")
    for p in plugins:
        print(f" - Plugin: id={p.manifest.id}, name='{p.manifest.name}', status={p.status.value}")

    assert len(plugins) >= 1
    print("PASS: Plugin discovery and loading verified.")

    mgr.shutdown()
    print("PASS: PluginManager shutdown complete.")
    print("\nALL PLUGIN LOADING DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
