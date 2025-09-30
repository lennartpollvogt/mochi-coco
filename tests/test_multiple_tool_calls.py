"""
Test multiple tool calls within a single LLM response.

This test demonstrates a bug in the current implementation where only the first
tool call in a multi-tool response gets executed.
"""

from unittest.mock import Mock
from dataclasses import dataclass
from typing import List, Any

from mochi_coco.rendering.tool_aware_renderer import ToolAwareRenderer
from mochi_coco.tools.execution_service import ToolExecutionService
from mochi_coco.tools.config import ToolSettings, ToolExecutionPolicy


@dataclass
class MockMessage:
    """Mock message for testing."""

    role: str = "assistant"
    content: str = ""
    tool_calls: List[Any] = None

    def __post_init__(self):
        if self.tool_calls is None:
            self.tool_calls = []


@dataclass
class MockChatResponse:
    """Mock ChatResponse for testing."""

    message: MockMessage
    done: bool = False

    def __post_init__(self):
        if not hasattr(self, "message") or self.message is None:
            self.message = MockMessage()


@dataclass
class MockToolCall:
    """Mock tool call for testing."""

    function: Any


class TestMultipleToolCallsBug:
    """Test demonstrating the multiple tool calls bug."""

    def test_multiple_tools_bug_demonstration(self):
        """Demonstrate that only the first tool call gets executed."""

        # Setup: Create execution service with simple functions
        functions = {
            "tool_a": lambda x: f"Result A: {x}",
            "tool_b": lambda x: f"Result B: {x}",
            "tool_c": lambda x: f"Result C: {x}",
        }
        execution_service = ToolExecutionService(functions)

        print(f"Created execution service with functions: {list(functions.keys())}")

        # Mock components
        base_renderer = Mock()
        base_renderer.render_streaming_response.return_value = None

        confirmation_ui = Mock()
        confirmation_ui.show_tool_result = Mock()

        session = Mock()
        session.messages = []
        session.metadata = Mock()
        session.get_messages_for_api.return_value = []
        session.save_session = Mock()

        client = Mock()
        empty_response = MockChatResponse(
            message=MockMessage(role="assistant", content="Done"), done=True
        )
        client.chat_stream.return_value = iter([empty_response])

        # Create renderer
        renderer = ToolAwareRenderer(base_renderer, execution_service, confirmation_ui)

        # Create stream with multiple tool calls in one response
        def create_multi_tool_stream():
            # Content chunk
            yield MockChatResponse(
                message=MockMessage(role="assistant", content="I'll use 3 tools: "),
                done=False,
            )

            # Multiple tool calls in one chunk (this is the key test case)
            mock_func_a = Mock()
            mock_func_a.name = "tool_a"
            mock_func_a.arguments = {"x": "first"}

            mock_func_b = Mock()
            mock_func_b.name = "tool_b"
            mock_func_b.arguments = {"x": "second"}

            mock_func_c = Mock()
            mock_func_c.name = "tool_c"
            mock_func_c.arguments = {"x": "third"}

            tool_calls = [
                MockToolCall(mock_func_a),
                MockToolCall(mock_func_b),
                MockToolCall(mock_func_c),
            ]

            message_with_tools = MockMessage(
                role="assistant", content="", tool_calls=tool_calls
            )
            print(
                f"Created message with {len(message_with_tools.tool_calls)} tool calls"
            )
            yield MockChatResponse(
                message=message_with_tools,
                done=False,
            )

            # Final chunk
            yield MockChatResponse(
                message=MockMessage(role="assistant", content=""), done=True
            )

        # Execute
        tool_settings = ToolSettings(
            tools=["tool_a", "tool_b", "tool_c"],
            execution_policy=ToolExecutionPolicy.NEVER_CONFIRM,
        )

        tool_context = {
            "tools_enabled": True,
            "tool_settings": tool_settings,
            "session": session,
            "model": "test-model",
            "client": client,
            "available_tools": [],
        }

        # Debug: Check what's in our tool context
        print(f"Tool context enabled: {tool_context.get('tools_enabled')}")
        print(f"Tool settings enabled: {tool_settings.is_enabled()}")
        print(f"Tool settings tools: {tool_settings.tools}")

        # Capture calls to base renderer for debugging
        original_render = base_renderer.render_streaming_response

        def debug_render(stream, context=None):
            print(
                f"Base renderer called with stream and context: {context is not None}"
            )
            # Count chunks in stream for debugging
            chunks = list(stream)
            print(f"Stream has {len(chunks)} chunks")
            for i, chunk in enumerate(chunks):
                tool_count = (
                    len(chunk.message.tool_calls) if chunk.message.tool_calls else 0
                )
                print(
                    f"  Chunk {i}: content='{chunk.message.content}', tool_calls={tool_count}"
                )
                if tool_count > 0:
                    for j, tc in enumerate(chunk.message.tool_calls):
                        print(
                            f"    Tool {j}: {tc.function.name} with args {tc.function.arguments}"
                        )
            return original_render(iter(chunks), context)

        base_renderer.render_streaming_response = debug_render

        # Test execution
        print("\n=== EXECUTING RENDERER ===")
        result = renderer.render_streaming_response(
            create_multi_tool_stream(), tool_context
        )
        print(f"Renderer returned: {result}")

        # Check results: Count how many tool responses were added to session
        print("\n=== SESSION MESSAGES ===")
        print(f"Total session messages: {len(session.messages)}")
        for i, msg in enumerate(session.messages):
            print(
                f"  Message {i}: role={getattr(msg, 'role', 'unknown')}, content='{getattr(msg, 'content', '')[:50]}...'"
            )
            # Check if this is an assistant message with tool calls
            if (
                hasattr(msg, "role")
                and msg.role == "assistant"
                and hasattr(msg, "tool_calls")
            ):
                tool_calls_count = len(msg.tool_calls) if msg.tool_calls else 0
                print(f"    Tool calls: {tool_calls_count}")
                if tool_calls_count > 0:
                    for j, tc in enumerate(msg.tool_calls):
                        if isinstance(tc, dict):
                            print(
                                f"      Tool {j}: {tc.get('function', {}).get('name', 'unknown')}"
                            )
                        else:
                            print(
                                f"      Tool {j}: {getattr(tc, 'function', {}).get('name', 'unknown')}"
                            )

        tool_responses = [
            msg
            for msg in session.messages
            if hasattr(msg, "role") and msg.role == "tool"
        ]
        actual_count = len(tool_responses)

        print("\n=== BUG DEMONSTRATION ===")
        print("Expected tool calls: 3 (tool_a, tool_b, tool_c)")
        print(f"Actual tool calls executed: {actual_count}")
        print(f"Bug exists: {actual_count < 3}")

        # Verify the bug: should be 3 but will likely be 1
        if actual_count == 3:
            print("✅ Bug has been fixed! All tools executed.")
        else:
            print(f"❌ Bug confirmed: Only {actual_count} out of 3 tools executed")

        # Show which tools were actually executed
        if tool_responses:
            for i, response in enumerate(tool_responses):
                print(f"  Tool {i + 1}: {response.content}")

    def test_debug_tool_call_detection(self):
        """Debug test to understand why tool calls aren't being detected."""

        # Create simple mock message with tool calls
        mock_func = Mock()
        mock_func.name = "test_tool"
        mock_func.arguments = {"arg": "value"}

        tool_call = MockToolCall(mock_func)
        message = MockMessage(role="assistant", content="", tool_calls=[tool_call])

        print(f"Created message with tool_calls: {message.tool_calls}")
        print(f"Tool call function name: {message.tool_calls[0].function.name}")
        print(f"hasattr check: {hasattr(message, 'tool_calls')}")
        print(f"tool_calls truth check: {bool(message.tool_calls)}")

        # Test the actual condition from StreamInterceptor
        if hasattr(message, "tool_calls") and message.tool_calls:
            print("✅ Tool calls would be detected by StreamInterceptor")
        else:
            print("❌ Tool calls would NOT be detected by StreamInterceptor")

    def test_all_tool_calls_stored_in_session(self):
        """Test that all tool calls from one response are stored in the assistant message."""

        # Use same successful pattern as test_multiple_tools_bug_demonstration
        functions = {
            "tool_a": lambda x: f"Result A: {x}",
            "tool_b": lambda x: f"Result B: {x}",
            "tool_c": lambda x: f"Result C: {x}",
        }
        execution_service = ToolExecutionService(functions)

        # Mock components - make base renderer actually consume the stream
        base_renderer = Mock()

        def mock_render_streaming(stream, context=None):
            # Consume the stream like a real renderer would
            _chunks = list(stream)
            return None

        base_renderer.render_streaming_response = mock_render_streaming

        confirmation_ui = Mock()
        confirmation_ui.show_tool_result = Mock()

        session = Mock()
        session.messages = []
        session.metadata = Mock()
        session.get_messages_for_api.return_value = []
        session.save_session = Mock()

        client = Mock()
        empty_response = MockChatResponse(
            message=MockMessage(role="assistant", content="Done"), done=True
        )
        client.chat_stream.return_value = iter([empty_response])

        # Create renderer
        renderer = ToolAwareRenderer(base_renderer, execution_service, confirmation_ui)

        # Create stream - use same pattern as working test
        def create_multi_tool_stream():
            # Content chunk
            yield MockChatResponse(
                message=MockMessage(role="assistant", content="I'll use 3 tools: "),
                done=False,
            )

            # Multiple tool calls in one chunk (this is the key test case)
            mock_func_a = Mock()
            mock_func_a.name = "tool_a"
            mock_func_a.arguments = {"x": "first"}

            mock_func_b = Mock()
            mock_func_b.name = "tool_b"
            mock_func_b.arguments = {"x": "second"}

            mock_func_c = Mock()
            mock_func_c.name = "tool_c"
            mock_func_c.arguments = {"x": "third"}

            tool_calls = [
                MockToolCall(mock_func_a),
                MockToolCall(mock_func_b),
                MockToolCall(mock_func_c),
            ]

            message_with_tools = MockMessage(
                role="assistant", content="", tool_calls=tool_calls
            )
            yield MockChatResponse(
                message=message_with_tools,
                done=False,
            )

            # Final chunk
            yield MockChatResponse(
                message=MockMessage(role="assistant", content=""), done=True
            )

        # Execute
        tool_settings = ToolSettings(
            tools=["tool_a", "tool_b", "tool_c"],
            execution_policy=ToolExecutionPolicy.NEVER_CONFIRM,
        )

        tool_context = {
            "tools_enabled": True,
            "tool_settings": tool_settings,
            "session": session,
            "model": "test-model",
            "client": client,
            "available_tools": [],
        }

        # Test execution
        renderer.render_streaming_response(create_multi_tool_stream(), tool_context)

        # Verify session structure: 1 assistant message with ALL tool calls + 3 tool response messages = 4 total
        assert len(session.messages) == 4, (
            f"Expected 4 messages, got {len(session.messages)}"
        )

        # Find the assistant message with tool calls
        assistant_messages = [
            msg
            for msg in session.messages
            if hasattr(msg, "role") and msg.role == "assistant"
        ]

        assert len(assistant_messages) == 1, (
            f"Expected 1 assistant message, got {len(assistant_messages)}"
        )

        assistant_msg = assistant_messages[0]

        # Verify the assistant message has ALL tool calls
        assert hasattr(assistant_msg, "tool_calls"), (
            "Assistant message should have tool_calls attribute"
        )
        assert assistant_msg.tool_calls is not None, "tool_calls should not be None"
        assert len(assistant_msg.tool_calls) == 3, (
            f"Expected 3 tool calls, got {len(assistant_msg.tool_calls)}"
        )

        # Verify the tool calls contain the correct information
        tool_names = [tc["function"]["name"] for tc in assistant_msg.tool_calls]
        expected_names = ["tool_a", "tool_b", "tool_c"]
        assert tool_names == expected_names, (
            f"Expected {expected_names}, got {tool_names}"
        )

        # Verify arguments are preserved
        expected_args_list = [{"x": "first"}, {"x": "second"}, {"x": "third"}]
        for i, tc in enumerate(assistant_msg.tool_calls):
            expected_args = expected_args_list[i]
            actual_args = tc["function"]["arguments"]
            assert actual_args == expected_args, (
                f"Tool {i} args: expected {expected_args}, got {actual_args}"
            )

        print("✅ All tool calls properly stored in session JSON structure")
        print(
            f"Assistant message contains {len(assistant_msg.tool_calls)} tool calls as expected"
        )
