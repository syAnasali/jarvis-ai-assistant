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


def test_controller_memory_write_success():
    """Verify write_service is called after assistant response is stored and metrics are updated."""
    mock_llm_manager = MagicMock(spec=LLMManager)
    mock_retriever = MagicMock(spec=MemoryRetriever)
    mock_retriever.retrieve.return_value = MemoryRetrievalResult("Q", (), 0, 0)
    mock_context_builder = MagicMock(spec=MemoryContextBuilder)
    mock_context_builder.build.return_value = ""

    mock_runner = MagicMock(spec=AgentRunner)
    exec_metrics = AgentExecutionMetrics(100.0, 1, 1, 0)
    mock_runner.run.return_value = AgentRunResult("Final response", exec_metrics)

    from app.memory.write_service import MemoryWriteService
    from app.memory.models import MemoryWriteResult
    mock_write_service = MagicMock(spec=MemoryWriteService)
    mock_write = MemoryWriteResult(extracted_count=2, persisted_count=1, duplicate_count=0, rejected_count=1, persisted_memory_ids=("m_1",))
    mock_write_service.write_memories.return_value = mock_write

    conversation = Conversation()
    context_manager = ContextManager()

    controller = AgentController(
        conversation=conversation,
        context_manager=context_manager,
        llm_manager=mock_llm_manager,
        agent_runner=mock_runner,
        retriever=mock_retriever,
        context_builder=mock_context_builder,
        write_service=mock_write_service
    )

    request = AgentRequest("req_1", "User query", "terminal")
    response = controller.process_request(request)

    # 1. Verify write service called with request text
    mock_write_service.write_memories.assert_called_once_with("User query")

    # 2. Verify metrics updated
    metrics = response.metadata.get("execution_metrics")
    assert metrics is not None
    assert metrics.memories_extracted == 2
    assert metrics.memories_persisted == 1


def test_controller_memory_write_failure_isolated():
    """Verify memory write failures are isolated and do not crash the user response flow."""
    mock_llm_manager = MagicMock(spec=LLMManager)
    mock_retriever = MagicMock(spec=MemoryRetriever)
    mock_retriever.retrieve.return_value = MemoryRetrievalResult("Q", (), 0, 0)
    mock_context_builder = MagicMock(spec=MemoryContextBuilder)
    mock_context_builder.build.return_value = ""

    mock_runner = MagicMock(spec=AgentRunner)
    exec_metrics = AgentExecutionMetrics(100.0, 1, 1, 0)
    mock_runner.run.return_value = AgentRunResult("Final response", exec_metrics)

    from app.memory.write_service import MemoryWriteService
    from app.core.exceptions import MemorySystemError
    mock_write_service = MagicMock(spec=MemoryWriteService)
    mock_write_service.write_memories.side_effect = MemorySystemError("Extraction failed")

    conversation = Conversation()
    context_manager = ContextManager()

    controller = AgentController(
        conversation=conversation,
        context_manager=context_manager,
        llm_manager=mock_llm_manager,
        agent_runner=mock_runner,
        retriever=mock_retriever,
        context_builder=mock_context_builder,
        write_service=mock_write_service
    )

    request = AgentRequest("req_1", "User query", "terminal")
    # Should complete successfully and NOT raise MemorySystemError
    response = controller.process_request(request)

    assert response.text == "Final response"
    mock_write_service.write_memories.assert_called_once_with("User query")

