"""
Tests for ToolAwareRenderer functionality.

This module tests the tool-aware rendering capabilities including tool call detection,
execution, confirmation, and continuation during streaming responses.
"""

from dataclasses import dataclass
from typing import Any, Dict, List
from unittest.mock import Mock, patch

import pytest

from mochi_coco.rendering.tool_aware_renderer import ToolAwareRenderer
from mochi_coco.tools.config import ToolExecutionPolicy, ToolSettings
from mochi_coco.tools.execution_service import ToolExecutionResult, ToolExecutionService
from mochi_coco.ui.tool_confirmation_ui import ToolConfirmationUI


@dataclass
class MockMessage:
    """Mock message for testing."""

    role: str = "assistant"
    content: str = ""
    thinking: str = ""
    tool_calls: List[Any] = None

    def __post_init__(self):
        if self.tool_calls is None:
            self.tool_calls = []


@dataclass
class MockChatResponse:
    """Mock ChatResponse for testing."""

    message: MockMessage
    done: bool = False
    model: str = "test-model"

    def __post_init__(self):
        if not hasattr(self, "message") or self.message is None:
            self.message = MockMessage()


@dataclass
class MockToolCall:
    """Mock tool call for testing."""

    function: Any

    def __post_init__(self):
        if not hasattr(self.function, "name"):
            self.function = Mock(name="test_tool", arguments={})


class TestToolAwareRenderer:
    """Test cases for ToolAwareRenderer."""

    @pytest.fixture
    def mock_base_renderer(self):
        """Create a mock base renderer."""
        renderer = Mock()
        renderer.show_thinking = False

        def mock_render_streaming_response(iterator):
            # Actually consume the iterator like a real renderer would
            accumulated_content = ""

            for chunk in iterator:
                if chunk.message.content:
                    accumulated_content += chunk.message.content

            # Return a mock response
            return MockChatResponse(MockMessage(content="Base response"), done=True)

        renderer.render_streaming_response.side_effect = mock_render_streaming_response
        return renderer

    @pytest.fixture
    def mock_tool_execution_service(self):
        """Create a mock tool execution service."""
        service = Mock(spec=ToolExecutionService)

        def mock_execute_tool(tool_name, arguments, policy, confirm_callback=None):
            # Actually call the confirmation callback if provided and policy requires it
            if confirm_callback and policy == ToolExecutionPolicy.ALWAYS_CONFIRM:
                confirmed = confirm_callback(tool_name, arguments)
                if not confirmed:
                    return ToolExecutionResult(
                        success=False,
                        result=None,
                        error_message="Tool execution denied by user",
                        tool_name=tool_name,
                    )

            return ToolExecutionResult(
                success=True, result="Tool executed successfully", tool_name=tool_name
            )

        service.execute_tool.side_effect = mock_execute_tool
        return service

    @pytest.fixture
    def mock_confirmation_ui(self):
        """Create a mock confirmation UI."""
        ui = Mock(spec=ToolConfirmationUI)
        ui.confirm_tool_execution.return_value = True
        return ui

    @pytest.fixture
    def tool_aware_renderer(
        self, mock_base_renderer, mock_tool_execution_service, mock_confirmation_ui
    ):
        """Create a ToolAwareRenderer with mocked dependencies."""
        return ToolAwareRenderer(
            mock_base_renderer, mock_tool_execution_service, mock_confirmation_ui
        )

    @pytest.fixture
    def tool_context(self):
        """Create a basic tool context for testing."""
        # Create a proper mock session
        session = Mock()
        session.messages = Mock()
        session.messages.__len__ = Mock(return_value=2)  # Mock len() method
        session.metadata = Mock()
        session.metadata.message_count = 0
        session.metadata.updated_at = ""
        session.save_session = Mock()

        return {
            "tools_enabled": True,
            "tool_settings": ToolSettings(
                tools=["test_tool"], execution_policy=ToolExecutionPolicy.ALWAYS_CONFIRM
            ),
            "session": session,
            "model": "test-model",
            "client": Mock(),
            "available_tools": [Mock(name="test_tool")],
        }

    def test_render_without_tool_context(self, tool_aware_renderer, mock_base_renderer):
        """Test that renderer falls back to base renderer when no tool context."""
        chunks = [MockChatResponse(MockMessage(content="Hello"), done=True)]

        result = tool_aware_renderer.render_streaming_response(iter(chunks))

        mock_base_renderer.render_streaming_response.assert_called_once()
        # Result should be the return value from the mock side_effect
        assert result is not None
        assert result.message.content == "Base response"

    def test_render_with_tools_disabled(self, tool_aware_renderer, mock_base_renderer):
        """Test that renderer falls back to base renderer when tools are disabled."""
        chunks = [MockChatResponse(MockMessage(content="Hello"), done=True)]
        tool_context = {"tools_enabled": False}

        tool_aware_renderer.render_streaming_response(iter(chunks), tool_context)

        mock_base_renderer.render_streaming_response.assert_called_once()

    def test_render_with_incomplete_tool_context(
        self, tool_aware_renderer, mock_base_renderer
    ):
        """Test fallback when tool context is incomplete."""
        chunks = [MockChatResponse(MockMessage(content="Hello"), done=True)]
        incomplete_context = {
            "tools_enabled": True,
            "tool_settings": ToolSettings(),
            # Missing session, model, client
        }

        with patch("mochi_coco.rendering.tool_aware_renderer.logger") as mock_logger:
            tool_aware_renderer.render_streaming_response(
                iter(chunks), incomplete_context
            )

            mock_logger.warning.assert_called_with(
                "Incomplete tool context, falling back to base renderer"
            )
            mock_base_renderer.render_streaming_response.assert_called_once()

    def test_render_regular_content_without_tools(
        self, tool_aware_renderer, tool_context
    ):
        """Test rendering regular content without tool calls."""
        message = MockMessage(content="Hello, how are you?")
        chunks = [MockChatResponse(message, done=True)]

        result = tool_aware_renderer.render_streaming_response(
            iter(chunks), tool_context
        )

        # Content should be handled by base renderer, check that we get a result
        assert result is not None
        # Base renderer was called and consumed the content
        assert tool_aware_renderer.base_renderer.render_streaming_response.called

    def test_render_thinking_blocks(self, tool_aware_renderer, tool_context):
        """Test rendering with thinking blocks when enabled."""
        tool_aware_renderer.base_renderer.show_thinking = True

        message = MockMessage(content="Response", thinking="I need to think...")
        chunks = [MockChatResponse(message, done=True)]

        result = tool_aware_renderer.render_streaming_response(
            iter(chunks), tool_context
        )

        # Thinking blocks are now handled by base renderer through delegation
        assert result is not None
        assert tool_aware_renderer.base_renderer.render_streaming_response.called

    @patch("builtins.print")
    def test_handle_tool_call_success(
        self, mock_print, tool_aware_renderer, tool_context
    ):
        """Test successful tool call handling."""
        # Create mock tool call
        mock_function = Mock()
        mock_function.name = "test_tool"
        mock_function.arguments = {"arg1": "value1"}

        tool_call = Mock()
        tool_call.function = mock_function

        message = MockMessage(content="I'll help you", tool_calls=[tool_call])
        chunks = [MockChatResponse(message, done=False)]

        # Mock session methods
        tool_context["session"].get_messages_for_api.return_value = [
            {"role": "user", "content": "test"}
        ]

        # Mock client to return continuation stream (empty for this test)
        tool_context["client"].chat_stream.return_value = iter([])

        tool_aware_renderer.render_streaming_response(iter(chunks), tool_context)

        # Should print tool processing message
        mock_print.assert_any_call("\n🤖 Processing 1 tool results...\n")

    def test_tool_execution_with_confirmation(self, tool_aware_renderer, tool_context):
        """Test tool execution with user confirmation."""
        # Test the _handle_tool_call method directly to isolate confirmation logic
        mock_function = Mock()
        mock_function.name = "test_tool"
        mock_function.arguments = {"arg1": "value1"}

        tool_call = Mock()
        tool_call.function = mock_function

        # Execute the tool call directly
        result = tool_aware_renderer._handle_tool_call(
            tool_call, tool_context["tool_settings"]
        )

        # Verify confirmation UI was called
        tool_aware_renderer.confirmation_ui.confirm_tool_execution.assert_called_once_with(
            "test_tool", {"arg1": "value1"}
        )

        # Verify tool execution service was called
        tool_aware_renderer.tool_execution_service.execute_tool.assert_called_once()

        # Verify the result is successful (since confirmation was mocked to return True)
        assert result.success is True

    def test_confirmation_callback_direct(self, tool_aware_renderer, tool_context):
        """Test the confirmation callback directly to debug the issue."""
        # Create confirmation callback function like in the actual code
        tool_settings = tool_context["tool_settings"]

        def confirm_callback(name: str, args: Dict) -> bool:
            if tool_settings.execution_policy == ToolExecutionPolicy.NEVER_CONFIRM:
                return True
            elif tool_settings.execution_policy == ToolExecutionPolicy.ALWAYS_CONFIRM:
                return tool_aware_renderer.confirmation_ui.confirm_tool_execution(
                    name, args
                )
            else:
                return tool_aware_renderer.confirmation_ui.confirm_tool_execution(
                    name, args
                )

        # Test the callback directly
        result = confirm_callback("test_tool", {"arg1": "value1"})

        # Should have called confirmation UI
        tool_aware_renderer.confirmation_ui.confirm_tool_execution.assert_called_once_with(
            "test_tool", {"arg1": "value1"}
        )
        # Should return True (mocked to return True)
        assert result is True

    def test_tool_execution_denied(self, tool_aware_renderer, tool_context):
        """Test behavior when tool execution is denied."""
        # Setup confirmation to deny
        tool_aware_renderer.confirmation_ui.confirm_tool_execution.return_value = False

        # Create tool call
        mock_function = Mock()
        mock_function.name = "test_tool"
        mock_function.arguments = {}

        tool_call = Mock()
        tool_call.function = mock_function

        message = MockMessage(tool_calls=[tool_call])
        chunks = [MockChatResponse(message, done=False)]

        # Setup mocks
        tool_context["session"].get_messages_for_api.return_value = []
        tool_context["client"].chat_stream.return_value = iter([])

        with patch("builtins.print"):
            tool_aware_renderer.render_streaming_response(iter(chunks), tool_context)

        # Verify execution was attempted but denied
        tool_aware_renderer.tool_execution_service.execute_tool.assert_called_once()
        call_args = tool_aware_renderer.tool_execution_service.execute_tool.call_args
        assert call_args[0][0] == "test_tool"  # tool_name
        assert call_args[0][1] == {}  # arguments

    def test_never_confirm_policy(self, tool_aware_renderer, tool_context):
        """Test that NEVER_CONFIRM policy skips confirmation."""
        # Set policy to never confirm
        tool_context[
            "tool_settings"
        ].execution_policy = ToolExecutionPolicy.NEVER_CONFIRM

        mock_function = Mock()
        mock_function.name = "test_tool"
        mock_function.arguments = {}

        tool_call = Mock()
        tool_call.function = mock_function

        message = MockMessage(tool_calls=[tool_call])
        chunks = [MockChatResponse(message, done=False)]

        tool_context["session"].get_messages_for_api.return_value = []
        tool_context["client"].chat_stream.return_value = iter([])

        with patch("builtins.print"):
            tool_aware_renderer.render_streaming_response(iter(chunks), tool_context)

        # Confirmation should not be called
        tool_aware_renderer.confirmation_ui.confirm_tool_execution.assert_not_called()

    def test_tool_execution_service_not_available(self, mock_base_renderer):
        """Test behavior when tool execution service is not available."""
        renderer = ToolAwareRenderer(mock_base_renderer, None)  # No execution service

        # Create proper mock session
        session = Mock()
        session.messages = Mock()
        session.messages.__len__ = Mock(return_value=2)
        session.metadata = Mock()
        session.metadata.message_count = 0
        session.metadata.updated_at = ""
        session.save_session = Mock()

        tool_context = {
            "tools_enabled": True,
            "tool_settings": ToolSettings(),
            "session": session,
            "model": "test-model",
            "client": Mock(),
            "available_tools": [],
        }

        mock_function = Mock()
        mock_function.name = "test_tool"
        mock_function.arguments = {}

        tool_call = Mock()
        tool_call.function = mock_function

        message = MockMessage(tool_calls=[tool_call])
        chunks = [MockChatResponse(message, done=False)]

        tool_context["session"].get_messages_for_api.return_value = []
        tool_context["client"].chat_stream.return_value = iter([])

        with patch("builtins.print"):
            result = renderer.render_streaming_response(iter(chunks), tool_context)

        # Should handle gracefully but still return a result from base renderer
        assert result is not None

    def test_session_message_updates(self, tool_aware_renderer, tool_context):
        """Test that tool calls and responses are added to session."""
        mock_function = Mock()
        mock_function.name = "test_tool"
        mock_function.arguments = {"arg": "value"}

        tool_call = Mock()
        tool_call.function = mock_function

        message = MockMessage(content="Using tool", tool_calls=[tool_call])
        chunks = [MockChatResponse(message, done=False)]

        # Mock successful tool execution
        tool_result = ToolExecutionResult(
            success=True, result="Tool completed", tool_name="test_tool"
        )
        tool_aware_renderer.tool_execution_service.execute_tool.return_value = (
            tool_result
        )

        tool_context["session"].get_messages_for_api.return_value = []
        tool_context["client"].chat_stream.return_value = iter([])

        with patch("builtins.print"):
            tool_aware_renderer.render_streaming_response(iter(chunks), tool_context)

        # Verify messages were added to session
        assert (
            tool_context["session"].messages.append.call_count == 2
        )  # Tool call + tool response
        assert tool_context["session"].save_session.call_count == 2

    def test_delegate_methods(self, tool_aware_renderer, mock_base_renderer):
        """Test that methods are properly delegated to base renderer."""
        # Test set_mode
        tool_aware_renderer.set_mode("markdown")
        mock_base_renderer.set_mode.assert_called_with("markdown")

        # Test set_show_thinking
        tool_aware_renderer.set_show_thinking(True)
        mock_base_renderer.set_show_thinking.assert_called_with(True)

        # Test is_markdown_enabled
        mock_base_renderer.is_markdown_enabled.return_value = True
        result = tool_aware_renderer.is_markdown_enabled()
        assert result is True

        # Test render_static_text
        tool_aware_renderer.render_static_text("Hello")
        mock_base_renderer.render_static_text.assert_called_with("Hello")

    def test_delegate_methods_fallback(self, mock_base_renderer):
        """Test delegation fallback when methods don't exist on base renderer."""
        # Remove methods from mock
        del mock_base_renderer.set_mode
        del mock_base_renderer.set_show_thinking
        del mock_base_renderer.is_markdown_enabled
        del mock_base_renderer.render_static_text

        renderer = ToolAwareRenderer(mock_base_renderer)

        # These should not raise exceptions
        renderer.set_mode("markdown")  # Should do nothing
        renderer.set_show_thinking(True)  # Should do nothing
        result = renderer.is_markdown_enabled()  # Should return False
        assert result is False

        # render_static_text should fallback to print
        with patch("builtins.print") as mock_print:
            renderer.render_static_text("Hello")
            mock_print.assert_called_with("Hello")

    def test_tool_result_display(self, tool_aware_renderer, tool_context):
        """Test that tool results are displayed via confirmation UI."""
        mock_function = Mock()
        mock_function.name = "test_tool"
        mock_function.arguments = {}

        tool_call = Mock()
        tool_call.function = mock_function

        message = MockMessage(tool_calls=[tool_call])
        chunks = [MockChatResponse(message, done=False)]

        # Mock successful tool execution with specific result
        tool_result = ToolExecutionResult(
            success=True,
            result="Tool completed successfully",
            execution_time=0.5,
            tool_name="test_tool",
        )

        def mock_execute_tool_custom(
            tool_name, arguments, policy, confirm_callback=None
        ):
            return tool_result

        tool_aware_renderer.tool_execution_service.execute_tool.side_effect = (
            mock_execute_tool_custom
        )

        tool_context["session"].get_messages_for_api.return_value = []
        tool_context["client"].chat_stream.return_value = iter([])

        with patch("builtins.print"):
            tool_aware_renderer.render_streaming_response(iter(chunks), tool_context)

        # Verify result was shown
        tool_aware_renderer.confirmation_ui.show_tool_result.assert_called_once_with(
            "test_tool", True, "Tool completed successfully", None
        )

    def test_error_handling_in_tool_execution(self, tool_aware_renderer, tool_context):
        """Test error handling during tool execution."""
        mock_function = Mock()
        mock_function.name = "failing_tool"
        mock_function.arguments = {}

        tool_call = Mock()
        tool_call.function = mock_function

        message = MockMessage(tool_calls=[tool_call])
        chunks = [MockChatResponse(message, done=False)]

        # Mock failed tool execution
        tool_result = ToolExecutionResult(
            success=False,
            result=None,
            error_message="Tool execution failed",
            tool_name="failing_tool",
        )

        def mock_execute_tool_custom(
            tool_name, arguments, policy, confirm_callback=None
        ):
            return tool_result

        tool_aware_renderer.tool_execution_service.execute_tool.side_effect = (
            mock_execute_tool_custom
        )

        tool_context["session"].get_messages_for_api.return_value = []
        tool_context["client"].chat_stream.return_value = iter([])

        with patch("builtins.print"):
            tool_aware_renderer.render_streaming_response(iter(chunks), tool_context)

        # Verify error was shown
        tool_aware_renderer.confirmation_ui.show_tool_result.assert_called_once_with(
            "failing_tool", False, None, "Tool execution failed"
        )

    def test_continue_on_technical_error(self, tool_aware_renderer, tool_context):
        """Test that conversation continues when tool has technical error."""

        # Setup tool execution service to return technical error
        def mock_execute_tool_with_error(
            tool_name, arguments, policy, confirm_callback=None
        ):
            return ToolExecutionResult(
                success=False,
                result=None,
                error_message="Invalid arguments for tool 'test_tool': missing required positional argument: 'b'",
                tool_name=tool_name,
            )

        tool_aware_renderer.tool_execution_service.execute_tool.side_effect = (
            mock_execute_tool_with_error
        )

        # Create tool call
        mock_function = Mock()
        mock_function.name = "test_tool"
        mock_function.arguments = {"a": 5}  # Missing 'b' argument

        tool_call = Mock()
        tool_call.function = mock_function

        message = MockMessage(content="Let me calculate", tool_calls=[tool_call])
        chunks = [MockChatResponse(message, done=True)]

        # Setup continuation stream
        continuation_chunks = [
            MockChatResponse(
                MockMessage(content="I see the error, let me fix that"), done=True
            )
        ]
        tool_context["session"].get_messages_for_api.return_value = [
            {"role": "user", "content": "test"}
        ]
        tool_context["client"].chat_stream.return_value = iter(continuation_chunks)

        with patch("builtins.print") as mock_print:
            result = tool_aware_renderer.render_streaming_response(
                iter(chunks), tool_context
            )

        # Verify continuation was initiated
        tool_context["client"].chat_stream.assert_called_once()
        mock_print.assert_any_call("\n🤖 Processing 1 tool results...\n")

        # Verify tool error was shown
        tool_aware_renderer.confirmation_ui.show_tool_result.assert_called_once_with(
            "test_tool",
            False,
            None,
            "Invalid arguments for tool 'test_tool': missing required positional argument: 'b'",
        )

    def test_stop_on_user_denial(self, tool_aware_renderer, tool_context):
        """Test that conversation stops when user denies tool execution."""

        # Setup tool execution service to return user denial
        def mock_execute_tool_with_denial(
            tool_name, arguments, policy, confirm_callback=None
        ):
            return ToolExecutionResult(
                success=False,
                result=None,
                error_message="Tool execution denied by user",
                tool_name=tool_name,
            )

        tool_aware_renderer.tool_execution_service.execute_tool.side_effect = (
            mock_execute_tool_with_denial
        )

        # Create tool call
        mock_function = Mock()
        mock_function.name = "test_tool"
        mock_function.arguments = {"value": 42}

        tool_call = Mock()
        tool_call.function = mock_function

        message = MockMessage(content="Let me use a tool", tool_calls=[tool_call])
        chunks = [MockChatResponse(message, done=True)]

        tool_context["session"].get_messages_for_api.return_value = [
            {"role": "user", "content": "test"}
        ]

        with patch("builtins.print") as mock_print:
            result = tool_aware_renderer.render_streaming_response(
                iter(chunks), tool_context
            )

        # Verify continuation was NOT initiated
        tool_context["client"].chat_stream.assert_not_called()
        # Should not print the processing message
        mock_print.assert_not_called()

        # Verify tool denial was shown
        tool_aware_renderer.confirmation_ui.show_tool_result.assert_called_once_with(
            "test_tool", False, None, "Tool execution denied by user"
        )

    def test_continue_on_mixed_success_and_technical_error(
        self, tool_aware_renderer, tool_context
    ):
        """Test continuation when some tools succeed and others have technical errors."""

        # Setup tool execution service to return mixed results
        def mock_execute_tool_mixed(
            tool_name, arguments, policy, confirm_callback=None
        ):
            if tool_name == "working_tool":
                return ToolExecutionResult(
                    success=True,
                    result="Tool worked fine",
                    tool_name=tool_name,
                )
            else:  # failing_tool
                return ToolExecutionResult(
                    success=False,
                    result=None,
                    error_message="Tool execution failed: connection timeout",
                    tool_name=tool_name,
                )

        tool_aware_renderer.tool_execution_service.execute_tool.side_effect = (
            mock_execute_tool_mixed
        )

        # Create multiple tool calls
        working_function = Mock()
        working_function.name = "working_tool"
        working_function.arguments = {}

        failing_function = Mock()
        failing_function.name = "failing_tool"
        failing_function.arguments = {}

        working_call = Mock()
        working_call.function = working_function

        failing_call = Mock()
        failing_call.function = failing_function

        message = MockMessage(
            content="Let me use two tools", tool_calls=[working_call, failing_call]
        )
        chunks = [MockChatResponse(message, done=True)]

        # Setup continuation stream
        continuation_chunks = [
            MockChatResponse(MockMessage(content="Got partial results"), done=True)
        ]
        tool_context["session"].get_messages_for_api.return_value = [
            {"role": "user", "content": "test"}
        ]
        tool_context["client"].chat_stream.return_value = iter(continuation_chunks)

        with patch("builtins.print") as mock_print:
            result = tool_aware_renderer.render_streaming_response(
                iter(chunks), tool_context
            )

        # Verify continuation was initiated
        tool_context["client"].chat_stream.assert_called_once()
        mock_print.assert_any_call("\n🤖 Processing 2 tool results...\n")

    def test_stop_on_mixed_success_and_user_denial(
        self, tool_aware_renderer, tool_context
    ):
        """Test that conversation stops when any tool is denied by user, even if others succeed."""

        # Setup tool execution service to return mixed results
        def mock_execute_tool_mixed(
            tool_name, arguments, policy, confirm_callback=None
        ):
            if tool_name == "working_tool":
                return ToolExecutionResult(
                    success=True,
                    result="Tool worked fine",
                    tool_name=tool_name,
                )
            else:  # denied_tool
                return ToolExecutionResult(
                    success=False,
                    result=None,
                    error_message="Tool execution denied by user",
                    tool_name=tool_name,
                )

        tool_aware_renderer.tool_execution_service.execute_tool.side_effect = (
            mock_execute_tool_mixed
        )

        # Create multiple tool calls
        working_function = Mock()
        working_function.name = "working_tool"
        working_function.arguments = {}

        denied_function = Mock()
        denied_function.name = "denied_tool"
        denied_function.arguments = {}

        working_call = Mock()
        working_call.function = working_function

        denied_call = Mock()
        denied_call.function = denied_function

        message = MockMessage(
            content="Let me use two tools", tool_calls=[working_call, denied_call]
        )
        chunks = [MockChatResponse(message, done=True)]

        tool_context["session"].get_messages_for_api.return_value = [
            {"role": "user", "content": "test"}
        ]

        with patch("builtins.print") as mock_print:
            result = tool_aware_renderer.render_streaming_response(
                iter(chunks), tool_context
            )

        # Verify continuation was NOT initiated
        tool_context["client"].chat_stream.assert_not_called()
        # Should not print the processing message
        mock_print.assert_not_called()

    def test_continue_on_multiple_technical_errors(
        self, tool_aware_renderer, tool_context
    ):
        """Test continuation when all tools have technical errors."""

        # Setup tool execution service to return only technical errors
        def mock_execute_tool_all_errors(
            tool_name, arguments, policy, confirm_callback=None
        ):
            error_messages = {
                "tool1": "Invalid arguments for tool 'tool1': missing parameter",
                "tool2": "Tool execution failed: network error",
            }
            return ToolExecutionResult(
                success=False,
                result=None,
                error_message=error_messages.get(tool_name, "Unknown error"),
                tool_name=tool_name,
            )

        tool_aware_renderer.tool_execution_service.execute_tool.side_effect = (
            mock_execute_tool_all_errors
        )

        # Create multiple tool calls
        func1 = Mock()
        func1.name = "tool1"
        func1.arguments = {}

        func2 = Mock()
        func2.name = "tool2"
        func2.arguments = {}

        call1 = Mock()
        call1.function = func1

        call2 = Mock()
        call2.function = func2

        message = MockMessage(
            content="Let me try these tools", tool_calls=[call1, call2]
        )
        chunks = [MockChatResponse(message, done=True)]

        # Setup continuation stream
        continuation_chunks = [
            MockChatResponse(
                MockMessage(content="I see both tools failed, let me correct"),
                done=True,
            )
        ]
        tool_context["session"].get_messages_for_api.return_value = [
            {"role": "user", "content": "test"}
        ]
        tool_context["client"].chat_stream.return_value = iter(continuation_chunks)

        with patch("builtins.print") as mock_print:
            result = tool_aware_renderer.render_streaming_response(
                iter(chunks), tool_context
            )

        # Verify continuation was initiated
        tool_context["client"].chat_stream.assert_called_once()
        mock_print.assert_any_call("\n🤖 Processing 2 tool results...\n")

    def test_stop_on_multiple_user_denials(self, tool_aware_renderer, tool_context):
        """Test that conversation stops when all tools are denied by user."""

        # Setup tool execution service to return all denials
        def mock_execute_tool_all_denials(
            tool_name, arguments, policy, confirm_callback=None
        ):
            return ToolExecutionResult(
                success=False,
                result=None,
                error_message="Tool execution denied by user",
                tool_name=tool_name,
            )

        tool_aware_renderer.tool_execution_service.execute_tool.side_effect = (
            mock_execute_tool_all_denials
        )

        # Create multiple tool calls
        func1 = Mock()
        func1.name = "tool1"
        func1.arguments = {}

        func2 = Mock()
        func2.name = "tool2"
        func2.arguments = {}

        call1 = Mock()
        call1.function = func1

        call2 = Mock()
        call2.function = func2

        message = MockMessage(
            content="Let me try these tools", tool_calls=[call1, call2]
        )
        chunks = [MockChatResponse(message, done=True)]

        tool_context["session"].get_messages_for_api.return_value = [
            {"role": "user", "content": "test"}
        ]

        with patch("builtins.print") as mock_print:
            result = tool_aware_renderer.render_streaming_response(
                iter(chunks), tool_context
            )

        # Verify continuation was NOT initiated
        tool_context["client"].chat_stream.assert_not_called()
        # Should not print the processing message
        mock_print.assert_not_called()

    def test_no_continuation_with_no_tool_results(
        self, tool_aware_renderer, tool_context
    ):
        """Test that conversation doesn't continue when there are no tool results."""
        # Create message without tool calls
        message = MockMessage(content="Just regular content")
        chunks = [MockChatResponse(message, done=True)]

        tool_context["session"].get_messages_for_api.return_value = [
            {"role": "user", "content": "test"}
        ]

        with patch("builtins.print") as mock_print:
            result = tool_aware_renderer.render_streaming_response(
                iter(chunks), tool_context
            )

        # Verify continuation was NOT initiated
        tool_context["client"].chat_stream.assert_not_called()
        # Should not print the processing message
        mock_print.assert_not_called()

    def test_never_confirm_policy_with_technical_error_continues(
        self, tool_aware_renderer, tool_context
    ):
        """Test that NEVER_CONFIRM policy with technical errors still continues conversation."""
        # Set policy to never confirm
        tool_context[
            "tool_settings"
        ].execution_policy = ToolExecutionPolicy.NEVER_CONFIRM

        # Setup tool execution service to return technical error (no confirmation asked)
        def mock_execute_tool_with_error(
            tool_name, arguments, policy, confirm_callback=None
        ):
            # With NEVER_CONFIRM, confirm_callback should not be called
            assert policy == ToolExecutionPolicy.NEVER_CONFIRM
            return ToolExecutionResult(
                success=False,
                result=None,
                error_message="Invalid arguments for tool 'test_tool': missing required parameter",
                tool_name=tool_name,
            )

        tool_aware_renderer.tool_execution_service.execute_tool.side_effect = (
            mock_execute_tool_with_error
        )

        # Create tool call
        mock_function = Mock()
        mock_function.name = "test_tool"
        mock_function.arguments = {"wrong": "args"}

        tool_call = Mock()
        tool_call.function = mock_function

        message = MockMessage(content="Let me use this tool", tool_calls=[tool_call])
        chunks = [MockChatResponse(message, done=True)]

        # Setup continuation stream
        continuation_chunks = [
            MockChatResponse(
                MockMessage(content="I see the error, let me fix that"), done=True
            )
        ]
        tool_context["session"].get_messages_for_api.return_value = [
            {"role": "user", "content": "test"}
        ]
        tool_context["client"].chat_stream.return_value = iter(continuation_chunks)

        with patch("builtins.print") as mock_print:
            result = tool_aware_renderer.render_streaming_response(
                iter(chunks), tool_context
            )

        # Verify no confirmation was requested
        tool_aware_renderer.confirmation_ui.confirm_tool_execution.assert_not_called()

        # Verify continuation was initiated (technical error should allow continuation)
        tool_context["client"].chat_stream.assert_called_once()
        mock_print.assert_any_call("\n🤖 Processing 1 tool results...\n")

    def test_never_confirm_policy_with_success_continues(
        self, tool_aware_renderer, tool_context
    ):
        """Test that NEVER_CONFIRM policy with successful tools continues conversation."""
        # Set policy to never confirm
        tool_context[
            "tool_settings"
        ].execution_policy = ToolExecutionPolicy.NEVER_CONFIRM

        # Setup tool execution service to return success (no confirmation asked)
        def mock_execute_tool_success(
            tool_name, arguments, policy, confirm_callback=None
        ):
            # With NEVER_CONFIRM, confirm_callback should not be called
            assert policy == ToolExecutionPolicy.NEVER_CONFIRM
            return ToolExecutionResult(
                success=True,
                result="Tool executed successfully",
                tool_name=tool_name,
            )

        tool_aware_renderer.tool_execution_service.execute_tool.side_effect = (
            mock_execute_tool_success
        )

        # Create tool call
        mock_function = Mock()
        mock_function.name = "test_tool"
        mock_function.arguments = {"correct": "args"}

        tool_call = Mock()
        tool_call.function = mock_function

        message = MockMessage(content="Let me use this tool", tool_calls=[tool_call])
        chunks = [MockChatResponse(message, done=True)]

        # Setup continuation stream
        continuation_chunks = [
            MockChatResponse(
                MockMessage(content="Great! The tool worked perfectly"), done=True
            )
        ]
        tool_context["session"].get_messages_for_api.return_value = [
            {"role": "user", "content": "test"}
        ]
        tool_context["client"].chat_stream.return_value = iter(continuation_chunks)

        with patch("builtins.print") as mock_print:
            result = tool_aware_renderer.render_streaming_response(
                iter(chunks), tool_context
            )

        # Verify no confirmation was requested
        tool_aware_renderer.confirmation_ui.confirm_tool_execution.assert_not_called()

        # Verify continuation was initiated (success should allow continuation)
        tool_context["client"].chat_stream.assert_called_once()
        mock_print.assert_any_call("\n🤖 Processing 1 tool results...\n")

    def test_never_confirm_policy_no_user_denials_possible(
        self, tool_aware_renderer, tool_context
    ):
        """Test that NEVER_CONFIRM policy never produces user denial errors."""
        # Set policy to never confirm
        tool_context[
            "tool_settings"
        ].execution_policy = ToolExecutionPolicy.NEVER_CONFIRM

        # Use the default mock that returns success
        # This verifies our mock setup doesn't accidentally create denial errors

        # Create tool call
        mock_function = Mock()
        mock_function.name = "test_tool"
        mock_function.arguments = {}

        tool_call = Mock()
        tool_call.function = mock_function

        message = MockMessage(content="Let me use this tool", tool_calls=[tool_call])
        chunks = [MockChatResponse(message, done=True)]

        # Setup continuation stream
        continuation_chunks = [
            MockChatResponse(MockMessage(content="Tool completed"), done=True)
        ]
        tool_context["session"].get_messages_for_api.return_value = [
            {"role": "user", "content": "test"}
        ]
        tool_context["client"].chat_stream.return_value = iter(continuation_chunks)

        with patch("builtins.print") as mock_print:
            result = tool_aware_renderer.render_streaming_response(
                iter(chunks), tool_context
            )

        # Verify no confirmation was requested
        tool_aware_renderer.confirmation_ui.confirm_tool_execution.assert_not_called()

        # Verify continuation happened (no user denials should occur)
        tool_context["client"].chat_stream.assert_called_once()

        # Verify tool execution was called with NEVER_CONFIRM policy
        tool_aware_renderer.tool_execution_service.execute_tool.assert_called_once()
        call_args = tool_aware_renderer.tool_execution_service.execute_tool.call_args
        assert call_args[0][2] == ToolExecutionPolicy.NEVER_CONFIRM  # policy argument

    def test_never_confirm_policy_with_wrong_arguments_continues(
        self, tool_aware_renderer, tool_context
    ):
        """Test NEVER_CONFIRM policy with wrong arguments: no confirmation, technical error, conversation continues."""
        # Set policy to never confirm
        tool_context[
            "tool_settings"
        ].execution_policy = ToolExecutionPolicy.NEVER_CONFIRM

        # Setup tool execution service to simulate wrong arguments scenario
        def mock_execute_tool_wrong_args(
            tool_name, arguments, policy, confirm_callback=None
        ):
            # Verify policy is NEVER_CONFIRM and no confirmation is requested
            assert policy == ToolExecutionPolicy.NEVER_CONFIRM
            # With NEVER_CONFIRM, confirm_callback should not be called at all

            # Simulate what happens when tool gets wrong arguments:
            # The function call fails with TypeError, which gets caught and converted to ToolExecutionResult
            return ToolExecutionResult(
                success=False,
                result=None,
                error_message="Invalid arguments for tool 'add_numbers': unexpected keyword argument 'wrong_param'",
                tool_name=tool_name,
            )

        tool_aware_renderer.tool_execution_service.execute_tool.side_effect = (
            mock_execute_tool_wrong_args
        )

        # Create tool call with wrong arguments (simulating LLM mistake)
        mock_function = Mock()
        mock_function.name = "add_numbers"
        mock_function.arguments = {
            "x": 5,
            "wrong_param": 10,
        }  # Should be "y", not "wrong_param"

        tool_call = Mock()
        tool_call.function = mock_function

        message = MockMessage(
            content="Let me add these numbers", tool_calls=[tool_call]
        )
        chunks = [MockChatResponse(message, done=True)]

        # Setup continuation stream (LLM should get a chance to self-correct)
        continuation_chunks = [
            MockChatResponse(
                MockMessage(
                    content="I see the error, let me use the correct parameter name"
                ),
                done=True,
            )
        ]
        tool_context["session"].get_messages_for_api.return_value = [
            {"role": "user", "content": "Add 5 and 10"},
            {
                "role": "assistant",
                "content": "Let me add these numbers",
                "tool_calls": [
                    {
                        "function": {
                            "name": "add_numbers",
                            "arguments": {"x": 5, "wrong_param": 10},
                        }
                    }
                ],
            },
            {
                "role": "tool",
                "content": "Error: Invalid arguments for tool 'add_numbers': unexpected keyword argument 'wrong_param'",
            },
        ]
        tool_context["client"].chat_stream.return_value = iter(continuation_chunks)

        with patch("builtins.print") as mock_print:
            result = tool_aware_renderer.render_streaming_response(
                iter(chunks), tool_context
            )

        # Verify no confirmation was requested (NEVER_CONFIRM policy)
        tool_aware_renderer.confirmation_ui.confirm_tool_execution.assert_not_called()

        # Verify the technical error was shown to user
        tool_aware_renderer.confirmation_ui.show_tool_result.assert_called_once_with(
            "add_numbers",
            False,
            None,
            "Invalid arguments for tool 'add_numbers': unexpected keyword argument 'wrong_param'",
        )

        # Verify continuation was initiated (technical error should allow LLM to self-correct)
        tool_context["client"].chat_stream.assert_called_once()
        mock_print.assert_any_call("\n🤖 Processing 1 tool results...\n")

        # This demonstrates the key behavior:
        # 1. No user confirmation needed (NEVER_CONFIRM)
        # 2. Tool fails with technical error (wrong arguments)
        # 3. Error is shown to user and added to chat history
        # 4. Conversation continues automatically
        # 5. LLM gets chance to see error and self-correct

    def test_confirm_destructive_policy_with_user_denial_stops(
        self, tool_aware_renderer, tool_context
    ):
        """Test that CONFIRM_DESTRUCTIVE policy with user denial stops conversation."""
        # Set policy to confirm destructive (currently same as ALWAYS_CONFIRM)
        tool_context[
            "tool_settings"
        ].execution_policy = ToolExecutionPolicy.CONFIRM_DESTRUCTIVE

        # Setup confirmation to deny
        tool_aware_renderer.confirmation_ui.confirm_tool_execution.return_value = False

        # Setup tool execution service to return user denial
        def mock_execute_tool_with_denial(
            tool_name, arguments, policy, confirm_callback=None
        ):
            # With CONFIRM_DESTRUCTIVE, confirm_callback should be called
            assert policy == ToolExecutionPolicy.CONFIRM_DESTRUCTIVE
            if confirm_callback:
                confirmed = confirm_callback(tool_name, arguments)
                if not confirmed:
                    return ToolExecutionResult(
                        success=False,
                        result=None,
                        error_message="Tool execution denied by user",
                        tool_name=tool_name,
                    )
            return ToolExecutionResult(
                success=True,
                result="Tool executed successfully",
                tool_name=tool_name,
            )

        tool_aware_renderer.tool_execution_service.execute_tool.side_effect = (
            mock_execute_tool_with_denial
        )

        # Create tool call
        mock_function = Mock()
        mock_function.name = "destructive_tool"
        mock_function.arguments = {"action": "delete"}

        tool_call = Mock()
        tool_call.function = mock_function

        message = MockMessage(content="Let me delete something", tool_calls=[tool_call])
        chunks = [MockChatResponse(message, done=True)]

        tool_context["session"].get_messages_for_api.return_value = [
            {"role": "user", "content": "test"}
        ]

        with patch("builtins.print") as mock_print:
            result = tool_aware_renderer.render_streaming_response(
                iter(chunks), tool_context
            )

        # Verify confirmation was requested
        tool_aware_renderer.confirmation_ui.confirm_tool_execution.assert_called_once()

        # Verify continuation was NOT initiated (user denial should stop)
        tool_context["client"].chat_stream.assert_not_called()
        # Should not print the processing message
        mock_print.assert_not_called()

    def test_confirm_destructive_policy_with_technical_error_continues(
        self, tool_aware_renderer, tool_context
    ):
        """Test that CONFIRM_DESTRUCTIVE policy with technical errors continues conversation."""
        # Set policy to confirm destructive (currently same as ALWAYS_CONFIRM)
        tool_context[
            "tool_settings"
        ].execution_policy = ToolExecutionPolicy.CONFIRM_DESTRUCTIVE

        # Setup confirmation to allow
        tool_aware_renderer.confirmation_ui.confirm_tool_execution.return_value = True

        # Setup tool execution service to return technical error after confirmation
        def mock_execute_tool_with_error(
            tool_name, arguments, policy, confirm_callback=None
        ):
            # With CONFIRM_DESTRUCTIVE, confirm_callback should be called
            assert policy == ToolExecutionPolicy.CONFIRM_DESTRUCTIVE
            if confirm_callback:
                confirmed = confirm_callback(tool_name, arguments)
                if not confirmed:
                    return ToolExecutionResult(
                        success=False,
                        result=None,
                        error_message="Tool execution denied by user",
                        tool_name=tool_name,
                    )
            # Even after confirmation, tool can still fail with technical error
            return ToolExecutionResult(
                success=False,
                result=None,
                error_message="Tool execution failed: network timeout",
                tool_name=tool_name,
            )

        tool_aware_renderer.tool_execution_service.execute_tool.side_effect = (
            mock_execute_tool_with_error
        )

        # Create tool call
        mock_function = Mock()
        mock_function.name = "network_tool"
        mock_function.arguments = {"url": "https://example.com"}

        tool_call = Mock()
        tool_call.function = mock_function

        message = MockMessage(content="Let me fetch data", tool_calls=[tool_call])
        chunks = [MockChatResponse(message, done=True)]

        # Setup continuation stream
        continuation_chunks = [
            MockChatResponse(
                MockMessage(content="I see there was a network error, let me retry"),
                done=True,
            )
        ]
        tool_context["session"].get_messages_for_api.return_value = [
            {"role": "user", "content": "test"}
        ]
        tool_context["client"].chat_stream.return_value = iter(continuation_chunks)

        with patch("builtins.print") as mock_print:
            result = tool_aware_renderer.render_streaming_response(
                iter(chunks), tool_context
            )

        # Verify confirmation was requested and approved
        tool_aware_renderer.confirmation_ui.confirm_tool_execution.assert_called_once()

        # Verify continuation was initiated (technical error should allow continuation)
        tool_context["client"].chat_stream.assert_called_once()
        mock_print.assert_any_call("\n🤖 Processing 1 tool results...\n")
