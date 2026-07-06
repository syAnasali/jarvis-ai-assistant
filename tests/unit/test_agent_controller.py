"""Unit tests for AgentController memory integration."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.agent.controller import AgentController
from app.agent.conversation import Conversation
from app.agent.context import ContextManager
from app.agent.models import AgentRequest, AgentResponse
from app.agent.messages import MessageRole
from app.ai.manager import LLMManager
from app.agent.runner import AgentRunner, AgentRunResult
from app.agent.metrics import AgentExecutionMetrics
from app.memory.interfaces import MemoryRetriever
from app.memory.context import MemoryContextBuilder
from app.memory.models import Memory, MemoryType, MemorySource, MemoryMatch, MemoryRetrievalResult
from app.memory.coordinator import MemoryWriteCoordinator


def test_controller_memory_retrieval_and_injection():
    """Verify memory retrieval is called, context built, injected into runner, and not stored in Conversation."""
    # Setup mocks
    mock_llm_manager = MagicMock(spec=LLMManager)
    
    mock_retriever = MagicMock(spec=MemoryRetriever)
    mem = Memory("m1", "Persistent fact", MemoryType.FACT, datetime.now(timezone.utc), datetime.now(timezone.utc), 1.0, MemorySource.MANUAL, {})
    match = MemoryMatch(mem, 1.0, 1.0, 1.0)
    mock_retriever.retrieve.return_value = MemoryRetrievalResult(
        query="User query",
        matches=(match,),
        total_candidates=1,
        selected_count=1
    )
    
    mock_context_builder = MagicMock(spec=MemoryContextBuilder)
    mock_context_builder.build.return_value = "[RELEVANT LONG-TERM MEMORY]\n- Persistent fact"
    
    mock_runner = MagicMock(spec=AgentRunner)
    exec_metrics = AgentExecutionMetrics(100.0, 1, 1, 0)
    mock_runner.run.return_value = AgentRunResult("Final response", exec_metrics)
    
    conversation = Conversation()
    context_manager = ContextManager()
    
    controller = AgentController(
        conversation=conversation,
        context_manager=context_manager,
        llm_manager=mock_llm_manager,
        agent_runner=mock_runner,
        retriever=mock_retriever,
        context_builder=mock_context_builder
    )
    
    request = AgentRequest("req_1", "User query", "terminal")
    response = controller.process_request(request)
    
    # 1. Verify retrieval is called with request text
    mock_retriever.retrieve.assert_called_once_with("User query")
    
    # 2. Verify context builder is called with matches list
    mock_context_builder.build.assert_called_once_with([match])
    
    # 3. Verify memory context is passed into runner execution
    mock_runner.run.assert_called_once()
    args, kwargs = mock_runner.run.call_args
    assert kwargs.get("memory_context") == "[RELEVANT LONG-TERM MEMORY]\n- Persistent fact"
    
    # 4. Verify that the memory context is NOT persisted into Conversation
    history = conversation.get_history()
    # We should only have the USER request message and ASSISTANT response message
    assert len(history) == 2
    assert history[0].role == MessageRole.USER
    assert history[0].content == "User query"
    assert history[1].role == MessageRole.ASSISTANT
    assert history[1].content == "Final response"
    
    # No system/memory messages should be stored in conversation
    for msg in history:
        assert "[RELEVANT LONG-TERM MEMORY]" not in msg.content


def test_controller_empty_retrieval_preserves_normal_flow():
    """Verify that when memory retrieval is empty, normal runner execution flow is preserved."""
    mock_llm_manager = MagicMock(spec=LLMManager)
    
    mock_retriever = MagicMock(spec=MemoryRetriever)
    mock_retriever.retrieve.return_value = MemoryRetrievalResult(
        query="User query",
        matches=(),
        total_candidates=0,
        selected_count=0
    )
    
    mock_context_builder = MagicMock(spec=MemoryContextBuilder)
    mock_context_builder.build.return_value = ""
    
    mock_runner = MagicMock(spec=AgentRunner)
    exec_metrics = AgentExecutionMetrics(100.0, 1, 1, 0)
    mock_runner.run.return_value = AgentRunResult("Final response", exec_metrics)
    
    conversation = Conversation()
    context_manager = ContextManager()
    
    controller = AgentController(
        conversation=conversation,
        context_manager=context_manager,
        llm_manager=mock_llm_manager,
        agent_runner=mock_runner,
        retriever=mock_retriever,
        context_builder=mock_context_builder
    )
    
    request = AgentRequest("req_1", "User query", "terminal")
    response = controller.process_request(request)
    
    # Verify memory context is empty string in runner call
    mock_runner.run.assert_called_once()
    args, kwargs = mock_runner.run.call_args
    assert kwargs.get("memory_context") == ""
    assert response.text == "Final response"


def test_controller_retrieval_failure_propagates():
    """Verify that retrieval failures are propagated and not silently swallowed."""
    mock_llm_manager = MagicMock(spec=LLMManager)
    
    mock_retriever = MagicMock(spec=MemoryRetriever)
    mock_retriever.retrieve.side_effect = RuntimeError("Database locked")
    
    mock_context_builder = MagicMock(spec=MemoryContextBuilder)
    mock_runner = MagicMock(spec=AgentRunner)
    
    conversation = Conversation()
    context_manager = ContextManager()
    
    controller = AgentController(
        conversation=conversation,
        context_manager=context_manager,
        llm_manager=mock_llm_manager,
        agent_runner=mock_runner,
        retriever=mock_retriever,
        context_builder=mock_context_builder
    )
    
    request = AgentRequest("req_1", "User query", "terminal")
    
    with pytest.raises(RuntimeError, match="Database locked"):
        controller.process_request(request)


def test_controller_memory_coordinator_schedule_success():
    """Verify that AgentController schedules request.text exactly once on successful response."""
    mock_llm_manager = MagicMock(spec=LLMManager)
    mock_retriever = MagicMock(spec=MemoryRetriever)
    mock_retriever.retrieve.return_value = MemoryRetrievalResult("Q", (), 0, 0)
    mock_context_builder = MagicMock(spec=MemoryContextBuilder)
    mock_context_builder.build.return_value = ""

    mock_runner = MagicMock(spec=AgentRunner)
    exec_metrics = AgentExecutionMetrics(100.0, 1, 1, 0)
    mock_runner.run.return_value = AgentRunResult("Final response", exec_metrics)

    mock_coordinator = MagicMock(spec=MemoryWriteCoordinator)
    mock_coordinator.submit.return_value = True

    conversation = Conversation()
    context_manager = ContextManager()

    controller = AgentController(
        conversation=conversation,
        context_manager=context_manager,
        llm_manager=mock_llm_manager,
        agent_runner=mock_runner,
        retriever=mock_retriever,
        context_builder=mock_context_builder,
        coordinator=mock_coordinator
    )

    request = AgentRequest("req_1", "User query", "terminal")
    response = controller.process_request(request)

    assert response.text == "Final response"
    
    # 1. Verify coordinator.submit is called with exactly request.text
    mock_coordinator.submit.assert_called_once_with("User query")


def test_controller_memory_coordinator_scheduling_failure_isolated():
    """Verify that if the coordinator fails to submit or raises, the response is still returned."""
    mock_llm_manager = MagicMock(spec=LLMManager)
    mock_retriever = MagicMock(spec=MemoryRetriever)
    mock_retriever.retrieve.return_value = MemoryRetrievalResult("Q", (), 0, 0)
    mock_context_builder = MagicMock(spec=MemoryContextBuilder)
    mock_context_builder.build.return_value = ""

    mock_runner = MagicMock(spec=AgentRunner)
    exec_metrics = AgentExecutionMetrics(100.0, 1, 1, 0)
    mock_runner.run.return_value = AgentRunResult("Final response", exec_metrics)

    mock_coordinator = MagicMock(spec=MemoryWriteCoordinator)
    mock_coordinator.submit.side_effect = RuntimeError("Executor saturated")

    conversation = Conversation()
    context_manager = ContextManager()

    controller = AgentController(
        conversation=conversation,
        context_manager=context_manager,
        llm_manager=mock_llm_manager,
        agent_runner=mock_runner,
        retriever=mock_retriever,
        context_builder=mock_context_builder,
        coordinator=mock_coordinator
    )

    request = AgentRequest("req_1", "User query", "terminal")
    response = controller.process_request(request)

    assert response.text == "Final response"
    mock_coordinator.submit.assert_called_once_with("User query")


def test_controller_memory_coordinator_streaming_schedule():
    """Verify that process_request_stream schedules memory only after successful stream completion."""
    mock_llm_manager = MagicMock(spec=LLMManager)
    mock_retriever = MagicMock(spec=MemoryRetriever)
    mock_retriever.retrieve.return_value = MemoryRetrievalResult("Q", (), 0, 0)
    mock_context_builder = MagicMock(spec=MemoryContextBuilder)
    mock_context_builder.build.return_value = ""

    mock_runner = MagicMock(spec=AgentRunner)
    exec_metrics = AgentExecutionMetrics(100.0, 1, 1, 0)

    class MockIterator:
        def __init__(self):
            self.chunks = ["Chunk 1", "Chunk 2"]
            self.index = 0
        def __iter__(self):
            return self
        def __next__(self):
            if self.index < len(self.chunks):
                val = self.chunks[self.index]
                self.index += 1
                return val
            raise StopIteration(exec_metrics)

    mock_runner.run_stream.return_value = MockIterator()

    mock_coordinator = MagicMock(spec=MemoryWriteCoordinator)

    conversation = Conversation()
    context_manager = ContextManager()

    controller = AgentController(
        conversation=conversation,
        context_manager=context_manager,
        llm_manager=mock_llm_manager,
        agent_runner=mock_runner,
        retriever=mock_retriever,
        context_builder=mock_context_builder,
        coordinator=mock_coordinator
    )

    request = AgentRequest("req_1", "User query", "terminal")
    stream = controller.process_request_stream(request)

    # Before consuming the stream, coordinator should NOT be called
    mock_coordinator.submit.assert_not_called()

    # Consume the stream
    chunks = list(stream)
    assert chunks == ["Chunk 1", "Chunk 2"]

    # After consumption finishes, coordinator should be called exactly once
    mock_coordinator.submit.assert_called_once_with("User query")


def test_controller_conversation_persistence_integration():
    """Verify that AgentController persists messages before in-memory addition and propagates errors."""
    from app.conversation.manager import ConversationManager
    from app.conversation.policy import ContextWindowPolicy

    mock_llm_manager = MagicMock(spec=LLMManager)
    mock_runner = MagicMock(spec=AgentRunner)
    exec_metrics = AgentExecutionMetrics(100.0, 1, 1, 0)
    mock_runner.run.return_value = AgentRunResult("Assistant reply", exec_metrics)

    conversation = Conversation()
    context_manager = ContextManager()

    mock_conv_manager = MagicMock(spec=ConversationManager)
    mock_policy = MagicMock(spec=ContextWindowPolicy)
    mock_policy.select_history.side_effect = lambda msgs: msgs

    controller = AgentController(
        conversation=conversation,
        context_manager=context_manager,
        llm_manager=mock_llm_manager,
        agent_runner=mock_runner,
        conversation_manager=mock_conv_manager,
        context_policy=mock_policy
    )
    controller.active_session_id = "session_xyz"

    # Callbacks to verify persistence occurs BEFORE in-memory add
    order = []

    def mock_add_message(session_id, message):
        assert session_id == "session_xyz"
        order.append(f"persist_{message.role.value}")
        # At this point, the message should NOT be in the conversation log yet
        # (meaning the last message in in-memory history isn't this one, or the list length doesn't include it yet)
        if message.role == MessageRole.USER:
            assert len(conversation.get_history()) == 0
        elif message.role == MessageRole.ASSISTANT:
            # Only USER is in history
            assert len(conversation.get_history()) == 1

    mock_conv_manager.add_message.side_effect = mock_add_message

    request = AgentRequest("req_1", "Hello there", "terminal")
    response = controller.process_request(request)

    assert response.text == "Assistant reply"
    assert order == ["persist_user", "persist_assistant"]
    assert len(conversation.get_history()) == 2
    assert conversation.get_history()[0].content == "Hello there"
    assert conversation.get_history()[1].content == "Assistant reply"


