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

    application_resolution_max_candidates: int = 10
    application_discovery_max_entries: int = 2000

    filesystem_list_max_entries: int = 100
    filesystem_write_max_chars: int = 100000
    filesystem_relative_path_max_length: int = 512

    desktop_window_list_limit: int = 50
    desktop_text_max_chars: int = 5000
    desktop_text_preview_chars: int = 80
    desktop_window_wait_timeout_seconds: int = 10
    desktop_window_poll_interval_ms: int = 200

    voice_enabled: bool = False
    voice_sample_rate: int = 16000
    voice_channels: int = 1
    voice_sample_width: int = 2
    voice_wait_timeout_seconds: int = 10
    voice_max_utterance_seconds: int = 30
    voice_min_speech_seconds: float = 0.25
    voice_end_silence_seconds: float = 0.8
    stt_provider: str = "faster_whisper"
    stt_model: str = "tiny"
    stt_device: str = "auto"
    stt_compute_type: str = "auto"
    stt_language: str | None = None
    tts_provider: str = "pyttsx3"
    tts_voice: str | None = None
    tts_rate: int | None = None
    tts_max_chars: int = 1000


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
        if values.get("application_resolution_max_candidates", 10) <= 0:
            raise ValueError("application_resolution_max_candidates must be positive")
        if values.get("application_discovery_max_entries", 2000) <= 0:
            raise ValueError("application_discovery_max_entries must be positive")
            
        if values.get("filesystem_list_max_entries", 100) <= 0:
            raise ValueError("filesystem_list_max_entries must be positive")
        if values.get("filesystem_list_max_entries", 100) > 1000:
            raise ValueError("filesystem_list_max_entries cannot exceed 1000")
        if values.get("filesystem_write_max_chars", 100000) <= 0:
            raise ValueError("filesystem_write_max_chars must be positive")
        if values.get("filesystem_write_max_chars", 100000) > 10000000:
            raise ValueError("filesystem_write_max_chars cannot exceed 10000000")
        if values.get("filesystem_relative_path_max_length", 512) <= 0:
            raise ValueError("filesystem_relative_path_max_length must be positive")
        if values.get("filesystem_relative_path_max_length", 512) > 4096:
            raise ValueError("filesystem_relative_path_max_length cannot exceed 4096")

        if values.get("desktop_window_list_limit", 50) <= 0:
            raise ValueError("desktop_window_list_limit must be positive")
        if values.get("desktop_window_list_limit", 50) > 500:
            raise ValueError("desktop_window_list_limit cannot exceed 500")
        if values.get("desktop_text_max_chars", 5000) <= 0:
            raise ValueError("desktop_text_max_chars must be positive")
        if values.get("desktop_text_max_chars", 5000) > 100000:
            raise ValueError("desktop_text_max_chars cannot exceed 100000")
        if values.get("desktop_text_preview_chars", 80) <= 0:
            raise ValueError("desktop_text_preview_chars must be positive")
        if values.get("desktop_window_wait_timeout_seconds", 10) <= 0:
            raise ValueError("desktop_window_wait_timeout_seconds must be positive")
        if values.get("desktop_window_poll_interval_ms", 200) <= 0:
            raise ValueError("desktop_window_poll_interval_ms must be positive")

        if values.get("voice_sample_rate", 16000) <= 0:
            raise ValueError("voice_sample_rate must be positive")
        if values.get("voice_channels", 1) not in (1, 2):
            raise ValueError("voice_channels must be 1 (mono) or 2 (stereo)")
        if values.get("voice_sample_width", 2) not in (1, 2, 4):
            raise ValueError("voice_sample_width must be 1, 2, or 4")
        if values.get("voice_wait_timeout_seconds", 10) <= 0:
            raise ValueError("voice_wait_timeout_seconds must be positive")
        if values.get("voice_max_utterance_seconds", 30) <= 0:
            raise ValueError("voice_max_utterance_seconds must be positive")
        if values.get("voice_min_speech_seconds", 0.25) < 0:
            raise ValueError("voice_min_speech_seconds must be non-negative")
        if values.get("voice_end_silence_seconds", 0.8) < 0:
            raise ValueError("voice_end_silence_seconds must be non-negative")
        if values.get("tts_max_chars", 1000) <= 0:
            raise ValueError("tts_max_chars must be positive")


    from pydantic import model_validator
    @model_validator(mode="after")
    def validate_all(self) -> "Settings":
        self.validate_relationships(self.__dict__)
        return self


# Singleton instance
settings = Settings()
