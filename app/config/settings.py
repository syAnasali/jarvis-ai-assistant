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
    conversation_context_max_messages: int = 24
    conversation_context_max_characters: int = 24000
    planning_enabled: bool = True
    planning_max_steps: int = 8
    planning_max_observation_characters: int = 16000

    tool_default_list_limit: int = 100
    tool_max_list_limit: int = 500
    tool_max_text_file_bytes: int = 2097152
    tool_default_text_characters: int = 12000
    tool_max_text_characters: int = 50000
    approval_timeout_seconds: int = 120

    @classmethod
    def validate_relationships(cls, values: dict) -> None:
        """Validates tool settings ranges and relationships."""
        if values.get("tool_default_list_limit", 100) <= 0:
            raise ValueError("tool_default_list_limit must be positive")
        if values.get("tool_max_list_limit", 500) < values.get("tool_default_list_limit", 100):
            raise ValueError("tool_max_list_limit must be >= tool_default_list_limit")
        if values.get("tool_max_text_file_bytes", 2097152) <= 0:
            raise ValueError("tool_max_text_file_bytes must be positive")
        if values.get("tool_default_text_characters", 12000) <= 0:
            raise ValueError("tool_default_text_characters must be positive")
        if values.get("tool_max_text_characters", 50000) < values.get("tool_default_text_characters", 12000):
            raise ValueError("tool_max_text_characters must be >= tool_default_text_characters")
        if values.get("approval_timeout_seconds", 120) <= 0:
            raise ValueError("approval_timeout_seconds must be positive")
        if values.get("approval_timeout_seconds", 120) > 3600:
            raise ValueError("approval_timeout_seconds cannot exceed 3600 seconds")

    from pydantic import model_validator
    @model_validator(mode="after")
    def validate_all(self) -> "Settings":
        self.validate_relationships(self.__dict__)
        return self


# Singleton instance
settings = Settings()
