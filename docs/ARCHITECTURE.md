# Jarvis AI Assistant Architecture

This document details the software architecture of the Jarvis AI Assistant, a production-oriented, offline-first local AI desktop helper.

---

## 1. Purpose

The architecture of Jarvis is designed to be highly modular to ensure clean separation of concerns, facilitate unit testing of subsystems, and decouple local model runtimes from high-level agent logic. By enforcing strict boundaries, the system supports interactive user interfaces (Terminal CLI, Voice Pipeline, PySide6 Desktop GUI), safe tool execution runtimes, persistent SQLite databases, and task planning without requiring core orchestrator changes.

---

## 2. Architectural Principles

- **Separation of Concerns**: User interaction, planning logic, inference backends, and infrastructure settings occupy dedicated modules with limited, well-defined communication channels.
- **Dependency Abstraction**: High-level components communicate with models through interfaces (e.g., `BaseLLMProvider`), preventing codebases from coupling to specific provider APIs.
- **Provider Isolation**: All vendor-specific communication logic is encapsulated within concrete provider modules (e.g., `OllamaProvider`), hiding implementation details from the rest of the application.
- **Synchronized Blocking Approval**: Confirmation-level tool calls pause execution, block standard input on native console threads, and require explicit human decision before execution resumes.
- **Lifecycle Management**: The application state is represented as an explicit state machine, ensuring predictable setups, execution loops, and resource release.
- **Configuration Externalization**: Application defaults and settings are declared in central configurations (`constants.py` and `settings.py`) and loaded via type-safe environments (`Pydantic Settings`).
- **Explicit Planning and Execution Boundaries**: Requests route through an intent router, heuristic planner, task executor, and safe tool executor boundary.

---

## 3. High-Level Architecture

The diagram below maps the runtime components and wiring in the codebase:

```
[ User Interfaces (CLI / Voice / PySide6 GUI) ]
                      │
                      ▼
             [ Application ] ───(Setup)───► [ Bootstrap ] ──► [ DirectoryManager ]
                      │                            │
                      │ (Registers)                ▼
                      ├───────────────────► [ JarvisLogger ] (daily rotating log files)
                      │
                      ▼ (Initializes & owns)
             [ ServiceContainer ]
                      │
                      ▼ (Holds Singletons)
                      ├─ Settings
                      ├─ JarvisLogger
                      ├─ LLMManager
                      ├─ MemoryManager
                      ├─ ApprovalManager
                      └─ AgentController ──► [ ContextManager ] (active request tracker)
                                │
                                ▼
                         [ Conversation ] (SQLite WAL Persistent Database)
                                │
                                ▼ (Routes)
                   ┌────────────┴────────────┐
                   ▼                         ▼
            [ Router / Planner ]   [ TaskExecutor / TaskPlan ]
                   │                         │
                   └────────────┬────────────┘
                                │
                                ▼
                         [ AgentRunner ]
                                │
                   ┌────────────┴────────────┐
                   ▼                         ▼
          [ LLMManager / Ollama ]    [ ToolExecutor ]
                   │                         │
                   ▼                         ▼
          (Model Generation)       {"permission": "CONFIRMATION"}
                                             │
                                             ▼
                                  [ ApprovalManager / CLI ]
                                  (Indefinite Console Wait)
```

---

## 4. Core Infrastructure

- **`Application`**: Located in `app/core/application.py`. Primary system orchestrator managing dependency registration, state machine transitions, interactive loop driving, and clean service shutdown.
- **`Bootstrap`**: Located in `app/core/bootstrap.py`. Coordinates environment verification during startup, validating directory existences and activating standard logs.
- **`DirectoryManager`**: Located in `app/core/bootstrap.py`. Creates and verifies required runtime directories (`DATA_DIR`, `LOG_DIR`, `CONFIG_DIR`) as defined by system paths.
- **`ApplicationState`**: Located in `app/core/lifecycle.py`. Represents the active state machine of the runtime process (`STARTING`, `INITIALIZING`, `RUNNING`, `STOPPING`, `STOPPED`, `ERROR`).
- **`ServiceContainer`**: Located in `app/core/container.py`. Service-locator container storing active singletons (e.g., `Settings`, `JarvisLogger`, `LLMManager`, `ApprovalManager`, `MemoryManager`) to prevent tight coupling.
- **`Settings`**: Located in `app/config/settings.py`. Type-safe configuration loader using `pydantic-settings` to load, map, and validate environment variables.
- **`JarvisLogger`**: Located in `app/core/logger.py`. Encapsulates `loguru` setup logic, exposing consistent level methods (`info`, `warning`, `error`, etc.) and establishing console/rotating file loggers.

---

## 5. Agent & Planning Engine

- **`AgentController`**: Located in `app/agent/controller.py`. Gateway for request processing. Records prompts, triggers router/planner, dispatches direct or planned execution, normalizes outputs, and persists dialogue logs.
- **`AgentRunner`**: Located in `app/agent/runner.py`. Action loop orchestrator executing model turns, parsing tool calls, enforcing tool policies, and streaming output fragments.
- **`Conversation`**: Located in `app/agent/conversation.py`. Manages session-isolated ordered message logs backed by SQLite persistent storage (`ConversationRepository`).
- **`ConversationContextPolicy`**: Located in `app/agent/context.py`. Enforces message token and message-count budget constraints, summarizing older history to trim prompt size.
- **`ExecutionRouter`**: Located in `app/agent/router.py`. Heuristic intent classifier routing requests to `DIRECT` execution or `PLANNED` multi-step execution.
- **`TaskPlanner`**: Located in `app/planning/planner.py`. Generates structured `TaskPlan` instances with sequential steps.
- **`PlanValidator`**: Located in `app/planning/validator.py`. Validates structural integrity, dependency ordering, and tool schema safety of planned steps.
- **`TaskExecutor`**: Located in `app/planning/executor.py`. Sequential plan runner executing `TOOL`, `REASONING`, and `SYNTHESIS` steps, collecting intermediate observations and generating final user summaries.

---

## 6. AI & LLM Subsystem

- **`BaseLLMProvider`**: Located in `app/ai/interfaces.py`. Abstract base class defining model client interactions (`initialize`, `shutdown`, `generate`, `generate_stream`, `health_check`).
- **`LLMManager`**: Located in `app/ai/manager.py`. Manages model providers, registers backends, loads model dependencies, and routes generation requests to active providers.
- **`OllamaProvider`**: Located in `app/ai/providers/ollama.py`. Implements `BaseLLMProvider` using Ollama API (`qwen2.5:7b` / `qwen3:8b`).
- **`ResponseParser`**: Located in `app/ai/parser.py`. Normalizes raw response payloads returned by LLM APIs into `AgentResponse` blocks and extracts structured tool calls.
- **`PromptManager`**: Located in `app/ai/prompts.py`. Exposes dynamic system prompts, tool use policies, and context trimming wrappers.

---

## 7. Action Approval Runtime

- **`ApprovalManager`**: Located in `app/approval/manager.py`. Orchestrates `PendingAction` creation, approval, rejection, and atomic consumption. Default `timeout_seconds = None` for interactive CLI usage eliminates automatic expiration during user input.
- **`SQLiteApprovalRepository`**: Located in `app/approval/repository.py`. SQLite database persistence for pending actions with atomic status transitions (`PENDING` -> `APPROVED` / `REJECTED` -> `EXECUTED`).
- **`prompt_user_approval`**: Located in `app/approval/cli.py`. Terminal confirmation UI that purges stale stdin buffers (`msvcrt.kbhit()`), prints formatted action banners, and blocks indefinitely on native console `input()` until explicit `y`/`n` input is provided.
- **`Application.waiting_for_approval`**: Located in `app/core/application.py`. Synchronization flag preventing concurrent chat prompt iterations while an approval is pending.

---

## 8. Persistent Memory Subsystem

- **`Memory`**: Located in `app/memory/models.py`. Immutable domain model for durable facts, preferences, project context, and workspace knowledge.
- **`SQLiteMemoryRepository`**: Located in `app/memory/repository.py`. SQLite database engine storing memories with JSON metadata.
- **`MemoryManager`**: Located in `app/memory/manager.py`. Memory domain manager handling CRUD operations and ID generation.
- **`LexicalMemoryRetriever`**: Located in `app/memory/retrieval.py`. Performs hybrid token matching and importance ranking to select relevant memories.
- **`MemoryContextBuilder`**: Located in `app/memory/context.py`. Formats selected memories into markdown prompt blocks (`[RELEVANT LONG-TERM MEMORY]`).
- **`LLMMemoryExtractor`**: Located in `app/memory/extraction.py`. LLM-based memory candidate extraction under deterministic low-temperature profile.
- **`MemoryEvidenceValidator`**: Located in `app/memory/validation.py`. Strict evidence verification enforcing verbatim claim support and first-person perspective.
- **`MemoryWriteCoordinator`**: Located in `app/memory/coordinator.py`. Asynchronous single-worker thread pool executing memory extraction and writes without blocking user chat responses.

---

## 9. Tool Execution Engine & 23 Built-in Tools

- **`ToolRegistry`**: Located in `app/tools/registry.py`. Thread-safe tool catalog managing schema registrations and keyword filtering.
- **`ToolExecutor`**: Located in `app/tools/executor.py`. Boundary executor handling permissions, approval interception, worker pool execution, timeouts, and cancellations.
- **`ToolFilter`**: Located in `app/tools/filter.py`. Dynamic category and keyword tool schema injector reducing prompt tokens.

### 23 Implemented Tools:
1. **Filesystem**: `inspect_path`, `list_directory`, `create_directory`, `create_file`, `write_text_file`, `move_path`, `delete_path`.
2. **Desktop Automation**: `get_active_window`, `list_visible_windows`, `focus_window`, `type_text`, `press_key`, `press_hotkey`, `click_screen`.
3. **Application Launcher**: `list_installed_applications`, `find_installed_application`, `resolve_application`, `launch_application`.
4. **System & Process**: `get_current_time`, `get_system_info`, `get_disk_usage`, `list_running_processes`, `find_running_process`.

---

## 10. Voice Interaction Pipeline & Full-Duplex Runtime

Jarvis incorporates a provider-neutral, full-duplex local voice assistant runtime in `app/voice/` (see detailed guide in [docs/VOICE_RUNTIME.md](file:///c:/Code-Playground/jarvis-ai-assistant/docs/VOICE_RUNTIME.md)):
- **`FasterWhisperProvider`**: Located in `app/voice/stt.py`. Local offline speech recognition using faster-whisper (`tiny`, `base`, `small`, `medium` models) with automatic GPU/CPU fallback and streaming frame transcription.
- **`PiperProvider` & `PyTTSx3TTSProvider`**: Located in `app/voice/tts.py`. Local neural speech synthesis (`PiperProvider`) and SAPI5 fallback engine with sentence-level streaming synthesis.
- **`VoiceActivityDetector` (`EnergyBasedVAD`)**: Located in `app/voice/vad.py`. Dynamic RMS energy-based voice activity detector for silence, speech start, and speech end boundaries without fixed recording duration limits.
- **`WakeWordDetector` (`LocalWakeWordDetector`)**: Located in `app/voice/wakeword.py`. Wake word detector for "Hey Jarvis" supporting `ALWAYS_LISTENING`, `PUSH_TO_TALK`, and `DISABLED` modes.
- **`VoiceSession`**: Located in `app/voice/session.py`. Active session state tracker maintaining states (`IDLE`, `LISTENING`, `TRANSCRIBING`, `PROCESSING`, `SPEAKING`, `INTERRUPTED`, `WAITING_APPROVAL`) and timing metrics.
- **`PlaybackManager`**: Located in `app/voice/playback.py`. Thread-safe audio output manager with instant `stop()` and `interrupt()` barge-in capabilities.
- **`VoicePipeline`**: Located in `app/voice/pipeline.py`. Core full-duplex loop linking STT -> AgentController -> Sentence-level streaming TTS -> Speaker. Features real-time barge-in interruption and spoken confirmation approval parsing (*"yes"/"approve"* vs *"no"/"cancel"*).

---

## 11. PySide6 Desktop GUI & System Tray

- **`AppWindow`**: Located in `app/ui/main_window.py`. Primary PySide6 window layout with chat pane, session sidebar, status bar, and activity timeline.
- **`ChatWidget`**: Located in `app/ui/chat_widget.py`. Scrollable conversation view rendering message bubbles, code blocks, and inline approval cards.
- **`ApprovalCardWidget`**: Located in `app/ui/widgets.py`. Interactive Qt approval widget displaying confirmation action details with Approve/Reject action buttons.
- **`JarvisSystemTray`**: Located in `app/ui/system_tray.py`. Windows system tray icon and context menu with global hotkey support (`ctrl+alt+j`).

---

## 12. Priority Inference Scheduler

- **`InferenceScheduler`**: Located in `app/ai/scheduler.py`. Priority-queue inference dispatcher prioritizing interactive foreground chat queries (`InferencePriority.FOREGROUND`) over asynchronous background memory extraction tasks (`InferencePriority.BACKGROUND`).

---

## 13. Runtime Reliability, Safeguards, and Recovery

- **Recursion safeguards**: Restricts TaskExecutor recursion depth to 2 to prevent infinite recovery loops.
- **Duplicate tool call prevention**: Tracks failed tool parameters to prevent repeating failing calls.
- **Timeout boundaries**: Configurable execution timeouts for tools (30s default) and plans (120s limit).
- **Graceful exception classification**: Distinguishes `RecoverableError` from `NonRecoverableError` to report clean, user-safe error messages without stack trace leaks.
- **Master Developer Production Validation**: Master script (`scripts/run_production_validation.py`) verifying 100% PASS across 405 unit tests, 9 integration scenarios, 7 stress tests, and 8 performance latency benchmarks.

---

## 14. Provider-Neutral Local Vision Runtime

Jarvis incorporates an offline-first local Vision Runtime in `app/vision/` (see detailed architecture in [docs/VISION_RUNTIME.md](file:///c:/Code-Playground/jarvis-ai-assistant/docs/VISION_RUNTIME.md)):
- **`OllamaVisionProvider` & `MockVisionProvider`**: Located in `app/vision/providers.py`. Interoperable multimodal local VLM backend (`llava`, `qwen-vl`) with zero-crash mock fallback.
- **`PILScreenCapturer`**: Located in `app/vision/capture.py`. Full-screen, active window, and region bounding box capturer.
- **`PILClipboardImageRetriever`**: Located in `app/vision/clipboard.py`. Retrieves clipboard images safely.
- **`LocalOCREngine`**: Located in `app/vision/ocr.py`. Extractor for text, code snippets, terminal outputs, and error dialogs.
- **`VisionPipeline` & `VisionManager`**: Located in `app/vision/pipeline.py` and `app/vision/manager.py`. End-to-end visual analysis pipeline with synchronous and token streaming capabilities.
- **Built-in System Tools**: `capture_screen`, `explain_error`, `read_clipboard_image`, `analyze_region`.

---

## 15. Autonomous Hierarchical Planning Engine (`app/planner/`)

Jarvis incorporates an autonomous, hierarchical planning engine (`app/planner/`) that decomposes complex goals into Directed Acyclic Graphs (DAGs) of executable task nodes while delegating step execution to existing runtime components (`ToolExecutor`, `VisionPipeline`, `VoicePipeline`, `MemoryManager`, `ApprovalManager`).

### Key Planning Architectural Components:
- **`TaskGraph`**: Directed Acyclic Graph structure supporting sequential tasks, parallel branches, topological dependency sorting, and cycle validation (`app/planner/graph.py`).
- **`GoalDecomposer`**: Decomposes high-level objectives into DAG task nodes with post-condition verification actions (`app/planner/planner.py`).
- **`PlanExecutor`**: Execution loop delegating tasks to system runtimes without duplicating execution logic (`app/planner/executor.py`).
- **`OutcomeTaskVerifier`**: Verifies post-condition outcome rules for completed tasks (`app/planner/verifier.py`).
- **`AutonomousRecoveryEngine`**: Handles step failures via retries, alternative tool selection, rollbacks, or user prompts (`app/planner/recovery.py`).
- **`SQLitePlanRepository`**: Durable plan state persistence in SQLite (`data/jarvis.db`) supporting plan pause, resume, cancellation, and restart (`app/planner/repository.py`).
- **`PlanProgressTracker`**: Computes completion percentages, renders progress bars (`Task 4/12 [███████░░░░] 58%`), and notifies subscribers (`app/planner/progress.py`).
- **Built-in System Tools**: `decompose_goal`, `execute_plan`, `get_plan_status`, `control_plan`.

---

## 16. Personal Knowledge Base (RAG) Subsystem (`app/knowledge/`)

Jarvis incorporates a provider-neutral Personal Knowledge Base (`app/knowledge/`) enabling document ingestion, parsing, multi-strategy chunking, local vector indexing, hybrid retrieval (vector similarity + BM25 keyword matching), reranking, and structured citations.

### Key RAG Architectural Components:
- **`UnifiedDocumentParser`**: Extensible parser for PDF, DOCX, TXT, MD, HTML, JSON, CSV, Code files, and Git repositories (`app/knowledge/parser.py`).
- **`ConfigurableTextChunker`**: Paragraph, semantic, recursive, and code-aware chunking strategies (`app/knowledge/chunker.py`).
- **`EmbeddingProvider`**: Local VLM embedding connection (`OllamaEmbeddingProvider`) with deterministic offline fallback (`LocalHashEmbeddingProvider`).
- **`LocalVectorStore` & `SQLiteKnowledgeRepository`**: Local vector index and SQLite database persistence (`data/jarvis.db`) (`app/knowledge/index.py`, `app/knowledge/repository.py`).
- **`HybridRetrieverEngine` & `ResultRerankerEngine`**: Combines vector cosine similarity with BM25 keyword matching and cross-feature reranking (`app/knowledge/retriever.py`, `app/knowledge/reranker.py`).
- **`StructuredCitationFormatter`**: Generates structured citations with clickable `file:///` URLs (`app/knowledge/citations.py`).
- **Memory Isolation Safeguard**: Retrieved RAG document chunks are strictly isolated and never automatically saved to long-term memory.
- **Built-in System Tools**: `ingest_document`, `search_knowledge`, `summarize_document`, `list_documents`, `remove_document`.

---

## 17. Provider-Neutral Plugin SDK & Extension Framework (`app/plugins/`)

Jarvis incorporates an isolated, provider-neutral Plugin SDK (`app/plugins/`) allowing external extensions, tools, voice commands, and event subscribers to be added without modifying core codebase files.

### Key Plugin Architectural Components:
- **`PluginManifestParser`**: Parses and validates `plugin.yaml` or `plugin.json` manifests (`app/plugins/manifest.py`).
- **`PluginPermissionSandbox`**: Enforces strict permission boundaries (`filesystem`, `desktop`, `voice`, `vision`, `knowledge`, `planner`, `network`, `memory`, `confirmation`) (`app/plugins/sandbox.py`).
- **`JarvisPluginSDK`**: Isolated API facade exposing safe capability access (`sdk.tools`, `sdk.memory`, `sdk.voice`, `sdk.vision`, `sdk.knowledge`, `sdk.planner`, `sdk.events`, `sdk.logger`, `sdk.settings`) (`app/plugins/sdk.py`).
- **`PluginEventBus`**: Thread-safe publish/subscribe event engine for lifecycle and execution events (`app/plugins/events.py`).
- **`DynamicPluginLoader`**: Topological dependency sorting and fault-isolated module loading (`app/plugins/loader.py`).
- **`PluginManager`**: Catalog registry, enabling/disabling, health reporting, and runtime `reload_plugin(plugin_id)` hot reloading (`app/plugins/manager.py`).
- **Built-in System Tools**: `list_plugins`, `enable_plugin`, `disable_plugin`, `reload_plugin`.

---

## 18. Observability & Developer Console Subsystem (`app/observability/`)

Jarvis incorporates a production-quality Observability subsystem (`app/observability/`) that collects live runtime metrics, distributed tracing spans, and chronological request event timelines across all 8 major subsystems.

### Key Observability Architectural Components:
- **`RuntimeMetricsCollector`**: Aggregates live counters, latencies, and rates across LLM, Agent, Memory, Knowledge, Planner, Voice, Vision, and Plugin runtimes (`app/observability/metrics.py`).
- **`DistributedTracer`**: Manages request-bound `trace_id` tracking and parent/child `Span` start, end, duration, and status calculation (`app/observability/tracing.py`).
- **`EventTimelineRecorder`**: Captures chronological request step events (`app/observability/timeline.py`).
- **`SQLiteMetricsRepository`**: Persists metrics, traces, and timeline events into SQLite (`data/jarvis.db`) with retention cleanup (`app/observability/repository.py`).
- **`TelemetryExporterImpl`**: Renders telemetry snapshots into JSON files, CSV spreadsheets, and formatted Markdown reports (`app/observability/exporters.py`).
- **`HealthDashboardAPI`**: Diagnostic status endpoints powering future Phase 25 Desktop GUI diagnostic panels (`app/observability/dashboard.py`).
- **Built-in System Tools**: `get_health_report`, `get_runtime_telemetry`, `export_telemetry`.

---

## 19. Desktop GUI Foundation (`app/gui/`)

Jarvis incorporates a production-quality PySide6 desktop application shell (`app/gui/`) consuming existing backend Application and Observability APIs.

### Key GUI Architectural Components:
- **`JarvisGuiApplication`**: PySide6 `QApplication` bootstrapper, theme applicator, and event loop runner (`app/gui/app.py`).
- **`MainWindow`**: Main application shell assembling `SidebarNav`, `TopToolbar`, `QStackedWidget` navigation stack, and `StatusBarNav` (`app/gui/main_window.py`).
- **`NavigationManager`**: Page routing manager managing index switching across all 9 registered views (`app/gui/navigation.py`).
- **`SidebarNav` & `TopToolbar`**: Collapsible sidebar menu and top action bar (`app/gui/widgets/sidebar.py`, `app/gui/widgets/toolbar.py`).
- **`StatusBarNav`**: Telemetry status bar displaying model, provider, active session, memory count, plugin count, and system status (`app/gui/widgets/status_bar.py`).
- **`ThemeManager`**: Dark and light mode QSS stylesheets with HSL color tokens (`app/gui/theme.py`).
- **`GuiSettingsManager`**: Persists window geometry, active page, and theme preferences via `QSettings` (`app/gui/settings.py`).

---

## 20. Chat Interface & Streaming Experience (`app/gui/chat/`)

Jarvis incorporates a production-quality PySide6 Chat Interface (`app/gui/chat/`) consuming backend LLM streaming, Tool, Memory, and Planner runtimes via thread-safe `QThread` workers.

### Key Chat Architectural Components:
- **`ChatController`**: Manages active `ConversationSession` history and QThread worker invocation (`app/gui/chat/controller.py`).
- **`ChatWorker`**: PySide6 `QThread` executing backend prompt generation off the main UI thread and emitting signals (`app/gui/chat/worker.py`).
- **`StreamingHandler`**: Manages real-time token updates to `StreamingBubble` without blocking PySide6 event loop (`app/gui/chat/streaming.py`).
- **`MarkdownRenderer`**: Converts Markdown to PySide6 Rich Text HTML (`app/gui/chat/markdown.py`).
- **`CodeBlockWidget`**: Monospace code container with syntax highlighting, language badges, and copy buttons (`app/gui/chat/syntax.py`).
- **`CitationWidget`**: Expandable RAG document citation cards with clickable `file:///` scheme links (`app/gui/chat/citations.py`).
- **`AttachmentBar`**: Multi-file attachment intake supporting images, documents, clipboard pasting, and drag & drop (`app/gui/chat/attachments.py`).

---

## 21. Voice & Vision Workspace (`app/gui/voice/`, `app/gui/vision/`)

Jarvis incorporates production-quality PySide6 Voice and Vision Workspaces (`app/gui/voice/`, `app/gui/vision/`) consuming backend speech and screen inspection runtimes via thread-safe `QThread` workers.

### Key Voice & Vision Architectural Components:
- **`VoiceController` & `VoiceWorker`**: Manages Push-to-Talk, Always-Listening toggle, and off-thread STT/TTS execution (`app/gui/voice/controller.py`, `app/gui/voice/worker.py`).
- **`WaveformWidget`**: Live animated microphone volume level meter (`app/gui/voice/waveform.py`).
- **`VoiceSessionWidget`**: Displays wake-word status ("Jarvis"), user transcript, assistant speech, and barge-in interrupt button (`app/gui/voice/session.py`).
- **`VisionController` & `VisionWorker`**: Manages desktop screen grabs, active window capture, region cropping, and off-thread OCR processing (`app/gui/vision/controller.py`, `app/gui/vision/worker.py`).
- **`RegionSelectionOverlay`**: Interactive semi-transparent desktop bounding box region selector (`app/gui/vision/overlays.py`).
- **`AnnotationLayerWidget`**: Bounding box overlay for OCR text and visual region highlights (`app/gui/vision/annotations.py`).
- **`ImageViewerWidget`**: Interactive image preview canvas supporting zoom and pan (`app/gui/vision/viewer.py`).







