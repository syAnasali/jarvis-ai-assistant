"""Unit tests for ResponseParser tool-call detection and parsing."""

import pytest
from typing import Any
from app.ai.parser import ResponseParser
from app.agent.models import ToolCall


# Simple mock classes mimicking SDK ChatResponse message objects
class FakeFunction:
    def __init__(self, name: str, arguments: Any) -> None:
        self.name = name
        self.arguments = arguments


class FakeToolCall:
    def __init__(self, function: FakeFunction) -> None:
        self.function = function


class FakeMessage:
    def __init__(self, content: str, tool_calls: list) -> None:
        self.content = content
        self.tool_calls = tool_calls


class FakeChatResponse:
    def __init__(self, message: FakeMessage) -> None:
        self.message = message


def test_dict_tool_call_detection_and_parsing():
    """Verifies that ResponseParser detects and parses tool calls in dictionary responses."""
    parser = ResponseParser()

    # Dictionary response with a valid tool call
    raw_dict = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "get_current_time",
                        "arguments": {}
                    }
                }
            ]
        }
    }

    assert parser.has_tool_calls(raw_dict) is True
    calls = parser.parse_tool_calls(raw_dict)
    assert len(calls) == 1
    assert calls[0].tool_name == "get_current_time"
    assert calls[0].arguments == {}


def test_sdk_object_tool_call_detection_and_parsing():
    """Verifies that ResponseParser detects and parses tool calls in SDK message objects."""
    parser = ResponseParser()

    # SDK object mimicking ChatResponse containing a tool call
    func = FakeFunction(name="get_system_info", arguments=None)
    tc = FakeToolCall(function=func)
    msg = FakeMessage(content="", tool_calls=[tc])
    raw_obj = FakeChatResponse(message=msg)

    assert parser.has_tool_calls(raw_obj) is True
    calls = parser.parse_tool_calls(raw_obj)
    assert len(calls) == 1
    assert calls[0].tool_name == "get_system_info"
    assert calls[0].arguments == {}  # None argument converts to {}


def test_multiple_tool_calls():
    """Verifies parsing multiple tool calls in a single turn."""
    parser = ResponseParser()

    raw_dict = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "tool_one",
                        "arguments": {"x": 1}
                    }
                },
                {
                    "function": {
                        "name": "tool_two",
                        "arguments": {"y": "yes"}
                    }
                }
            ]
        }
    }

    assert parser.has_tool_calls(raw_dict) is True
    calls = parser.parse_tool_calls(raw_dict)
    assert len(calls) == 2
    assert calls[0].tool_name == "tool_one"
    assert calls[0].arguments == {"x": 1}
    assert calls[1].tool_name == "tool_two"
    assert calls[1].arguments == {"y": "yes"}


def test_malformed_tool_calls_ignored_safely():
    """Verifies that malformed tool call structures (missing name) are ignored without crashing."""
    parser = ResponseParser()

    # Dictionary tool call missing name in function details
    raw_dict = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        # No name key
                        "arguments": {"x": 1}
                    }
                },
                {
                    "function": {
                        "name": "valid_tool",
                        "arguments": None
                    }
                }
            ]
        }
    }

    assert parser.has_tool_calls(raw_dict) is True
    calls = parser.parse_tool_calls(raw_dict)
    assert len(calls) == 1
    assert calls[0].tool_name == "valid_tool"
    assert calls[0].arguments == {}
