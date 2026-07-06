"""Custom exception hierarchy for Jarvis AI Assistant."""


class JarvisError(Exception):
    """Base exception class for all Jarvis AI Assistant errors."""


class ConfigurationError(JarvisError):
    """Raised when there is a configuration error or validation failure."""


class LLMError(JarvisError):
    """Raised when an operation with the language model fails."""


class MemoryError(JarvisError):
    """Raised when there is an issue with memory storage or retrieval.
    Preserved for backward compatibility, behaves as MemorySystemError base.
    """


class MemorySystemError(MemoryError):
    """Base exception class for all memory subsystem errors."""


class MemoryValidationError(MemorySystemError):
    """Raised when memory validation fails."""


class MemoryNotFoundError(MemorySystemError):
    """Raised when a requested memory cannot be found."""


class MemoryPersistenceError(MemorySystemError):
    """Raised when a memory database or storage operation fails."""


class VoiceError(JarvisError):
    """Raised when speech-to-text or text-to-speech services fail."""


class ToolExecutionError(JarvisError):
    """Raised when a system tool fails to execute or fails verification."""


class ApplicationStartupError(JarvisError):
    """Raised when the application fails to start up correctly."""
