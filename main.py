"""Main entry point for Jarvis AI Assistant."""

import sys
from app.core.application import Application
from app.core.exceptions import JarvisError


def main() -> None:
    """Initializes and runs the Jarvis AI Assistant."""
    app = Application()
    try:
        app.initialize()
        app.run()
    except JarvisError as e:
        print(f"Jarvis encountered a fatal error and must exit: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected critical error occurred: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        app.shutdown()


if __name__ == "__main__":
    main()
