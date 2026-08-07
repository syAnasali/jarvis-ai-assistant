# Project Structure

This document outlines the complete directory structure and module responsibilities of the Jarvis AI Assistant repository.

---

## Repository File Tree

```
jarvis-ai-assistant/
├── app/                              # Primary application source package
│   ├── agent/                        # Agent state, context policies, and execution runner
│   │   ├── __init__.py
│   │   ├── context.py                # Context window budget policy (ConversationContextPolicy)
│   │   ├── controller.py             # AgentController entry gateway and request router
│   │   ├── conversation.py           # Session conversation manager wrapper
│   │   ├── intent.py                 # IntentType classifications and intent models
│   │   ├── messages.py               # Message roles, Message models, and JSON sanitizers
│   │   ├── models.py                 # AgentRequest, AgentResponse, AgentRunResult, ToolCall
│   │   ├── planner.py                # Legacy planner wrapper
│   │   ├── router.py                 # ExecutionRouter for direct vs planned routing
│   │   └── runner.py                 # AgentRunner action loop and streaming executor
│   ├── ai/                           # AI provider abstractions and inference scheduling
│   │   ├── __init__.py
│   │   ├── formatter.py              # Message payload formatter for LLM APIs
│   │   ├── interfaces.py             # BaseLLMProvider abstract interface
│   │   ├── manager.py                # LLMManager multi-provider registry
│   │   ├── parser.py                 # ResponseParser output normalizer
│   │   ├── prompts.py                # Prompt templates and dynamic system prompts
│   │   ├── scheduler.py              # Priority InferenceScheduler (Foreground vs Background)
│   │   └── providers/                # Concrete model clients
│   │       ├── __init__.py
│   │       └── ollama.py             # Local Ollama client implementation
│   ├── approval/                     # Action Approval Runtime
│   │   ├── __init__.py
│   │   ├── cli.py                    # Terminal approval UI with msvcrt buffer clearing and native input loop
│   │   ├── manager.py                # ApprovalManager orchestrator with cancel_all_pending
│   │   └── repository.py             # SQLiteApprovalRepository implementation
│   ├── config/                       # Application settings loader
│   │   ├── __init__.py
│   │   └── settings.py               # Pydantic Settings env configurations
│   ├── conversation/                 # Persistent Conversation Subsystem
│   │   ├── __init__.py
│   │   ├── manager.py                # ConversationManager orchestrator
│   │   ├── models.py                 # ConversationSession models
│   │   └── repository.py             # SQLiteConversationRepository implementation
│   ├── core/                         # Core infrastructure & lifecycle management
│   │   ├── __init__.py
│   │   ├── application.py            # Main Application class and waiting_for_approval state
│   │   ├── bootstrap.py              # Startup environment verifier and path creator
│   │   ├── constants.py              # Centralized system constants and paths
│   │   ├── container.py              # ServiceContainer dependency injection registry
│   │   ├── exceptions.py             # Custom JarvisError exception hierarchy
│   │   ├── lifecycle.py              # ApplicationState enum
│   │   └── logger.py                 # Loguru log setup handlers
│   ├── gui/                          # PySide6 Desktop GUI Foundation Subsystem
│   │   ├── animations.py             # PageTransitionManager for smooth QGraphicsOpacityEffect cross-fades
│   │   ├── command_palette.py        # CommandPaletteDialog for Ctrl+Shift+P quick action launcher
│   │   ├── session.py                # SessionRestoreManager for auto-saving drafts and window geometry
│   │   ├── shortcuts.py              # GlobalShortcutManager for application-wide hotkeys
│   │   ├── approval/                 # Native Approval Center Subsystem
│   │   │   ├── __init__.py           # Package exports
│   │   │   ├── controller.py         # ApprovalController managing pending queue & ApprovalWorker
│   │   │   ├── details.py            # ApprovalDetailsWidget tool action inspector
│   │   │   ├── dialog.py             # ApprovalDialog modal popup approval dialog
│   │   │   ├── history.py            # ApprovalHistoryWidget approval log table
│   │   │   ├── queue.py              # ApprovalQueueWidget pending tool request table
│   │   │   ├── risk.py               # RiskBadgeWidget color-coded risk badge renderer
│   │   │   └── worker.py             # ApprovalWorker QThread executing approvals off-thread
│   │   ├── chat/                     # Chat Interface & Streaming Experience Subsystem
│   │   ├── __init__.py               # Package exports
│   │   ├── attachments.py            # AttachmentWidget and AttachmentBar for file intake
│   │   ├── citations.py              # CitationWidget rendering expandable RAG document references
│   │   ├── controller.py             # ChatController orchestrating session history & QThread workers
│   │   ├── markdown.py               # MarkdownRenderer converting Markdown to PySide6 Rich Text HTML
│   │   ├── knowledge/                # Knowledge Center Subsystem
│   │   │   ├── __init__.py           # Package exports
│   │   │   ├── browser.py            # KnowledgeBrowserWidget table view of indexed documents
│   │   │   ├── citations.py          # KnowledgeCitationsWidget score breakdowns & snippets
│   │   │   ├── controller.py         # KnowledgeController managing ingestion & KnowledgeWorker
│   │   │   ├── ingestion.py          # IngestionDropZoneWidget drag & drop target
│   │   │   ├── preview.py            # DocumentPreviewWidget multi-format previewer
│   │   │   ├── search.py             # KnowledgeSearchWidget hybrid vector + BM25 search bar
│   │   │   └── worker.py             # KnowledgeWorker QThread running ingestion & search off-thread
│   │   ├── memory/                   # Memory Center Subsystem
│   │   │   ├── __init__.py           # Package exports
│   │   │   ├── browser.py            # MemoryBrowserWidget table view of memory records
│   │   │   ├── controller.py         # MemoryController managing CRUD operations & MemoryWorker
│   │   │   ├── details.py            # MemoryDetailsWidget inspector panel
│   │   │   ├── editor.py             # MemoryEditorWidget modal dialog
│   │   │   ├── filters.py            # MemoryFilterWidget dropdown filters
│   │   ├── observability/            # Observability Dashboard Subsystem
│   │   │   ├── __init__.py           # Package exports
│   │   │   ├── charts.py             # TelemetryChartsWidget live QPainter trend curves
│   │   │   ├── controller.py         # ObservabilityController managing QTimer refresh & ObservabilityWorker
│   │   │   ├── export.py             # ExportTelemetryDialog JSON/CSV/Markdown report dialog
│   │   │   ├── health.py             # HealthOverviewWidget 8-subsystem status grid
│   │   │   ├── metrics.py            # MetricsGridWidget live telemetry counter cards
│   │   │   ├── requests.py           # RequestDetailsWidget trace inspector
│   │   │   ├── timeline.py           # TimelineViewWidget chronological request timeline
│   │   │   ├── traces.py             # TraceTreeWidget distributed tracing span tree
│   │   │   └── worker.py             # ObservabilityWorker QThread executing telemetry collection
│   │   ├── planner/                  # Planner Dashboard Subsystem
│   │   │   ├── __init__.py           # Package exports
│   │   │   ├── controller.py         # PlannerController managing DAG graph & PlannerWorker
│   │   │   ├── execution.py          # LiveExecutionLogsWidget streaming log panel
│   │   │   ├── graph.py              # DagGraphWidget visual DAG node graph & inspector
│   │   │   ├── progress.py           # ProgressTrackerWidget progress bar & control buttons
│   │   │   ├── recovery.py           # RecoveryPanelWidget retry history & rollback status
│   │   │   ├── timeline.py           # ExecutionTimelineWidget chronological step timeline
│   │   │   ├── widgets.py            # PlanMetricsWidget & PlanCardWidget summaries
│   │   │   └── worker.py             # PlannerWorker QThread executing DAG nodes off-thread
│   │   ├── plugins/                  # Plugin Manager Subsystem
│   │   │   ├── __init__.py           # Package exports
│   │   │   ├── browser.py            # PluginBrowserWidget table of installed plugins
│   │   │   ├── controller.py         # PluginController managing plugin states & PluginWorker
│   │   │   ├── details.py            # PluginDetailsWidget manifest inspector
│   │   │   ├── logs.py               # PluginLogsWidget plugin lifecycle log stream
│   │   │   ├── marketplace.py        # PluginMarketplaceWidget catalog placeholder
│   │   │   ├── permissions.py        # PluginPermissionsWidget declared permissions viewer
│   │   │   └── worker.py             # PluginWorker QThread executing plugin actions off-thread
│   │   ├── vision/                   # Vision Workspace Subsystem
│   │   │   ├── __init__.py           # Package exports
│   │   │   ├── annotations.py        # AnnotationLayerWidget for OCR bounding box overlays
│   │   │   ├── controller.py         # VisionController managing capture workflows & VisionWorker
│   │   │   ├── overlays.py           # RegionSelectionOverlay bounding box region selector
│   │   │   ├── viewer.py             # ImageViewerWidget interactive canvas
│   │   │   └── worker.py             # VisionWorker QThread running capture & OCR off UI thread
│   │   ├── voice/                    # Voice Workspace Subsystem
│   │   │   ├── __init__.py           # Package exports
│   │   │   ├── controller.py         # VoiceController managing Push-to-Talk & VoiceWorker
│   │   │   ├── microphone.py         # MicrophoneDeviceSelector audio input device dropdown
│   │   │   ├── session.py            # VoiceSessionWidget displaying live transcripts & barge-in
│   │   │   ├── waveform.py           # WaveformWidget animated microphone volume level meter
│   │   │   └── worker.py             # VoiceWorker QThread running STT & TTS off UI thread
│   │   ├── dialogs.py                # ConfirmationDialog, ErrorDialog, AboutDialog
│   │   ├── icons.py                  # IconManager generating vector and procedural icons
│   │   ├── main_window.py            # MainWindow application shell layout
│   │   ├── navigation.py             # NavigationManager managing view index routing
│   │   ├── resources.py              # ResourceLoader managing asset paths
│   │   ├── settings.py               # GuiSettingsManager persisting QSettings
│   │   ├── theme.py                  # ThemeManager supporting Dark/Light QSS stylesheets
│   │   ├── views/                    # 9 Registered page views (Chat, Planner, Memory, etc.)
│   │   └── widgets/                  # SidebarNav, TopToolbar, StatusBarNav, ToastNotification
│   ├── knowledge/                    # Personal Knowledge Base (RAG) Subsystem
│   │   ├── __init__.py               # Package exports & factory constructors
│   │   ├── chunker.py                # ConfigurableTextChunker (Paragraph, Semantic, Recursive, Code-Aware)
│   │   ├── citations.py              # StructuredCitationFormatter producing clickable file:/// URLs
│   │   ├── embeddings.py             # OllamaEmbeddingProvider & LocalHashEmbeddingProvider
│   │   ├── index.py                  # LocalVectorStore performing vector cosine similarity search
│   │   ├── ingestion.py              # IngestionPipeline (Parse -> Chunk -> Embed -> Index)
│   │   ├── interfaces.py             # DocumentParser, TextChunker, EmbeddingProvider, VectorStore contracts
│   │   ├── manager.py                # KnowledgeManager subsystem coordinator & telemetry
│   │   ├── models.py                 # Document, DocumentChunk, KnowledgeQuery, RetrievalResult, Citation
│   │   ├── parser.py                 # UnifiedDocumentParser for PDF, DOCX, TXT, MD, HTML, Code, CSV, JSON
│   │   ├── reranker.py               # ResultRerankerEngine scoring candidate matches & diversity
│   │   ├── repository.py             # SQLiteKnowledgeRepository implementation (data/jarvis.db)
│   ├── observability/                # Observability & Developer Console Subsystem
│   │   ├── __init__.py               # Package exports
│   │   ├── dashboard.py              # HealthDashboardAPI providing status endpoints
│   │   ├── events.py                 # System observability events
│   │   ├── exceptions.py             # Observability exception hierarchy
│   │   ├── exporters.py              # TelemetryExporterImpl producing JSON, CSV, and Markdown exports
│   │   ├── interfaces.py             # MetricsCollector, Tracer, TimelineRecorder, Exporter contracts
│   │   ├── manager.py                # ObservabilityManager subsystem coordinator
│   │   ├── metrics.py                # RuntimeMetricsCollector aggregating LLM, Agent, Memory, Knowledge, Planner, Voice, Vision, Plugin metrics
│   │   ├── models.py                 # MetricRecord, Span, TimelineEvent, HealthStatus, TelemetrySummary
│   │   ├── repository.py             # SQLiteMetricsRepository storing metrics, traces, and timeline events in data/jarvis.db
│   │   ├── timeline.py               # EventTimelineRecorder capturing request processing steps
│   │   └── tracing.py                # DistributedTracer managing trace IDs and span hierarchies
│   ├── plugins/                      # Provider-Neutral Plugin SDK & Extension Framework
│   │   ├── __init__.py               # Package exports
│   │   ├── events.py                 # PluginEventBus thread-safe publish/subscribe event bus
│   │   ├── exceptions.py             # Plugin exception hierarchy
│   │   ├── interfaces.py             # Plugin abstract base class & contracts
│   │   ├── lifecycle.py              # PluginLifecycleCoordinator handling startup & shutdown
│   │   ├── loader.py                 # DynamicPluginLoader with topological dependency sorting
│   │   ├── manager.py                # PluginManager handling load, unload, reload, enable, disable
│   │   ├── manifest.py               # PluginManifestParser & validator for plugin.yaml/json
│   │   ├── models.py                 # PluginManifest, PluginStatus, PluginPermission, PluginInfo, PluginEvent
│   │   ├── registry.py               # PluginRegistry catalog
│   │   ├── sandbox.py                # PluginPermissionSandbox enforcing permission boundaries
│   │   └── sdk.py                    # JarvisPluginSDK facade exposing safe APIs
│   ├── memory/                       # Persistent Multi-Type Memory Subsystem
│   │   ├── __init__.py
│   │   ├── context.py                # MemoryContextBuilder for prompt formatting
│   │   ├── coordinator.py            # MemoryWriteCoordinator background thread pool
│   │   ├── extraction.py             # LLMMemoryExtractor
│   │   ├── guard.py                  # SecretGuard credential pattern matcher
│   │   ├── interfaces.py             # Abstract Memory contracts
│   │   ├── manager.py                # MemoryManager orchestrator
│   │   ├── models.py                 # Memory domain models (Fact, Preference, Project, Context)
│   │   ├── parser.py                 # MemoryExtractionParser
│   │   ├── related.py                # RelatedMemoryFinder candidate matcher
│   │   ├── repository.py             # SQLiteMemoryRepository implementation
│   │   ├── resolution.py             # MemoryResolutionValidator & MemoryResolutionExecutor
│   │   ├── resolver.py               # LLMMemoryResolver
│   │   ├── retrieval.py              # LexicalMemoryRetriever
│   │   ├── validation.py             # MemoryEvidenceValidator enforcing verbatim constraints
│   │   └── write_service.py          # MemoryWriteService
│   ├── planning/                     # Task Planning & Execution Engine
│   │   ├── __init__.py
│   │   ├── executor.py               # TaskExecutor for sequential multi-step plans
│   │   ├── metrics.py                # PlanningMetrics tracking
│   │   ├── models.py                 # TaskPlan, StepObservation, PlanExecutionResult
│   │   ├── parser.py                 # PlanParser for structured plan text parsing
│   │   ├── planner.py                # TaskPlanner formulation engine
│   │   ├── prompts.py                # Reasoning and synthesis prompts
│   │   └── validator.py             # PlanValidator step dependency checker
│   ├── planner/                      # Autonomous Hierarchical Planning Engine
│   │   ├── __init__.py               # Package exports & factory constructors
│   │   ├── executor.py               # PlanExecutor delegating steps to ToolExecutor, Vision, Voice, Memory
│   │   ├── graph.py                  # TaskGraph DAG data structure & topological sort
│   │   ├── interfaces.py             # HierarchicalPlanner, TaskGraphExecutor, TaskVerifier contracts
│   │   ├── manager.py                # PlannerManager subsystem coordinator & telemetry
│   │   ├── models.py                 # Goal, Plan, PlanNode, ExecutionStep, VerificationResult, RecoveryAction, PlanProgress
│   │   ├── planner.py                # GoalDecomposer & HierarchicalPlanner
│   │   ├── progress.py               # PlanProgressTracker computing percentage & rendering progress bars
│   │   ├── recovery.py               # AutonomousRecoveryEngine handling retries & rollbacks
│   │   ├── repository.py             # SQLitePlanRepository implementation (data/jarvis.db)
│   │   ├── scheduler.py              # TaskScheduler managing branch execution & queueing
│   │   └── verifier.py               # OutcomeTaskVerifier checking post-condition outcome rules
│   ├── services/                     # Domain Services & System Resolvers
│   │   ├── applications/             # Windows Application Discovery & Resolver
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   └── resolver.py
│   │   ├── desktop/                  # Policy-Controlled Desktop Interaction Service
│   │   │   ├── __init__.py
│   │   │   ├── backend.py            # Native Ctypes Windows API backend
│   │   │   ├── policy.py             # DesktopPolicy key allowlist & bounds checker
│   │   │   ├── resolver.py           # Window candidate resolver
│   │   │   └── service.py            # DesktopService with Foreground Safety Guard
│   │   └── filesystem/               # Root-Bounded Filesystem Service
│   │       ├── __init__.py
│   │       ├── policy.py             # FilesystemPolicy logical root mapper
│   │       ├── resolver.py           # Path resolution and traversal guard
│   │       └── service.py            # FilesystemService atomic operations
│   ├── tools/                        # 23 Built-in Execution Tools
│   │   ├── __init__.py
│   │   ├── base.py                   # BaseTool abstract base class
│   │   ├── executor.py               # ToolExecutor with worker pool & timeout policy
│   │   ├── filter.py                 # Dynamic ToolFilter schema injector
│   │   ├── models.py                 # ToolPermission & ToolResult schemas
│   │   ├── registry.py               # ToolRegistry thread-safe catalog
│   │   └── builtin/                  # Concrete tool implementations
│   │       ├── applications.py       # Application Discovery & Launch tools
│   │       ├── desktop.py            # Desktop Window & Automation tools
│   │       ├── disk.py               # Disk usage inspection tools
│   │       ├── filesystem.py         # Root-bounded filesystem tools
│   │       ├── process.py            # Process inspection & search tools
│   │       └── system.py             # System info & time tools
│   ├── ui/                           # PySide6 Desktop GUI Package
│   │   ├── __init__.py
│   │   ├── app.py                    # MainWindow assembly and controller thread coordinator
│   │   ├── theme.py                  # Dark stylesheet CSS theme
│   │   ├── threads.py                # Background AgentWorker and VoiceWorker QThreads
│   │   ├── tray.py                   # System tray icon and context menus
│   │   └── widgets/                  # Modular PySide6 Component Widgets
│   │       ├── approval_card.py      # Confirmation action review card widget
│   │       ├── chat_view.py          # Scrollable conversation view
│   │       ├── settings_dialog.py    # Configuration settings dialog
│   │       ├── sidebar.py            # Session list and metrics sidebar
│   │       ├── status_bar.py         # System status bar
│   │       ├── timeline.py           # Execution activity timeline widget
│   │       └── top_bar.py            # Top header bar
│   └── voice/                        # Full-Duplex Offline Voice Runtime Package
│       ├── __init__.py               # Package exports & factory constructors
│       ├── capture.py                # PyAudio microphone capture stream
│       ├── interfaces.py             # AudioCapture, VAD, WakeWordDetector, STT, and TTS interfaces
│       ├── manager.py                # VoiceManager subsystem coordinator & telemetry
│       ├── models.py                 # AudioFrame, AudioSegment, TranscriptionResult, SpeechSynthesisResult, VoiceState
│       ├── pipeline.py               # Full-duplex VoicePipeline with sentence-level streaming TTS & spoken approvals
│       ├── playback.py               # PlaybackManager handling audio stream queueing & barge-in interruption
│       ├── runtime.py                # Push-to-talk state machine and AgentController adapter loop
│       ├── session.py                # VoiceSession tracker maintaining state machine & metrics
│       ├── stt.py                    # FasterWhisperProvider (tiny, base, small, medium) with GPU/CPU fallback
│       ├── tts.py                    # PiperProvider & PyTTSx3TTSProvider local speech synthesis engines
│       ├── vad.py                    # EnergyBasedVAD dynamic speech & silence boundary detector
│       └── wakeword.py               # LocalWakeWordDetector supporting "Hey Jarvis" and mode configurations
│   └── vision/                       # Provider-Neutral Local Vision Runtime Package
│       ├── __init__.py               # Package exports & factory constructors
│       ├── annotation.py             # ImageAnnotator bounding box overlays, highlights, and crops
│       ├── capture.py                # PILScreenCapturer full-screen, active window, and region capture
│       ├── clipboard.py              # PILClipboardImageRetriever system clipboard image extraction
│       ├── interfaces.py             # VisionProvider, ScreenCapturer, ClipboardImageRetriever, OCREngine contracts
│       ├── manager.py                # VisionManager subsystem coordinator & telemetry
│       ├── models.py                 # VisionImage, VisionRequest, VisionResponse, OCRResult, ImageMetadata
│       ├── ocr.py                    # LocalOCREngine text, code, terminal, and dialog box extractor
│       ├── pipeline.py               # VisionPipeline image intake, OCR, VLM analysis, and token streaming
│       └── providers.py              # OllamaVisionProvider (llava, qwen-vl) and MockVisionProvider fallback
├── assets/                           # Static UI media resources
├── data/                             # Application database directory (`jarvis.db`)
├── docs/                             # Architecture and design guides
│   ├── ARCHITECTURE.md
│   ├── PROJECT_STRUCTURE.md
│   ├── REQUEST_FLOW.md
│   └── ROADMAP.md
├── logs/                             # Daily rotating log files (`jarvis.log`)
├── scripts/                          # Admin, validation, and diagnostic scripts
│   ├── run_production_validation.py  # Master Developer Validation Suite
│   ├── regression/                   # Subsystem regression suite (`run_all.py`)
│   └── validation/                   # End-to-end integration, stress, and benchmark suites
│       ├── test_approval_workflow_integration.py
│       ├── test_end_to_end_integration.py
│       ├── test_performance_benchmarks.py
│       └── test_stress_suite.py
├── tests/                            # Pytest Test Suite
│   ├── integration/                  # Integration test suite (`test_blocking_approval_dialog.py`)
│   └── unit/                         # Unit tests (400+ unit test files)
├── .env.example                      # Settings placeholders template
├── .gitignore                        # Git exclusion rules
├── LICENSE                           # MIT License
├── main.py                           # Primary application entrypoint
├── pyproject.toml                    # Pytest/Ruff build configuration
└── requirements.txt                  # System dependency specifications
```

---

## Package Responsibilities Summary

- **`app/agent/`**: Request routing (`ExecutionRouter`), action loop execution (`AgentRunner`), conversation context budget policy (`ConversationContextPolicy`), and gateway orchestrator (`AgentController`).
- **`app/ai/`**: LLM provider contracts (`BaseLLMProvider`), multi-provider client manager (`LLMManager`), response chunking parser (`ResponseParser`), and priority queue scheduler (`InferenceScheduler`).
- **`app/approval/`**: Synchronized blocking action approval runtime (`ApprovalManager`), SQLite pending actions repository (`SQLiteApprovalRepository`), and CLI terminal approval UI (`prompt_user_approval`).
- **`app/conversation/`**: Persistent SQLite conversation history database repository and session manager.
- **`app/memory/`**: Persistent multi-type memory engine, hybrid lexical retriever, evidence validator, and background extraction coordinator.
- **`app/planning/`**: Multi-step TaskPlan formulation engine, step validator, and sequential TaskExecutor.
- **`app/services/`**: Domain services for root-bounded filesystem operations, Ctypes Windows desktop automation, and application discovery.
- **`app/tools/`**: Catalog of 23 built-in system tools, ToolExecutor worker pool, permissions, and dynamic ToolFilter schema injector.
- **`app/ui/`**: Professional PySide6 desktop GUI, QThread workers, approval cards, system tray launcher, and dark theme.
- **`app/voice/`**: Offline speech recognition (`faster-whisper`), VAD, speech synthesis (`pyttsx3`), push-to-talk runtime, and air-gapped approval safety guard.
- **`app/core/`**: Central application orchestrator, service container, lifecycle state machine, bootstrap verifier, and Loguru logging wrapper.
