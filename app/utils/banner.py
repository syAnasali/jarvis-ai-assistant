"""Application startup and shutdown banner rendering."""

from app.config.settings import settings


def render_startup_banner() -> None:
    """Prints a professional startup banner to the console interface."""
    print("==================================================")
    print(f"Application: {settings.app_name}")
    print(f"Version:     {settings.app_version}")
    print(f"Provider:    ollama")
    print(f"Model:       {settings.ollama_model}")
    print("Status:      Ready")
    print("==================================================")
    print("Type 'exit', 'quit', or 'bye' to end the session.")
    print()


def render_shutdown_banner() -> None:
    """Prints a shutdown confirmation message to the console interface."""
    print("Exiting chat session.")
