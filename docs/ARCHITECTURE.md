# Jarvis AI Assistant Architecture

This document details the software architecture of the Jarvis AI Assistant, a production-oriented, local AI desktop helper.

---

## 1. Purpose

The architecture of Jarvis is designed to be highly modular to ensure clean separation of concerns, facilitate unit testing of subsystems, and decouple local model runtimes from high-level agent logic. By enforcing strict boundaries, the system is designed to support the implementation of future interfaces, tool runtimes, and local audio capture without requiring core orchestrator changes.

---

## 2. Architectural Principles

- **Separation of Concerns**: User interaction, planning logic, inference backends, and infrastructure settings occupy dedicated modules with limited, well-defined communication channels.
- **Dependency Abstraction**: High-level components communicate with models through interfaces (e.g. `BaseLLMProvider`), preventing codebases from coupling to specific provider APIs.
- **Provider Isolation**: All vendor-specific communication logic is encapsulated within concrete provider modules (e.g. `OllamaProvider`), hiding implementation details from the rest of the application.
- **Lifecycle Management**: The application state is represented as an explicit state machine, ensuring predictable setups, execution loops, and resource release.
- **Configuration Externalization**: Application defaults and settings are declared in central configurations (`constants.py` and `settings.py`) and loaded via type-safe environments.
- **Explicit Planning and Execution Boundaries**: Task routing decisions are decoupled into an explicit classification stage (`Planner`) and execution stage (`Executor`), laying the foundation for future tool usage routing.

---

## 3. High-Level Architecture

The diagram below maps the runtime components and wiring in the current codebase:

```
[ Entry Point (main.py) ]
          │
          ▼
   [ Application ] ──────(Setup)──────► [ Bootstrap ] ──► [ DirectoryManager ]
          │                                   │
          │ (Registers)                       ▼
          ├──────────────────────────► [ JarvisLogger ] (daily rotating file)
          │
          ▼ (Initializes & owns)
  [ ServiceContainer ]
          │
          ▼ (Holds singletons)
          ├─ Settings
          ├─ JarvisLogger
          ├─ LLMManager
          └─ AgentController ──► [ ContextManager ] (active request tracker)
                    │
                    ▼
             [ Conversation ] (in-memory message log list)
                    │
                    ▼ (Uses)
              [ Planner ] ──► [ ExecutionPlan ] (Intent: CHAT)
                    │
                    ▼ (Uses)
              [ Executor ] ──(Generates format payload)──► [ MessageFormatter ]
                    │
                    ▼
              [ LLMManager ] ──► [ BaseLLMProvider ] (Interface)
                                          ▲
                                          │ (Implements)
                                  [ OllamaProvider ] ──► [ Local Ollama Server ]
                                          │
                                          ▼ (Returns ChatResponse/dict)
                                  [ ResponseParser ]
                                          │
                                          ▼
                                   [ AgentResponse ]
```

---

## 4. Core Infrastructure

- **`Application`**: Located in `app/core/application.py`. Serves as the primary system orchestrator. It manages the dependency registration, setups the runtime state, and drives the interactive terminal input loop.
- **`Bootstrap`**: Located in `app/core/bootstrap.py`. Coordinates environment verification during startup, validating directory existences and activating standard logs.
- **`DirectoryManager`**: Located in `app/core/bootstrap.py`. Creates and verifies required runtime directories (`DATA_DIR`, `LOG_DIR`, `CONFIG_DIR`) as defined by system paths.
- **`ApplicationState`**: Located in `app/core/lifecycle.py`. Represents the active state machine of the runtime process (`STARTING`, `INITIALIZING`, `RUNNING`, `STOPPING`, `STOPPED`, `ERROR`).
- **`ServiceContainer`**: Located in `app/core/container.py`. A lightweight service-locator container storing active singletons (e.g. `Settings`, `JarvisLogger`, `LLMManager`) to prevent tight coupling.
- **`Settings`**: Located in `app/config/settings.py`. Type-safe configuration loader using `pydantic-settings` to load, map, and validate variables from the environment.
- **`JarvisLogger`**: Located in `app/core/logger.py`. Encapsulates `loguru` setup logic, exposing consistent level methods (`info`, `warning`, `error`, etc.) and establishing console/rotating file loggers.

---

## 5. Agent Engine

- **`AgentController`**: Located in `app/agent/controller.py`. Serves as the gateway for request processing. It records prompts, triggers planners, executes workflows, normalizes outputs, and completes dialogue logs.
- **`Conversation`**: Located in `app/agent/conversation.py`. Manages the session-specific ordered history list of message objects. It is strictly in-memory and holds no database configurations.
- **`ContextManager`**: Located in `app/agent/context.py`. Maintains short-lived state variables of the active user session, such as active topics and current `AgentRequest` tracking.
- **`Intent` & `IntentType`**: Located in `app/agent/intent.py`. Data structures describing classified user requests. The `IntentType` enum defines categories such as `CHAT`, `TOOL`, `MEMORY_READ`, `MEMORY_WRITE`, `SYSTEM`, and `UNKNOWN`.
- **`Planner`**: Located in `app/agent/planner.py`. Evaluates incoming prompts to generate an `ExecutionPlan`. Currently, the `Planner` uses a hardcoded rule that always outputs a `CHAT` intent requiring LLM generation. No AI-based classification is currently implemented.
- **`ExecutionPlan`**: Located in `app/agent/planner.py`. An immutable dataclass indicating whether the execution loop must call the LLM (`use_llm=True`), call system tools (`use_tools=False`), or write/retrieve database memories (`use_memory=False`).
- **`Executor`**: Located in `app/agent/executor.py`. Handles routing of plans. If `use_llm` is enabled, it dispatches message payloads to `LLMManager` and returns the raw model completions. It raises a `NotImplementedError` for tool or memory executions.

---

## 6. AI Layer

- **`BaseLLMProvider`**: Located in `app/ai/interfaces.py`. Abstract base class defining model client interactions (`initialize`, `shutdown`, `generate`, `health_check`).
- **`LLMManager`**: Located in `app/ai/manager.py`. Manages available model providers, registers backends, loads model dependencies, and routes generation prompts to active provider instances.
- **`MessageFormatter`**: Located in `app/ai/formatter.py`. Standardizes internal message models into dictionaries containing role and text payloads expected by LLM APIs.
- **`ResponseParser`**: Located in `app/ai/parser.py`. Normalizes raw response payloads returned by LLM APIs (supporting both dictionary logs and SDK `ChatResponse` objects) into standard `AgentResponse` blocks.
- **`PromptManager`**: Located in `app/ai/prompts.py`. Exposes placeholder system, safety, and developer instructions.
- **`OllamaProvider`**: Located in `app/ai/providers/ollama.py`. Implements `BaseLLMProvider` using the official `ollama` SDK. It coordinates server connections, lists installed models to verify model availability, and executes chat queries.

---

## 7. Dependency Direction

Jarvis enforces a strict Directed Acyclic Graph (DAG) for all imports and dependencies:

```
[ app/utils/ ] ◄── [ app/config/ ] ◄── [ app/ai/ ] ◄── [ app/agent/ ] ◄── [ app/core/ ]
```

- Infrastructure utilities (`app/utils/` and `app/core/constants.py`) depend on nothing.
- Settings depend only on Constants.
- The AI Layer (`app/ai/`) imports models from the Agent Layer (`app/agent/`) but does not depend on the Orchestrator (`app/core/`).
- The Agent Layer (`app/agent/`) depends on the AI Layer (`app/ai/`) and Config systems.
- The Orchestration Layer (`app/core/`) imports all sub-systems at runtime to configure the `ServiceContainer` and wire execution pathways.

---

## 8. Application Lifecycle

The runtime processes transitions through states governed by `ApplicationState`:

```
 [STOPPED] ──(initialize)──► [STARTING] ──► [INITIALIZING] ──► [STOPPED (Initialized)]
                                                                     │
    ┌────────────────────────────────────────────────────────────────┘
    │
    ▼
 [RUNNING] ──(KeyboardInterrupt / exit)──► [STOPPING] ──► [STOPPED]
    │
    └──(Exception during execution)──► [ERROR] ──► [STOPPED]
```

1. **Initialization**:
   - `Application` starts in `STOPPED`. Transitions to `STARTING`, registers basic settings, and calls `Bootstrap`.
   - `Bootstrap` transitions to `INITIALIZING`, creates folder paths, and configures the logger.
   - On success, state resets to `STOPPED` (fully initialized).
2. **Execution Loop**:
   - Calling `run()` transitions state to `RUNNING`.
   - The CLI reads input, queries the agent controller, prints assistant outputs, and continues.
3. **Shutdown**:
   - Catching `exit`/`quit`/`bye` or standard interrupts (`KeyboardInterrupt`, `EOFError`) breaks the loop and calls `shutdown()`.
   - State transitions to `STOPPING`. The active LLM provider shutdown method is triggered.
   - References are cleared, and the application terminates in the `STOPPED` state.

---

## 9. Extension Points

The architecture defines dedicated boundaries for implementing future capabilities:
- **Additional LLM Providers**: Inheriting from `BaseLLMProvider` inside `app/ai/providers/` allows registering new runtimes (e.g. OpenAI, llama.cpp) inside the `LLMManager` registry.
- **Tools**: Future tools can be defined inside `app/tools/` and registered with a tool orchestrator, with execution routed when `ExecutionPlan.use_tools` is enabled.
- **Memory**: Persistent memory engines (SQLite/SQLAlchemy) will implement database structures inside `app/memory/`, with storage and retrieval activated when `ExecutionPlan.use_memory` is enabled.
- **Streaming**: Subclassing `ResponseParser` and modifying the `generate` API will support chunk-by-chunk stream formatting.
- **Voice**: Low-latency speech interfaces will reside inside `app/voice/`, hooking audio streams to the controller as a custom user prompt source.
- **GUI**: A PySide6 desktop window can replace the CLI entry loop, importing the same `Application` orchestrator and servicecontainer resources.

---

## 10. Current Architectural Limitations

- **Terminal Presentation**: Input and output are locked to terminal standard standard stream descriptors (`stdin`, `stdout`).
- **Single Model Backend**: Currently only implements `OllamaProvider` as a concrete LLM provider.
- **Static Planning Logic**: The `Planner` does not classify intents dynamically; it hardcodes the plan route to `CHAT` (using the LLM).
- **No Persistent Storage**: Conversation logs are volatile and vanish immediately when the CLI process exits.
- **No Tool Capabilities**: System calls, directory reads, and web searches cannot be performed by the agent loop.
- **Synchronous inference**: Generation requests block execution until the model completes its response, with no token streaming.
