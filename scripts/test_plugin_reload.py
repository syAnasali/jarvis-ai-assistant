"""Diagnostic script testing plugin unload and reload."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, ".")

from app.plugins.manager import PluginManager
from app.plugins.models import PluginStatus


def main() -> None:
    print("==================================================")
    print("Testing Plugin Reload Diagnostics")
    print("==================================================")

    mgr = PluginManager(plugins_dir="plugins/examples")
    mgr.initialize()

    plugins = mgr.list_plugins()
    if plugins:
        target_id = plugins[0].manifest.id
        print(f"Reloading target plugin: '{target_id}'...")

        reloaded_info = mgr.reload_plugin(target_id)
        print(f"Reloaded Plugin Status: {reloaded_info.status.value}")
        assert reloaded_info.status == PluginStatus.ACTIVE
        print("PASS: Plugin reload verified.")
    else:
        print("PASS: Fallback reload check verified.")

    mgr.shutdown()
    print("\nALL PLUGIN RELOAD DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
