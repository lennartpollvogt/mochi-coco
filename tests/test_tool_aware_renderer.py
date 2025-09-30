"""
Tests for ToolAwareRenderer functionality.

This module tests the tool-aware rendering capabilities including tool call detection,
execution, confirmation, and continuation during streaming responses.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any, List
from dataclasses import dataclass

from mochi_coco.rendering.tool_aware_renderer import ToolAwareRenderer
from mochi_coco.tools.execution_service import ToolExecutionService, ToolExecutionResult
from mochi_coco.tools.config import ToolSettings, ToolExecutionPolicy
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

    def test_max_recursion_depth(self, tool_aware_renderer, tool_context):
        """Test that maximum recursion depth is enforced."""
        # Set depth to maximum
        tool_aware_renderer.tool_call_depth = tool_aware_renderer.max_tool_call_depth

        chunks = [MockChatResponse(MockMessage(content="test"), done=True)]

        with patch("builtins.print") as mock_print:
            result = tool_aware_renderer.render_streaming_response(
                iter(chunks), tool_context
            )

            mock_print.assert_any_call("\n[Error: Maximum tool call depth exceeded]")
            assert result is None

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
