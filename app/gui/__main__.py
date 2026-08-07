"""Main entry point when executing python -m app.gui."""

import sys
from app.gui.app import JarvisGuiApplication


def main() -> None:
    gui_app = JarvisGuiApplication()
    sys.exit(gui_app.run())


if __name__ == "__main__":
    main()
