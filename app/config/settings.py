"""Configuration settings loader using Pydantic Settings."""

from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.core.constants import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_LOG_LEVEL,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_HOST,
    DATABASE_PATH,
)

LogLevel = Literal["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    """Application settings class loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = APP_NAME
    app_version: str = APP_VERSION
    ollama_host: str = DEFAULT_HOST
    ollama_model: str = DEFAULT_OLLAMA_MODEL
    database_path: Path = DATABASE_PATH
    log_level: LogLevel = DEFAULT_LOG_LEVEL
    voice_name: str = "en-US-Neural"
    hotkey: str = "ctrl+alt+j"


# Singleton instance
settings = Settings()
