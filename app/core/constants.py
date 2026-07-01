"""Application-wide constants for Jarvis AI Assistant."""

from pathlib import Path

APP_NAME: str = "Jarvis AI Assistant"
APP_VERSION: str = "0.1.0"
DEFAULT_LOG_LEVEL: str = "INFO"
DEFAULT_OLLAMA_MODEL: str = "qwen3"
DEFAULT_HOST: str = "http://localhost:11434"

# Centralized path settings
DATA_DIR: Path = Path("data")
LOG_DIR: Path = Path("logs")
CONFIG_DIR: Path = Path("config")
DATABASE_NAME: str = "jarvis.db"
DATABASE_PATH: Path = DATA_DIR / DATABASE_NAME
