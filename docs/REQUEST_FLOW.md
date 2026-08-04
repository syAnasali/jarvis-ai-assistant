# Request Processing Flow

This document details the step-by-step lifecycle of user requests in the Jarvis AI Assistant across all processing modes (Direct Chat, Tool Execution with Blocking Action Approval, Multi-step Task Planning, Memory Retrieval, Voice Input, and Desktop GUI).

---

## 1. Direct Chat Request Flow

```mermaid
sequenceDiagram
    participant User
    participant App as Application / CLI
    participant Controller as AgentController
    participant Router as ExecutionRouter
    participant DB as SQLite Conversation DB
    participant Memory as MemoryRetriever
    participant LLM as LLMManager / Ollama
    
    User->>App: Input text ("Hello Jarvis")
    App->>Controller: process_request_stream(request)
    Controller->>DB: Add user Message
    Controller->>Memory: retrieve(request.text)
    Memory-->>Controller: MemoryContext ([RELEVANT LONG-TERM MEMORY])
    Controller->>Router: classify_intent(request)
    Router-->>Controller: Intent (CHAT, DIRECT)
    Controller->>LLM: run_stream(formatted_messages, memory_context)
    LLM-->>App: yield token chunks ("Jarvis > Hello!...")
    Controller->>DB: Add assistant Message
    Controller->>Memory: schedule_background_extraction(request, response)
```

---

## 2. Tool Execution & Synchronized Blocking Action Approval Flow

When a request requires executing a tool marked with `ToolPermission.CONFIRMATION` (e.g. `delete_path`, `write_text_file`, `launch_application`, `focus_window`, `type_text`):

```mermaid
sequenceDiagram
    participant User
    participant CLI as Terminal CLI UI
    participant App as Application
    participant Controller as AgentController
    participant Runner as AgentRunner
    participant ToolExec as ToolExecutor
    participant ApprovalMgr as ApprovalManager
    
    User->>CLI: Input ("Delete temp/file.txt")
    CLI->>Controller: process_request_stream(request)
    Controller->>Runner: run_stream()
    Runner->>ToolExec: execute(ToolCall("delete_path"))
    ToolExec->>ApprovalMgr: create_pending_action("delete_path")
    ApprovalMgr-->>ToolExec: action_id = "action_123"
    ToolExec-->>Runner: Execution suspended (confirmation_required=True)
    Runner-->>Controller: Yield message (confirmation_required=True, pending_action_id="action_123")
    Controller->>App: Intercept confirmation_required metadata
    App->>App: Set waiting_for_approval = True
    App->>CLI: prompt_user_approval(tool_name, args)
    Note over CLI: Purge stdin buffer (msvcrt.kbhit)<br/>Block OS thread on native input()
    CLI-->>App: User inputs 'y' (True)
    App->>ApprovalMgr: approve("action_123")
    App->>Controller: process_request_stream(request, approval_action_id="action_123")
    Controller->>Runner: Resume execution
    Runner->>ToolExec: execute(ToolCall, approval_action_id="action_123")
    ToolExec->>ToolExec: Consume approval & run tool
    ToolExec-->>Runner: ToolResult(success=True)
    Runner->>LLM: Final synthesis prompt with Tool output
    LLM-->>CLI: yield token chunks ("File deleted successfully.")
    App->>App: Set waiting_for_approval = False
```

---

## 3. Multi-Step Task Planner Execution Flow

For complex tasks requiring multiple steps (e.g. "Find running process chrome, inspect disk usage, and write summary to log.txt"):

```mermaid
sequenceDiagram
    participant Controller as AgentController
    participant Router as ExecutionRouter
    participant Planner as TaskPlanner
    participant Executor as TaskExecutor
    participant Tools as ToolExecutor
    
    Controller->>Router: classify_intent(request)
    Router-->>Controller: Intent (PLANNED)
    Controller->>Planner: create_plan(request)
    Planner-->>Controller: TaskPlan ([Step 1: TOOL, Step 2: REASONING, Step 3: SYNTHESIS])
    Controller->>Executor: execute(plan)
    loop For Each Plan Step
        alt Step is TOOL
            Executor->>Tools: execute(Step.tool_name, Step.arguments)
            Tools-->>Executor: StepObservation
        else Step is REASONING
            Executor->>Executor: Evaluate intermediate observations
        end
    end
    Executor->>LLM: Synthesize observations into final user response
    Executor-->>Controller: PlanExecutionResult
```

---

## 4. Persistent Memory Retrieval & Background Extraction Flow

1. **Foreground Retrieval Phase**:
   - Before building system prompts, `LexicalMemoryRetriever` queries the SQLite database for stored user facts and preferences matching key tokens in the user request.
   - Matched items are formatted by `MemoryContextBuilder` into a structured prompt section:
     ```markdown
     [RELEVANT LONG-TERM MEMORY]
     - User prefers dark mode.
     - User workspace directory is C:\Projects.
     ```
   - System prompt token budget is preserved.

2. **Background Extraction Phase**:
   - Immediately after the assistant response is delivered to the user, `AgentController` schedules an asynchronous extraction task.
   - `MemoryWriteCoordinator` runs `LLMMemoryExtractor` on a dedicated background worker thread (`InferencePriority.BACKGROUND`).
   - `MemoryEvidenceValidator` verifies that extracted memory candidates match verbatim text evidence from the user prompt.
   - Validated items are saved to the `memories` table in SQLite (`data/jarvis.db`).

---

## 5. Offline Voice Push-to-Talk Interaction Flow

1. **Trigger**: User presses hotkey or spacebar in Voice Mode.
2. **Audio Capture**: `AudioCapture` records microphone input into 16kHz PCM audio frames.
3. **Speech Activity Detection**: `VoiceActivityDetector` isolates voice segments using RMS energy boundaries.
4. **Offline Speech-to-Text**: `FasterWhisperSTTProvider` transcribes audio locally (using GPU CUDA or automatic CPU fallback).
5. **Air-Gapped Safety Check**: If the transcribed command requests a confirmation-level tool (e.g. "delete directory"), execution is suspended to `WAITING_APPROVAL`, speech output announces the required approval, and execution blocks until explicit terminal approval is granted. Spoken commands cannot bypass tool approvals.
6. **Speech Synthesis**: `PyTTSx3TTSProvider` strips markdown formatting and speaks the final assistant response.

---

## 6. Desktop GUI Event & Synchronization Flow

1. **User Action**: User types prompt or selects session in PySide6 `AppWindow`.
2. **Background Execution**: `AgentWorker` background `QThread` receives `AgentRequest` and runs `AgentController.process_request_stream()`.
3. **Signal Emission**:
   - `chunk_received(str)`: Emitted per token chunk to update `ChatWidget` live text view.
   - `approval_requested(action_id, tool_name, reason)`: Emitted when execution is suspended for confirmation, injecting an `ApprovalCardWidget` into the chat pane.
   - `response_completed(Message)`: Emitted when turn finishes, updating sidebar database metrics and history lists.
