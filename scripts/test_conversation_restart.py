"""Diagnostic script verifying conversation persistence and cross-restart continuity using a simulated grounded LLM."""

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


def run_restart_diagnostic():
    print("==========================================================")
    print("RUNNING CROSS-RESTART CONVERSATION DIAGNOSTIC")
    print("==========================================================")

    bootstrap = Bootstrap()
    bootstrap.setup()

    temp_db_path = Path("data/test_conversation_restart.db")
    if temp_db_path.exists():
        os.remove(temp_db_path)

    # --- PHASE 1: Create conversation, send messages, persist ---
    print("PHASE 1: Initiating pipeline and persisting dialog...")

    repo_p1 = SQLiteConversationRepository(database_path=temp_db_path)
    manager_p1 = ConversationManager(repository=repo_p1)
    session_p1 = manager_p1.create_session(title="Restart test")
    session_id = session_p1.session_id

    conversation_p1 = Conversation()
    context_manager_p1 = ContextManager()

    llm_manager = LLMManager()
    provider = FakeContinuityProvider()
    llm_manager.register_provider("fake_continuity", provider)
    llm_manager.load_provider("fake_continuity")

    controller_p1 = AgentController(
        conversation=conversation_p1,
        context_manager=context_manager_p1,
        llm_manager=llm_manager,
        conversation_manager=manager_p1,
        context_policy=ContextWindowPolicy()
    )
    controller_p1.active_session_id = session_id

    # Send first message
    print("Sending message 1...")
    req1 = AgentRequest("r1", "My API is returning a Prisma connection timeout.", "terminal")
    controller_p1.process_request(req1)

    # Send second message
    print("Sending message 2...")
    req2 = AgentRequest("r2", "I am debugging the database connection.", "terminal")
    controller_p1.process_request(req2)

    # Destroy pipeline objects
    print("Destroying Phase 1 pipeline objects...")
    del repo_p1, manager_p1, conversation_p1, context_manager_p1, controller_p1

    # --- PHASE 2: Reconstruct pipeline, load session, hydrate ---
    print("\nPHASE 2: Restoring conversation from database...")

    repo_p2 = SQLiteConversationRepository(database_path=temp_db_path)
    manager_p2 = ConversationManager(repository=repo_p2)
    session_p2 = manager_p2.load_session(session_id)

    conversation_p2 = Conversation()
    context_manager_p2 = ContextManager()

    # Hydrate conversation from history
    messages_p2 = manager_p2.get_messages(session_id)
    conversation_p2.load_history(messages_p2)

    controller_p2 = AgentController(
        conversation=conversation_p2,
        context_manager=context_manager_p2,
        llm_manager=llm_manager,
        conversation_manager=manager_p2,
        context_policy=ContextWindowPolicy()
    )
    controller_p2.active_session_id = session_id

    # Display restored messages
    print("\nRestored Conversation Messages:")
    for msg in conversation_p2.get_history():
        print(f"  [{msg.role.value.upper()}] {msg.content}")

    # Ask the continuity question to verify it is grounded in restored conversation
    print("\nAsking continuity question to verify grounding...")
    req3 = AgentRequest("r3", "What issue was I debugging?", "terminal")
    response_p2 = controller_p2.process_request(req3)
    print(f"  [ASSISTANT RESPONSE] {response_p2.text}")

    # Verify semantic grounding
    continuity_grounded = "prisma" in response_p2.text.lower() or "connection" in response_p2.text.lower() or "database" in response_p2.text.lower()

    # Check assertions
    session_persisted = session_p2 is not None
    messages_restored = len(messages_p2) >= 4  # 2 user queries + 2 assistant responses
    order_preserved = messages_p2[0].content == "My API is returning a Prisma connection timeout." and messages_p2[2].content == "I am debugging the database connection."
    conversation_hydrated = len(conversation_p2.get_history()) >= 4

    # Clean up temp database
    if temp_db_path.exists():
        os.remove(temp_db_path)

    print("\n----------------------------------------------------------")
    print("Cross-Restart Conversation Diagnostic:")
    print(f"Session persisted:            {'PASS' if session_persisted else 'FAIL'}")
    print(f"Messages restored:            {'PASS' if messages_restored else 'FAIL'}")
    print(f"Order preserved:              {'PASS' if order_preserved else 'FAIL'}")
    print(f"Conversation hydrated:        {'PASS' if conversation_hydrated else 'FAIL'}")
    print(f"Continuity response grounded: {'PASS' if continuity_grounded else 'FAIL'}")
    print("==========================================================")


if __name__ == "__main__":
    run_restart_diagnostic()
