# Roadmap

This document outlines the multi-phase roadmap for developing the Jarvis AI Assistant.

## Phase 1: Repository Foundation
- **Goal**: Establish the development workspace, directory hierarchy, and initial configuration.
- **Deliverables**: Directory structure, basic configuration files, environment configuration structure, and project configuration layouts.
- **Expected Outcome**: A clean workspace ready for developer collaboration and coding.

## Phase 2: Core Infrastructure
- **Goal**: Build logging subsystems, global configuration management, and system-wide utilities.
- **Deliverables**: Configuration manager, standard logging formatter, and basic path resolution tools.
- **Expected Outcome**: Developers have standard tools to load configurations and log system behaviors securely.

## Phase 3: LLM Integration
- **Goal**: Interface with local and remote Large Language Models (LLMs).
- **Deliverables**: LLM client wrappers, connection error handlers, and token counters.
- **Expected Outcome**: Ability to programmatically send prompts and receive text outputs from LLMs.

## Phase 4: Agent Loop
- **Goal**: Establish the central orchestration framework and state machine.
- **Deliverables**: Main execution loop, state management, and interaction lifecycle hooks.
- **Expected Outcome**: An autonomous execution cycle that continuously processes incoming inputs and determines next actions.

## Phase 5: Tool Calling [Complete]
- **Goal**: Implement a safe and extensible tool registration and execution framework, and establish a secure local capability foundation.
- **Deliverables**: ToolRegistry, ToolExecutor with permission checks, GetDiskUsageTool, ListRunningProcessesTool, FindRunningProcessTool, ListInstalledApplicationsTool, FindInstalledApplicationTool, ListDirectoryTool, and ReadTextFileTool.
- **Expected Outcome**: The agent can inspect local machine state (disk space, processes, Windows registry-installed programs, and non-recursive directory lists/text files) safely and deterministically, using the ToolExecutor security boundary, with full regression tests and diagnostics.

## Phase 6: Memory Engine [Complete]
- **Goal**: Set up local database storage, retrieval, context injection, and write pipeline for persistence.
- **Deliverables**: SQLite schema setup, MemoryRepository, SQLiteMemoryRepository, MemoryManager, LexicalMemoryRetriever, MemoryContextBuilder, LLMMemoryExtractor, MemoryExtractionParser, MemoryWriteService, and SecretGuard complete.
- **Expected Outcome**: Durable long-term memory system is integrated into the agent loop. Facts and preferences are automatically extracted from user input, validation and security filters are applied, exact/near-duplicates are resolved, and contextually relevant memories are retrieved and injected into the model's system prompt dynamically. State and memories persist across restarts.

## Phase 7: Voice System [Complete]
- **Goal**: Implement text-to-speech (TTS) and speech-to-text (STT) capabilities.
- **Deliverables**: sounddevice-based `AudioCapture` backend, numpy energy-based `VoiceActivityDetector`, local `FasterWhisperSTTProvider` with dynamic CPU fallback, local offline `PyTTSx3TTSProvider` SAPI5 backend, plain-text speech normalization, `VoiceManager` subsystem coordinator, and push-to-talk stateful `VoiceRuntime` loop with strict confirmation approval safety barriers.
- **Expected Outcome**: The assistant can process raw voice commands and speak responses aloud offline, maintaining security boundaries and terminal loop compatibility.

## Phase 8: Controlled Desktop Interaction Runtime [Complete]
- **Goal**: Construct a policy-controlled, secure Windows desktop automation runtime.
- **Deliverables**: `DesktopService`, `DesktopPolicy` with strict key/hotkey allowlists, `WindowsDesktopBackend` using native `ctypes` Win32 APIs, `DesktopResolver` for candidate mapping, stable runtime-local window ID mapping, foreground-target focus verification guards, and 7 desktop tools (`get_active_window`, `list_visible_windows`, `focus_window`, `type_text`, `press_key`, `press_hotkey`, `click_screen`).
- **Expected Outcome**: The assistant can safely inspect and automate UI actions on Windows. All mutations are protected by the `CONFIRMATION` permission level, and a foreground focus change guard automatically aborts execution if the active window switches between approval and execution. Includes full E2E planned sequential diagnostics and unit test suite coverage.

## Phase 9: Professional Desktop UI + System Tray [Complete]
- **Goal**: Implement a production-quality, responsive desktop GUI and system tray adapter.
- **Deliverables**: PySide6 dark mode theme, system tray menu controls, non-blocking asynchronous `AgentWorker` and `VoiceWorker` QThreads, dynamic state-driven voice indicators, embedded `ApprovalCardWidget` for pending approvals, Markdown chat rendering with copyable code blocks, settings dialog editor, and E2E GUI thread diagnostics.
- **Expected Outcome**: Users can interact with Jarvis through a modern desktop window or minimize it to the system tray, while preserving terminal compatibility and approval database guarantees.

## Phase 10: Advanced Features
- **Goal**: Implement context-rich, long-term memory retrieval and advanced agent reasoning.
- **Deliverables**: Vector database wrappers, semantic memories, and multi-step task planning.
- **Expected Outcome**: The assistant can retrieve relevant history based on context and complete complex objectives.

## Phase 11: Testing
- **Goal**: Build complete test suites verifying all subsystems.
- **Deliverables**: Unit tests, integration tests, mock environments, and automated CI pipelines.
- **Expected Outcome**: High confidence in code changes and regression protection.

## Phase 12: Packaging
- **Goal**: Create production installers and executables.
- **Deliverables**: Packaging scripts, application icons, and installer executable bundle.
- **Expected Outcome**: Single-click installation package ready for end-user deployment.

## Phase 13: Documentation
- **Goal**: Finalize user and developer manuals.
- **Deliverables**: User manual, developer contribution guides, and complete API references.
- **Expected Outcome**: Comprehensive guides facilitating system usage, contribution, and maintenance.
