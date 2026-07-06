# Project Structure

This document outlines the directory structure and file responsibilities of the Jarvis AI Assistant project repository.

---

## Repository File Tree

```
jarvis-ai-assistant/
├── app/                              # Primary application source package
│   ├── __init__.py                   # Package initialization
│   ├── agent/                        # Agent engine and workflow orchestration
│   │   ├── __init__.py
│   │   ├── context.py                # Session metadata and topic tracker
│   │   ├── controller.py             # Agent orchestrator and workflow gateway
│   │   ├── conversation.py           # In-memory message history tracking
│   │   ├── executor.py               # Action router for execution plans
│   │   ├── intent.py                 # Intent data structures and classifications
│   │   ├── messages.py               # Message schemas and message roles
│   │   ├── models.py                 # Dataclasses for request/response payloads
│   │   └── planner.py                # Classification and plan formulator
│   ├── ai/                           # AI provider abstractions and model connectors
│   │   ├── __init__.py
│   │   ├── formatter.py              # Message payload translator for models
│   │   ├── interfaces.py             # BaseLLMProvider abstract definition
│   │   ├── manager.py                # Provider registry and routing manager
│   │   ├── parser.py                 # Provider output normalizer
│   │   ├── prompts.py                # Prompt template manager (placeholders)
│   │   └── providers/                # Concrete AI API client implementations
│   │       ├── __init__.py
│   │       └── ollama.py             # Local Ollama client implementation
│   ├── config/                       # Application settings loader
│   │   ├── __init__.py
│   │   └── settings.py               # Pydantic Settings env configurations
│   ├── core/                         # Orchestrator and lifecycle management
│   │   ├── __init__.py
│   │   ├── application.py            # Main application lifecycle entry
│   │   ├── bootstrap.py              # Startup checks and path creator
│   │   ├── constants.py              # Centralized constants and system paths
│   │   ├── container.py              # Service-locator dependency container
│   │   ├── exceptions.py             # Custom Jarvis system exception hierarchy
│   │   ├── lifecycle.py              # Application lifecycle states enum
│   │   └── logger.py                 # Loguru log setup handlers
│   ├── memory/                       # Persistent memory domain and SQLite store
│   │   ├── __init__.py               # Package initialization and exports
│   │   ├── coordinator.py            # MemoryWriteCoordinator for background writes
│   │   ├── context.py                # MemoryContextBuilder for prompt formatting
│   │   ├── extraction.py             # LLMMemoryExtractor
│   │   ├── guard.py                  # SecretGuard for credential filtering
│   │   ├── interfaces.py             # MemoryRepository, MemoryRetriever, MemoryExtractor
│   │   ├── manager.py                # MemoryManager orchestrator class
│   │   ├── models.py                 # Memory, MemoryType, MemorySource, MemoryCandidate, etc.
│   │   ├── parser.py                 # MemoryExtractionParser
│   │   ├── repository.py             # SQLiteMemoryRepository implementation
│   │   ├── retrieval.py              # LexicalMemoryRetriever
│   │   ├── validation.py             # MemoryEvidenceValidator for exact-evidence constraints
│   │   └── write_service.py          # MemoryWriteService
│   ├── prompts/                      # External prompt files (reserved)
│   │   └── __init__.py               # Reserved for future implementation
│   ├── services/                     # Third-party integrations (reserved)
│   │   └── __init__.py               # Reserved for future implementation
│   ├── tools/                        # Agent execution tools (reserved)
│   │   └── __init__.py               # Reserved for future implementation
│   ├── ui/                           # Graphical Interface modules (reserved)
│   │   └── __init__.py               # Reserved for future implementation
│   ├── utils/                        # Shared helper utilities
│   │   ├── __init__.py
│   │   ├── banner.py                 # Console banner text renderer
│   │   └── id_generator.py           # Centralized message/request ID generator
│   └── voice/                        # Voice processing routines (reserved)
│       └── __init__.py               # Reserved for future implementation
├── assets/                           # Static UI media resources (empty)
├── data/                             # Created application data folder (empty)
├── docs/                             # System design specifications
│   ├── ARCHITECTURE.md               # Architecture details and layers
│   ├── PROJECT_STRUCTURE.md          # Project structure mapping (this file)
│   ├── REQUEST_FLOW.md               # User prompt request life flow
│   └── ROADMAP.md                    # Multi-phase project development roadmap
├── logs/                             # Daily rotating log directory (empty)
├── scripts/                          # Administration and diagnostic scripts
│   ├── __init__.py
│   └── test_ollama_provider.py       # Isolated Ollama client verification script
├── tests/                            # Diagnostic system test suites (empty)
├── .env.example                      # Settings placeholders template
├── .gitignore                        # Filesystem tracking exclusions list
├── LICENSE                           # Project terms (empty by default)
├── main.py                           # Application initialization entry point
├── pyproject.toml                    # Pytest/Ruff build configuration
└── requirements.txt                  # System dependency specifications
```

---

## Directory Responsibilities

### `app/agent/`
Contains the agent's core decision, state, and conversation flow logic.
- **`controller.py`**: Coordinates request processing, user interactions, message history, plan creation, execution, and outputs.
- **`planner.py`**: Classifies inputs to formulate an `ExecutionPlan`. Currently hardcoded to target `CHAT` LLM generation.
- **`executor.py`**: Routes request executions based on plans, calling `LLMManager` or throwing errors for unimplemented structures.
- **`intent.py`**: Defines the `IntentType` enum (e.g. `CHAT`, `TOOL`) and `Intent` metadata dataclass.
- **`conversation.py`**: Holds session-specific message logs in-memory.
- **`context.py`**: Manages volatile session details like current topics and active request structures.
- **`messages.py`**: Implements the immutable `Message` dataclass and `MessageRole` enum.
- **`models.py`**: Defines communication dataclasses (`AgentRequest`, `AgentResponse`, `ToolCall`).
- **`response.py`**: Creational builder class for constructing standardized `AgentResponse` instances.

### `app/ai/`
Handles LLM backend connections, formatting pipelines, and parser boundaries.
- **`interfaces.py`**: Defines the `BaseLLMProvider` abstract base class contract.
- **`manager.py`**: Implements `LLMManager`, coordinating registrations and switches between active provider targets.
- **`formatter.py`**: Translates internal message structures into API-ready payload dictionaries.
- **`parser.py`**: Extracts raw text blocks from model responses (supporting dictionaries and SDK payloads).
- **`prompts.py`**: Serves default instruction prompts.
- **`providers/ollama.py`**: Implements model communication with local Ollama APIs using the official `ollama` SDK.

### `app/config/`
Manages configuration and environments.
- **`settings.py`**: Loads and validates environment configurations using Pydantic Settings.

### `app/core/`
Manages application lifecycles, bootstraps, setups, and common configurations.
- **`application.py`**: Coordinates setup boundaries, service registries, and triggers terminal I/O.
- **`bootstrap.py`**: Verifies directories and activates default log formatters.
- **`constants.py`**: Houses application-wide constants and filesystem paths.
- **`container.py`**: Provides a service-locator registry for system singletons.
- **`exceptions.py`**: Implements the custom `JarvisError` hierarchy.
- **`lifecycle.py`**: Defines the `ApplicationState` enum.
- **`logger.py`**: Sets up rotating and console loggers via Loguru.

### `app/memory/`
Manages durable facts, projects, preferences, and assistant context persistence.
- **`models.py`**: Declares Memory, MemoryType, MemorySource, MemoryCandidate, etc.
- **`interfaces.py`**: Defines abstract base class contracts for repositories, retrievers, and extractors.
- **`repository.py`**: Coordinates raw SQLite table CRUD executions.
- **`manager.py`**: Handles validation rules, timezone-aware UTC datetime timestamps, and delegates operations to injected repositories.
- **`retrieval.py`**: Token-based deterministic lexical retriever.
- **`context.py`**: Compiles matches into system prompt context with constraint enforcement.
- **`extraction.py`**: LLM memory candidate extractor using a dedicated profile.
- **`parser.py`**: Parser to extract memory list JSON.
- **`validation.py`**: MemoryEvidenceValidator enforcing verbatim checking and claim-support conservatism.
- **`write_service.py`**: Coordinates extraction, confidence filter, secret guard, duplicate checks, and writes.
- **`coordinator.py`**: MemoryWriteCoordinator orchestrating background async executions and resource serialization.
- **`guard.py`**: Narrow deterministic pattern matching secret guard.

### `app/utils/`
Provides shared utilities.
- **`id_generator.py`**: Centralizes unique ID generation for messages, requests, responses, and memories.
- **`banner.py`**: Houses console startup and shutdown banners.

### Reserved Packages (Reserved for Future Implementation)
The following directories are empty placeholder packages (except for `__init__.py`) reserved for future phases of the project roadmap:
- **`app/prompts/`**: Externalized prompt files.
- **`app/services/`**: Third-party API integrations (e.g. email, calendars).
- **`app/tools/`**: Local sandboxed system execution tools.
- **`app/ui/`**: Desktop GUI views and window widgets (PySide6).
- **`app/voice/`**: Audio capture, VAD, Whisper STT, and Kokoro TTS modules.

---

## Scripts & Tests

- **`scripts/`**: Administration and diagnostic scripts.
  - **`test_ollama_provider.py`**: Isolated Ollama client verification script.
  - **`test_memory_retrieval.py`**: Lexical memory retriever diagnostics.
  - **`test_agent_memory.py`**: E2E memory retrieval test.
  - **`test_memory_extraction.py`**: Memory extraction diagnostics.
  - **`test_memory_write.py`**: Memory write service diagnostics.
  - **`test_memory_restart.py`**: Cross-restart memory persistence diagnostics.
  - **`test_memory_extraction_precision.py`**: Verbatim evidence and claim-support conservatism diagnostic.
  - **`test_memory_response_latency.py`**: Measure response latency and verify background non-blocking execution.
- **`tests/`**: Test suite directory containing unit tests covering the core agent engine, memory retrieval, context building, memory extraction parser, and memory write service.
