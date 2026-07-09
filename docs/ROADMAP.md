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

## Phase 7: Voice System
- **Goal**: Implement text-to-speech (TTS) and speech-to-text (STT) capabilities.
- **Deliverables**: Voice activation listener, audio capture pipeline, and speech synthesizers.
- **Expected Outcome**: The assistant can process raw voice commands and answer the user aloud.

## Phase 8: Desktop Interface
- **Goal**: Construct the desktop user interface.
- **Deliverables**: Main UI window, settings dialog, and notification manager.
- **Expected Outcome**: A functional UI allowing text chatting, system configuration, and status monitoring.

## Phase 9: Advanced Features
- **Goal**: Implement context-rich, long-term memory retrieval and advanced agent reasoning.
- **Deliverables**: Vector database wrappers, semantic memories, and multi-step task planning.
- **Expected Outcome**: The assistant can retrieve relevant history based on context and complete complex objectives.

## Phase 10: Testing
- **Goal**: Build complete test suites verifying all subsystems.
- **Deliverables**: Unit tests, integration tests, mock environments, and automated CI pipelines.
- **Expected Outcome**: High confidence in code changes and regression protection.

## Phase 11: Packaging
- **Goal**: Create production installers and executables.
- **Deliverables**: Packaging scripts, application icons, and installer executable bundle.
- **Expected Outcome**: Single-click installation package ready for end-user deployment.

## Phase 12: Documentation
- **Goal**: Finalize user and developer manuals.
- **Deliverables**: User manual, developer contribution guides, and complete API references.
- **Expected Outcome**: Comprehensive guides facilitating system usage, contribution, and maintenance.
