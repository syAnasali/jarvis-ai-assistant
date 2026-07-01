"""Application lifecycle state enum."""

from enum import Enum


class ApplicationState(Enum):
    """Enum representing the lifecycle states of the Jarvis AI Assistant."""

    STARTING = "STARTING"
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"
