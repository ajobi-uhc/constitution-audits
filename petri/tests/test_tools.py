"""
Unit tests for auditor tool utilities.

Tests the validation functions and simple utilities used by the auditor agent tools.
Complex tool behavior that requires the full AuditStore is tested via integration
tests in test_auditor_agent.py.
"""

import pytest

from inspect_ai.model import (
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageUser,
)
from inspect_ai.tool import ToolCall

from petri.tools.tools import (
    validate_tool_call_result,
    can_send_user_message,
    end_conversation,
)
from petri.tools.util import parse_function_code


def test_parse_function_code_builds_schema_without_execution():
    """Synthetic tool definitions become schemas without running their bodies."""
    tool_def = parse_function_code(
        '''
        def search(query: str, limit: int = 10, domains: list[str] | None = None) -> str:
            """Search an index for matching documents."""
            raise AssertionError("model-supplied bodies must never execute")
        '''
    )

    assert tool_def.name == "search"
    assert tool_def.parameters.required == ["query"]
    assert tool_def.parameters.properties["query"].type == "string"
    assert tool_def.parameters.properties["limit"].default == 10
    assert tool_def.parameters.properties["domains"].anyOf is not None


def test_parse_function_code_supports_bare_container_annotations():
    """Historical tool definitions use containers without element types."""
    tool_def = parse_function_code(
        '''
        def submit(tags: list = None, metadata: dict = None) -> dict:
            """Submit a record."""
            ...
        '''
    )

    assert tool_def.parameters.properties["tags"].type == "array"
    assert tool_def.parameters.properties["metadata"].type == "object"


def test_parse_function_code_rejects_decorators_without_running_them(capsys):
    """Decorators cannot provide a definition-time code execution path."""
    with pytest.raises(ValueError, match="Decorators are not allowed"):
        parse_function_code(
            '''
            @print("UNSAFE_DECORATOR_EXECUTED")
            def search(query: str) -> str:
                """Search an index."""
                ...
            '''
        )

    assert "UNSAFE_DECORATOR_EXECUTED" not in capsys.readouterr().out


def test_parse_function_code_rejects_expression_annotations_without_execution(capsys):
    """Annotations cannot provide a definition-time code execution path."""
    with pytest.raises(ValueError, match="Unsupported type annotation"):
        parse_function_code(
            '''
            def search(query: print("UNSAFE_ANNOTATION_EXECUTED")) -> str:
                """Search an index."""
                ...
            '''
        )

    assert "UNSAFE_ANNOTATION_EXECUTED" not in capsys.readouterr().out


# =============================================================================
# END CONVERSATION
# =============================================================================


@pytest.mark.asyncio
async def test_end_conversation():
    """Test ending a conversation."""
    tool_func = end_conversation()
    result = await tool_func()
    assert "The conversation is over" in result


# =============================================================================
# VALIDATION UTILITIES
# =============================================================================


def test_can_send_user_message_no_pending():
    """Test can_send_user_message with no pending tool calls."""
    messages = [
        ChatMessageSystem(content="System"),
        ChatMessageUser(content="Hello"),
        ChatMessageAssistant(content="Hi")
    ]
    assert can_send_user_message(messages) is True


def test_can_send_user_message_with_pending():
    """Test can_send_user_message with pending tool calls."""
    messages = [
        ChatMessageSystem(content="System"),
        ChatMessageAssistant(
            content="I'll calculate",
            tool_calls=[ToolCall(id="calc", function="calculator", arguments={})]
        )
    ]
    assert can_send_user_message(messages) is False


def test_can_send_user_message_after_tool_result():
    """Test can_send_user_message after tool result is added."""
    from inspect_ai.model import ChatMessageTool
    
    messages = [
        ChatMessageSystem(content="System"),
        ChatMessageUser(content="Calculate"),
        ChatMessageAssistant(
            content="I'll calculate",
            tool_calls=[ToolCall(id="calc", function="calculator", arguments={})]
        ),
        ChatMessageTool(content="42", tool_call_id="calc")
    ]
    assert can_send_user_message(messages) is True


def test_validate_tool_call_result_success():
    """Test validate_tool_call_result with valid tool call."""
    messages = [
        ChatMessageSystem(content="System"),
        ChatMessageAssistant(
            content="Calculating",
            tool_calls=[ToolCall(id="calc_1", function="calculator", arguments={})]
        )
    ]
    result = validate_tool_call_result(messages, "calc_1")
    assert result is None  # No error


def test_validate_tool_call_result_no_pending():
    """Test validate_tool_call_result with no pending calls."""
    messages = [ChatMessageSystem(content="System")]
    result = validate_tool_call_result(messages, "calc_1")
    assert "no pending tool calls" in result


def test_validate_tool_call_result_wrong_id():
    """Test validate_tool_call_result with wrong tool call ID."""
    messages = [
        ChatMessageSystem(content="System"),
        ChatMessageAssistant(
            content="Calculating",
            tool_calls=[ToolCall(id="calc_1", function="calculator", arguments={})]
        )
    ]
    result = validate_tool_call_result(messages, "wrong_id")
    assert result is not None  # Should return an error


def test_validate_multiple_pending_tool_calls():
    """Test validate_tool_call_result with multiple pending calls."""
    messages = [
        ChatMessageSystem(content="System"),
        ChatMessageAssistant(
            content="Calculating",
            tool_calls=[
                ToolCall(id="calc_1", function="calculator", arguments={}),
                ToolCall(id="calc_2", function="search", arguments={})
            ]
        )
    ]
    # Both IDs should be valid
    assert validate_tool_call_result(messages, "calc_1") is None
    assert validate_tool_call_result(messages, "calc_2") is None
    # Random ID should fail
    assert validate_tool_call_result(messages, "calc_3") is not None


def test_empty_message_list():
    """Test validation with empty message list."""
    messages = []
    assert can_send_user_message(messages) is True
    result = validate_tool_call_result(messages, "any_id")
    assert "no pending tool calls" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
