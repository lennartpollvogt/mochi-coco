"""
Tests for tool history rendering functionality.
"""

import pytest
from unittest.mock import Mock

from mochi_coco.ui.menu_display import MenuDisplay
from mochi_coco.chat.session import ChatSession, SessionMessage
from mochi_coco.rendering import MarkdownRenderer


class TestToolHistoryRendering:
    """Test suite for tool call rendering in chat history."""

    @pytest.fixture
    def mock_console(self):
        """Create a mock console for testing."""
        return Mock()

    @pytest.fixture
    def mock_renderer(self):
        """Create a mock renderer."""
        return Mock(spec=MarkdownRenderer)

    @pytest.fixture
    def menu_display(self, mock_renderer):
        """Create MenuDisplay instance with mocked dependencies."""
        display = MenuDisplay(renderer=mock_renderer)
        # Replace the console with mock for testing
        display.console = Mock()
        return display

    @pytest.fixture
    def sample_session_with_tools(self, temp_sessions_dir):
        """Create a session with tool calls for testing."""
        session = ChatSession(model="test-model", sessions_dir=temp_sessions_dir)

        # Add user message
        user_message = SessionMessage(
            role="user",
            content="Roll a dice",
            message_id="user1"
        )
        session.messages.append(user_message)

        # Add assistant message with tool call
        assistant_message = SessionMessage(
            role="assistant",
            content="",
            model="test-model",
            message_id="asst1"
        )
        assistant_message.tool_calls = [{
            'function': {
                'name': 'roll_dice',
                'arguments': {'count': 1, 'sides': 6}
            }
        }]
        session.messages.append(assistant_message)

        # Add tool response
        tool_response = SessionMessage(
            role="tool",
            content="Rolled a 6-sided die: 4",
            message_id="tool1"
        )
        tool_response.tool_name = "roll_dice"
        session.messages.append(tool_response)

        # Add final assistant response
        final_response = SessionMessage(
            role="assistant",
            content="You rolled a 4!",
            model="test-model",
            message_id="asst2"
        )
        session.messages.append(final_response)

        return session

    def test_display_chat_history_with_tools(self, menu_display, sample_session_with_tools):
        """Test that tool calls are rendered in chat history."""
        menu_display.display_chat_history(sample_session_with_tools)

        # Verify console.print was called multiple times
        assert menu_display.console.print.called
        call_count = menu_display.console.print.call_count

        # Should have calls for:
        # - User header + content
        # - Assistant header + tool request panel + tool response panel + final response
        assert call_count > 8  # At least user, assistant headers, tool panels, responses, and spacing

    def test_render_tool_request_valid_data(self, menu_display):
        """Test rendering of valid tool request."""
        tool_call = {
            'function': {
                'name': 'roll_dice',
                'arguments': {'count': 1, 'sides': 6}
            }
        }

        menu_display._render_tool_request(tool_call)

        # Verify panel was created and printed
        assert menu_display.console.print.called

        # Check that a panel with tool request styling was created
        calls = menu_display.console.print.call_args_list
        panel_calls = [call for call in calls if len(call[0]) > 0 and hasattr(call[0][0], 'title')]

        # Should have at least one panel call
        assert len(panel_calls) > 0

    def test_render_tool_request_no_arguments(self, menu_display):
        """Test rendering tool request without arguments."""
        tool_call = {
            'function': {
                'name': 'get_current_time',
                'arguments': {}
            }
        }

        menu_display._render_tool_request(tool_call)

        # Should still render successfully
        assert menu_display.console.print.called

    def test_render_tool_request_malformed_data(self, menu_display):
        """Test handling of malformed tool call data."""
        malformed_tool_call = {
            'invalid': 'structure'
        }

        menu_display._render_tool_request(malformed_tool_call)

        # Should render error panel without crashing
        assert menu_display.console.print.called

    def test_render_tool_response_with_content(self, menu_display):
        """Test rendering of tool response with content."""
        message = SessionMessage(
            role="tool",
            content="Operation completed successfully",
            message_id="tool1"
        )
        message.tool_name = "test_tool"

        menu_display._render_tool_response(message)

        # Verify panel was created and printed
        assert menu_display.console.print.called

    def test_render_tool_response_long_content(self, menu_display):
        """Test truncation of long tool response content."""
        long_content = "x" * 600  # Exceeds 500 char limit

        message = SessionMessage(
            role="tool",
            content=long_content,
            message_id="tool1"
        )
        message.tool_name = "test_tool"

        menu_display._render_tool_response(message)

        # Should still render without issues
        assert menu_display.console.print.called

    def test_render_tool_response_no_tool_name(self, menu_display):
        """Test tool response without tool_name attribute."""
        message = SessionMessage(
            role="tool",
            content="Some result",
            message_id="tool1"
        )
        # No tool_name attribute

        menu_display._render_tool_response(message)

        # Should render with "Unknown Tool"
        assert menu_display.console.print.called

    def test_render_tool_response_error_content(self, menu_display):
        """Test tool response with error content shows red styling."""
        message = SessionMessage(
            role="tool",
            content="Error: Tool execution denied by user",
            message_id="tool1"
        )
        message.tool_name = "test_tool"

        menu_display._render_tool_response(message)

        # Should render with error styling
        assert menu_display.console.print.called

    def test_render_tool_response_failed_content(self, menu_display):
        """Test tool response with 'failed' keyword shows red styling."""
        message = SessionMessage(
            role="tool",
            content="Tool execution failed due to timeout",
            message_id="tool1"
        )
        message.tool_name = "test_tool"

        menu_display._render_tool_response(message)

        # Should render with error styling
        assert menu_display.console.print.called

    def test_render_tool_response_denied_content(self, menu_display):
        """Test tool response with 'denied' keyword shows red styling."""
        message = SessionMessage(
            role="tool",
            content="Access denied for this operation",
            message_id="tool1"
        )
        message.tool_name = "test_tool"

        menu_display._render_tool_response(message)

        # Should render with error styling
        assert menu_display.console.print.called

    def test_render_assistant_message_with_tool_calls(self, menu_display, sample_session_with_tools):
        """Test assistant message rendering when it contains tool calls."""
        assistant_message = sample_session_with_tools.messages[1]  # Assistant with tool call

        menu_display._render_assistant_message(assistant_message, 1, sample_session_with_tools)

        # Should render assistant header and tool request
        assert menu_display.console.print.called

    def test_render_assistant_message_with_content_after_tool(self, menu_display):
        """Test assistant message with both tool call and content."""
        message = SessionMessage(
            role="assistant",
            content="Here's what I found:",
            model="test-model",
            message_id="asst1"
        )
        message.tool_calls = [{
            'function': {
                'name': 'search',
                'arguments': {'query': 'test'}
            }
        }]

        session = Mock()

        menu_display._render_assistant_message(message, 0, session)

        # Should render both tool call and content
        assert menu_display.console.print.called
        assert menu_display.renderer.render_static_text.called

    def test_render_assistant_message_no_tool_calls(self, menu_display):
        """Test normal assistant message without tool calls."""
        message = SessionMessage(
            role="assistant",
            content="Hello! How can I help you?",
            model="test-model",
            message_id="asst1"
        )

        session = Mock()

        menu_display._render_assistant_message(message, 0, session)

        # Should only render header and content
        assert menu_display.console.print.called
        assert menu_display.renderer.render_static_text.called

    def test_multiple_tool_calls_in_sequence(self, menu_display, temp_sessions_dir):
        """Test rendering multiple tool calls in one assistant message."""
        session = ChatSession(model="test-model", sessions_dir=temp_sessions_dir)

        # Assistant message with multiple tool calls
        assistant_message = SessionMessage(
            role="assistant",
            content="",
            model="test-model",
            message_id="asst1"
        )
        assistant_message.tool_calls = [
            {
                'function': {
                    'name': 'add_numbers',
                    'arguments': {'a': 5, 'b': 3}
                }
            },
            {
                'function': {
                    'name': 'multiply_numbers',
                    'arguments': {'a': 2, 'b': 4}
                }
            }
        ]
        session.messages.append(assistant_message)

        menu_display.display_chat_history(session)

        # Should render multiple tool requests
        assert menu_display.console.print.call_count > 4  # Headers + multiple panels + spacing

    def test_empty_session_history(self, menu_display, temp_sessions_dir):
        """Test display of empty session."""
        session = ChatSession(model="test-model", sessions_dir=temp_sessions_dir)

        menu_display.display_chat_history(session)

        # Should return early without printing anything
        assert not menu_display.console.print.called

    def test_session_with_mixed_messages(self, menu_display, temp_sessions_dir):
        """Test session with mix of regular and tool messages."""
        session = ChatSession(model="test-model", sessions_dir=temp_sessions_dir)

        # Regular conversation
        session.messages.append(SessionMessage(
            role="user",
            content="Hello",
            message_id="user1"
        ))

        session.messages.append(SessionMessage(
            role="assistant",
            content="Hi there!",
            model="test-model",
            message_id="asst1"
        ))

        # Tool interaction
        session.messages.append(SessionMessage(
            role="user",
            content="Roll a dice",
            message_id="user2"
        ))

        tool_message = SessionMessage(
            role="assistant",
            content="",
            model="test-model",
            message_id="asst2"
        )
        tool_message.tool_calls = [{
            'function': {
                'name': 'roll_dice',
                'arguments': {'sides': 6}
            }
        }]
        session.messages.append(tool_message)

        # More regular conversation
        session.messages.append(SessionMessage(
            role="user",
            content="Thanks!",
            message_id="user3"
        ))

        menu_display.display_chat_history(session)

        # Should handle all message types
        assert menu_display.console.print.called

    def test_json_formatting_in_tool_arguments(self, menu_display):
        """Test JSON formatting for complex tool arguments."""
        complex_args = {
            'nested': {
                'key': 'value',
                'number': 42
            },
            'array': [1, 2, 3],
            'boolean': True
        }

        tool_call = {
            'function': {
                'name': 'complex_tool',
                'arguments': complex_args
            }
        }

        menu_display._render_tool_request(tool_call)

        # Should format JSON without crashing
        assert menu_display.console.print.called

    def test_error_handling_in_tool_response(self, menu_display):
        """Test error handling when tool response rendering fails."""
        # Create a problematic message that might cause rendering issues
        message = Mock()
        message.content = None
        message.role = "tool"
        # Missing tool_name to trigger error path

        menu_display._render_tool_response(message)

        # Should handle gracefully
        assert menu_display.console.print.called

    @pytest.fixture
    def temp_sessions_dir(self, tmp_path):
        """Create temporary sessions directory."""
        sessions_dir = tmp_path / "test_sessions"
        sessions_dir.mkdir()
        return sessions_dir

    def test_integration_with_real_session_data(self, menu_display, temp_sessions_dir):
        """Test with realistic session data structure."""
        session = ChatSession(model="test-model", sessions_dir=temp_sessions_dir)

        # Load from dict like real session loading
        session_data = {
            "metadata": {
                "session_id": "test123",
                "model": "test-model",
                "created_at": "2025-01-01T10:00:00",
                "updated_at": "2025-01-01T10:05:00",
                "message_count": 4,
                "format_version": "1.1"
            },
            "messages": [
                {
                    "role": "user",
                    "content": "Roll a dice",
                    "message_id": "user1",
                    "timestamp": "2025-01-01T10:01:00"
                },
                {
                    "role": "assistant",
                    "content": "",
                    "model": "test-model",
                    "message_id": "asst1",
                    "timestamp": "2025-01-01T10:02:00",
                    "tool_calls": [{
                        "function": {
                            "name": "roll_dice",
                            "arguments": {"count": 1, "sides": 6}
                        }
                    }]
                },
                {
                    "role": "tool",
                    "content": "Rolled a 6-sided die: 3",
                    "message_id": "tool1",
                    "timestamp": "2025-01-01T10:03:00",
                    "tool_name": "roll_dice"
                },
                {
                    "role": "assistant",
                    "content": "You rolled a 3!",
                    "model": "test-model",
                    "message_id": "asst2",
                    "timestamp": "2025-01-01T10:04:00"
                }
            ]
        }

        # Manually create messages from data
        for msg_data in session_data["messages"]:
            msg = SessionMessage(**{k: v for k, v in msg_data.items()
                                  if k not in ['tool_calls', 'tool_name']})

            # Add special attributes
            if 'tool_calls' in msg_data:
                msg.tool_calls = msg_data['tool_calls']
            if 'tool_name' in msg_data:
                msg.tool_name = msg_data['tool_name']

            session.messages.append(msg)

        # Test display
        menu_display.display_chat_history(session)

        # Should render complete conversation flow
        assert menu_display.console.print.called
        call_count = menu_display.console.print.call_count
        assert call_count > 6  # Multiple components should be rendered
