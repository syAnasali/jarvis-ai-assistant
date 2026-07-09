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


class MemoryExtractionError(MemorySystemError):
    """Raised when memory extraction from text fails."""


class MemoryCandidateValidationError(MemoryValidationError):
    """Raised when validation of a MemoryCandidate fails."""


class ConversationError(JarvisError):
    """Base exception class for all conversation subsystem errors."""


class ConversationValidationError(ConversationError):
    """Raised when conversation domain validation fails (e.g. naive datetimes)."""


class ConversationNotFoundError(ConversationError):
    """Raised when a requested conversation session or message is not found."""


class ConversationPersistenceError(ConversationError):
    """Raised when a conversation database or persistence operation fails."""


class SessionStateError(ConversationError):
    """Raised when an illegal session state transition or operation occurs."""


class PlanningError(JarvisError):
    """Base exception class for all planning subsystem errors."""


class PlanningParseError(PlanningError):
    """Raised when parsing or extracting planner response fails."""


class PlanValidationError(PlanningError):
    """Raised when plan structure or constraint validation fails."""


class PlanExecutionError(PlanningError):
    """Raised when unexpected internal plan execution fails."""


class PlanLimitError(PlanningError):
    """Raised when task plan limits (e.g. max steps) are exceeded."""


class StepExecutionError(PlanningError):
    """Raised when a specific plan step execution fails."""
