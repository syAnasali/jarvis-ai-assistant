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


class ApprovalError(JarvisError):
    """Base exception class for all approval subsystem errors."""


class ApprovalPersistenceError(ApprovalError):
    """Raised when an approval database or persistence operation fails."""


class FilesystemError(ToolExecutionError):
    """Base exception class for all filesystem operation errors."""

    def __init__(self, message: str, error_code: str = "FILESYSTEM_ERROR") -> None:
        super().__init__(message)
        self.error_code = error_code


class InvalidRootError(FilesystemError):
    """Raised when the specified logical root is invalid or unknown."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="INVALID_ROOT")


class InvalidPathError(FilesystemError):
    """Raised when a relative path contains illegal characters, absolute path markers, etc."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="INVALID_PATH")


class PathEscapeError(FilesystemError):
    """Raised when directory traversal escapes the trusted root boundaries."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="PATH_ESCAPE")


class PathNotFoundError(FilesystemError):
    """Raised when a requested path target does not exist."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="NOT_FOUND")


class PathAlreadyExistsError(FilesystemError):
    """Raised when a path target already exists but was expected to be created/moved."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="ALREADY_EXISTS")


class TypeMismatchError(FilesystemError):
    """Raised when a file was expected but a directory was found (or vice-versa)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="TYPE_MISMATCH")


class DirectoryNotEmptyError(FilesystemError):
    """Raised when attempting to delete a non-empty directory without recursive flag."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="DIRECTORY_NOT_EMPTY")


class BlockedExtensionError(FilesystemError):
    """Raised when a file write target has a blacklisted executable/script extension."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="BLOCKED_EXTENSION")


class ContentTooLargeError(FilesystemError):
    """Raised when content to write exceeds configured size constraints."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="CONTENT_TOO_LARGE")


class UnsupportedPathError(FilesystemError):
    """Raised when a path is a UNC, device, or system path that is unsupported."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="UNSUPPORTED_PATH")


class OSFilesystemError(FilesystemError):
    """Raised when an underlying OS or shutil filesystem exception occurs."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="FILESYSTEM_ERROR")


# =====================================================================
# DESKTOP INTERACTION EXCEPTIONS
# =====================================================================

class DesktopError(ToolExecutionError):
    """Base exception class for all desktop interaction operation errors."""

    def __init__(self, message: str, error_code: str = "DESKTOP_BACKEND_ERROR") -> None:
        super().__init__(message)
        self.error_code = error_code


class WindowNotFoundError(DesktopError):
    """Raised when the specified target window is not found."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="WINDOW_NOT_FOUND")


class WindowAmbiguousError(DesktopError):
    """Raised when a window query is ambiguous and matches multiple windows."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="WINDOW_AMBIGUOUS")


class WindowStaleError(DesktopError):
    """Raised when a window ID exists but the window is no longer alive."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="WINDOW_STALE")


class WindowNotVisibleError(DesktopError):
    """Raised when a focus target exists but is not visible."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="WINDOW_NOT_VISIBLE")


class FocusFailedError(DesktopError):
    """Raised when window focus operation fails verification."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="FOCUS_FAILED")


class ForegroundChangedError(DesktopError):
    """Raised when the foreground window changes before execution of a guarded tool."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="FOREGROUND_CHANGED")


class InvalidTextError(DesktopError):
    """Raised when input text contains invalid characters (e.g. NUL)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="INVALID_TEXT")


class TextTooLongError(DesktopError):
    """Raised when input text exceeds maximum length constraints."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="TEXT_TOO_LONG")


class InvalidKeyError(DesktopError):
    """Raised when a keyboard key is not in the allowlist."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="INVALID_KEY")


class InvalidHotkeyError(DesktopError):
    """Raised when a keyboard shortcut combination is invalid or blocked."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="INVALID_HOTKEY")


class InvalidCoordinatesError(DesktopError):
    """Raised when mouse coordinates are negative or exceed screen bounds."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="INVALID_COORDINATES")


class UnsupportedButtonError(DesktopError):
    """Raised when a mouse button is not left or right."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="UNSUPPORTED_BUTTON")


class DesktopBackendError(DesktopError):
    """Raised when a native Windows API call or backend action fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="DESKTOP_BACKEND_ERROR")


