"""Diagnostic script demonstrating persistent conversation integration and context bounds verification using simulated grounded LLM."""

import os
from datetime import datetime, timezone
from pathlib import Path
from app.core.bootstrap import Bootstrap
from app.conversation.repository import SQLiteConversationRepository
from app.conversation.manager import ConversationManager
from app.conversation.policy import ContextWindowPolicy
from app.agent.conversation import Conversation
from app.agent.context import ContextManager
from app.agent.controller import AgentController
from app.ai.manager import LLMManager
from app.ai.interfaces import BaseLLMProvider
from app.ai.models import GenerationResult, GenerationMetrics
from app.agent.models import AgentRequest


class FakeContinuityProvider(BaseLLMProvider):
    """Simulated LLM Provider that outputs answers grounded in the conversation history context."""

    def initialize(self) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def is_available(self) -> bool:
        return True

    def health_check(self) -> dict:
        return {"status": "ok"}

    def generate_stream(self, messages, options=None, tools=None, profile=None):
        yield "chunk"

    def generate(self, messages, options=None, tools=None, profile=None) -> GenerationResult:
        history_text = " ".join([m.get("content", "") for m in messages]).lower()
        last_msg = messages[-1]["content"].lower()

        if "what issue was i debugging" in last_msg or "what issue" in last_msg:
            if "prisma" in history_text:
                reply = "You were debugging a Prisma connection timeout issue."
            else:
                reply = "I don't see any active debugging topic in our history."
        elif "what priority" in last_msg:
            if "foreground" in history_text:
                reply = "You said the scheduler uses foreground priority."
            else:
                reply = "You did not specify a priority."
        else:
            reply = f"Simulated response to: {messages[-1]['content']}"

        metrics = GenerationMetrics(
            provider="fake_continuity",
            model="fake-qwen3",
            total_duration_ms=5.0,
            load_duration_ms=0.0,
            prompt_eval_duration_ms=0.0,
            generation_duration_ms=5.0,
            prompt_tokens=10,
            generated_tokens=10,
            tokens_per_second=2000.0,
            generation_profile=profile.value if profile else "BALANCED",
            metadata={}
        )
        return GenerationResult(raw_response=reply, metrics=metrics)


def run_persistent_conversation_diagnostic():
    print("==========================================================")
    print("RUNNING PERSISTENT CONVERSATION INTEGRATION DIAGNOSTIC")
    print("==========================================================")

    # 1. Setup application config
    bootstrap = Bootstrap()
    bootstrap.setup()

    temp_db_path = Path("data/test_persistent_conversation.db")
    if temp_db_path.exists():
        os.remove(temp_db_path)

    # Reusable LLM Manager
    llm_manager = LLMManager()
    provider = FakeContinuityProvider()
    llm_manager.register_provider("fake_continuity", provider)
    llm_manager.load_provider("fake_continuity")

    # --- PHASE 1: Create session, send initial queries, persist ---
    print("PHASE 1: Constructing pipeline and sending initial context...")
    repo_p1 = SQLiteConversationRepository(database_path=temp_db_path)
    manager_p1 = ConversationManager(repository=repo_p1)
    session_p1 = manager_p1.create_session(title="Persistent Integration Test")
    session_id = session_p1.session_id

    conversation_p1 = Conversation()
    context_manager_p1 = ContextManager()
    policy_p1 = ContextWindowPolicy()

    controller_p1 = AgentController(
        conversation=conversation_p1,
        context_manager=context_manager_p1,
        llm_manager=llm_manager,
        conversation_manager=manager_p1,
        context_policy=policy_p1
    )
    controller_p1.active_session_id = session_id

    # Send first message
    print("Sending message 1...")
    req1 = AgentRequest("r1", "I am working on the Jarvis scheduler.", "terminal")
    controller_p1.process_request(req1)

    # Send second message
    print("Sending message 2...")
    req2 = AgentRequest("r2", "The scheduler uses foreground priority.", "terminal")
    controller_p1.process_request(req2)

    # Capture persisted messages count
    persisted_count_p1 = manager_p1.count_messages(session_id)

    # Destroy Phase 1 objects
    del repo_p1, manager_p1, conversation_p1, context_manager_p1, controller_p1

    # --- PHASE 2: Restore session and ask the continuity question ---
    print("\nPHASE 2: Restoring pipeline with the same session ID...")
    repo_p2 = SQLiteConversationRepository(database_path=temp_db_path)
    manager_p2 = ConversationManager(repository=repo_p2)
    session_p2 = manager_p2.load_session(session_id)

    conversation_p2 = Conversation()
    context_manager_p2 = ContextManager()
    policy_p2 = ContextWindowPolicy()

    # Hydrate history
    restored_msgs = manager_p2.get_messages(session_id)
    conversation_p2.load_history(restored_msgs)

    controller_p2 = AgentController(
        conversation=conversation_p2,
        context_manager=context_manager_p2,
        llm_manager=llm_manager,
        conversation_manager=manager_p2,
        context_policy=policy_p2
    )
    controller_p2.active_session_id = session_id

    # Ask the test question
    print("Asking continuity question...")
    req3 = AgentRequest("r3", "What priority did I say the scheduler uses?", "terminal")
    response_p2 = controller_p2.process_request(req3)
    print(f"  [ASSISTANT RESPONSE] {response_p2.text}")

    # Capture final counts
    persisted_count_final = manager_p2.count_messages(session_id)
    selected_context_count = len(policy_p2.select_history(conversation_p2.get_history()))

    # Semantic answer check
    passed = "foreground" in response_p2.text.lower()

    # Cleanup temp DB
    if temp_db_path.exists():
        os.remove(temp_db_path)

    print("\nResults:")
    print(f"Session ID:                     {session_id}")
    print(f"Persisted message count:        {persisted_count_final}")
    print(f"Restored message count:         {len(restored_msgs)}")
    print(f"Selected context message count: {selected_context_count}")
    print(f"Final continuity response:      {response_p2.text}")

    print("\n----------------------------------------------------------")
    print(f"Persistent Conversation Integration Diagnostic: {'PASS' if passed else 'FAIL'}")
    print("==========================================================")


if __name__ == "__main__":
    run_persistent_conversation_diagnostic()
