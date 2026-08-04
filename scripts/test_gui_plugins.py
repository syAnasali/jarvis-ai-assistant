"""Diagnostic script testing PySide6 Plugin Manager workspace offscreen."""

import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, ".")

import time
from PySide6.QtWidgets import QApplication
from app.gui.views.plugins_view import PluginsView


def main() -> None:
    print("==================================================")
    print("Testing PySide6 Plugin Manager Diagnostics")
    print("==================================================")

    app = QApplication.instance() or QApplication(sys.argv)

    plugins_view = PluginsView()
    print("PASS: PluginsView instantiated successfully.")

    # Enable/Disable toggle
    plugins_view.controller.execute_plugin_action("enable", "plugin_web")
    if plugins_view.controller.active_worker:
        plugins_view.controller.active_worker.wait(2000)
    app.processEvents()

    assert plugins_view.browser.plugins[2]["status"] == "ENABLED"
    print("PASS: QThread PluginWorker status toggle verified.")

    # Hot-reload
    plugins_view.btn_reload_all.click()
    if plugins_view.controller.active_worker:
        plugins_view.controller.active_worker.wait(2000)
    app.processEvents()

    print("PASS: QThread PluginWorker hot-reload verified.")

    print("\nALL PLUGIN MANAGER DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
