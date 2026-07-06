"""Jarvis AI Assistant Memory Subsystem package initialization."""

from app.memory.models import Memory, MemoryType, MemorySource, MemoryMatch, MemoryRetrievalResult
from app.memory.interfaces import MemoryRepository, MemoryRetriever
from app.memory.repository import SQLiteMemoryRepository
from app.memory.manager import MemoryManager
from app.memory.retrieval import LexicalMemoryRetriever
from app.memory.context import MemoryContextBuilder, MEMORY_CONTEXT_MARKER

__all__ = [
    "Memory",
    "MemoryType",
    "MemorySource",
    "MemoryMatch",
    "MemoryRetrievalResult",
    "MemoryRepository",
    "MemoryRetriever",
    "SQLiteMemoryRepository",
    "MemoryManager",
    "LexicalMemoryRetriever",
    "MemoryContextBuilder",
    "MEMORY_CONTEXT_MARKER",
]
