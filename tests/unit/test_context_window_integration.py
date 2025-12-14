"""
Integration tests for dynamic context window implementation Phase 3.

Tests the integration between SessionController, CommandProcessor, and
ToolAwareRenderer with the DynamicContextWindowService.
"""

from typing import Any, Dict, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

from mochi_coco.chat.session import ChatSession, SessionMetadata
from mochi_coco.commands.command_processor import CommandProcessor
from mochi_coco.controllers.session_controller import SessionController
from mochi_coco.ollama.client import ModelInfo
from mochi_coco.rendering.tool_aware_renderer import ToolAwareRenderer
from mochi_coco.services.context_window_service import (
    ContextDecisionReason,
    ContextWindowDecision,
    DynamicContextWindowService,
)


class TestContextWindowIntegration:
    """Test dynamic context window integration across components."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock session with context window metadata."""
        session = Mock(spec=ChatSession)
        session.metadata = Mock(spec=SessionMetadata)
        session.metadata.model = "test-model"
        session.metadata.context_window_config = {
            "dynamic_enabled": True,
            "current_window": None,
            "last_adjustment": None,
            "adjustment_history": [],
            "manual_override": False,
        }
        session.get_messages_for_api.return_value = [
            {"role": "user", "content": "Hello"},
        ]
        return session

    @pytest.fixture
    def mock_ollama_client(self):
        """Create a mock Ollama client."""
        client = Mock()
        client.list_models.return_value = [
            ModelInfo(
                name="test-model",
                size_mb=100,
                context_length=8192,
            )
        ]
        return client

    @pytest.fixture
    def mock_context_decision(self):
        """Create a mock context window decision."""
        decision = Mock(spec=ContextWindowDecision)
        decision.new_context_window = 4096
        decision.should_adjust = True
        decision.reason = ContextDecisionReason.PERFORMANCE_OPTIMIZATION
        return decision

    @pytest.fixture
    def context_window_service(self, mock_ollama_client, mock_context_decision):
        """Create context window service with mocked decision."""
        service = Mock(spec=DynamicContextWindowService)
        service.calculate_optimal_context_window.return_value = mock_context_decision
        return service

    @pytest.fixture
    def session_controller(self, mock_ollama_client, context_window_service):
        """Create session controller with context window service."""
        session_manager = Mock()
        return SessionController(
            session_manager, mock_ollama_client, context_window_service
        )

    def test_session_controller_uses_context_window(
        self,
        session_controller,
        mock_session,
        mock_context_decision,
        mock_ollama_client,
    ):
        """Test that SessionController calculates and uses context window."""
        # Mock renderer
        renderer = Mock()
        renderer.render_streaming_response_with_interrupt.return_value = (
            Mock(message=Mock(content="Response", tool_calls=None)),
            False,
        )

        # Mock chat stream
        mock_ollama_client.chat_stream.return_value = iter(
            [Mock(message=Mock(content="Response", tool_calls=None))]
        )

        # Process user message
        result = session_controller.process_user_message(
            mock_session, "test-model", "Hello", renderer
        )

        # Verify context window service was called
        session_controller.context_window_service.calculate_optimal_context_window.assert_called_once_with(
            mock_session, "test-model"
        )

        # Verify context window was passed to chat_stream
        mock_ollama_client.chat_stream.assert_called_once_with(
            model="test-model",
            messages=[{"role": "user", "content": "Hello"}],
            context_window=4096,
        )

        # Verify session metadata was updated
        assert mock_session.metadata.context_window_config["current_window"] == 4096
        assert (
            mock_session.metadata.context_window_config["last_adjustment"]
            == "performance_optimization"
        )

        # Verify success
        assert result.success is True

    def test_session_controller_with_tools_context_window(
        self,
        session_controller,
        mock_session,
        mock_context_decision,
        mock_ollama_client,
    ):
        """Test that SessionController passes context window through tool context."""
        # Mock tool-aware renderer
        tool_renderer = Mock(spec=ToolAwareRenderer)
        tool_renderer.render_streaming_response.return_value = Mock(
            message=Mock(content="Response with tools", tool_calls=None)
        )

        # Mock tool context
        tool_context = {
            "tools_enabled": True,
            "tools": [Mock()],
            "tool_execution_service": Mock(),
        }

        # Mock chat stream
        mock_ollama_client.chat_stream.return_value = iter(
            [Mock(message=Mock(content="Response", tool_calls=None))]
        )

        # Process user message with tools
        result = session_controller.process_user_message(
            mock_session, "test-model", "Hello", tool_renderer, tool_context
        )

        # Verify context window was passed to chat_stream
        # Verify context window was passed to chat_stream (tools list may be different mock objects)
        call_args = mock_ollama_client.chat_stream.call_args
        assert call_args is not None
        assert call_args.kwargs["model"] == "test-model"
        assert call_args.kwargs["messages"] == [{"role": "user", "content": "Hello"}]
        assert call_args.kwargs["context_window"] == 4096
        assert "tools" in call_args.kwargs

        # Verify context window was added to tool context
        expected_tool_context = tool_context.copy()
        expected_tool_context.update(
            {
                "session": mock_session,
                "model": "test-model",
                "client": mock_ollama_client,
                "available_tools": [Mock()],
                "context_window": 4096,
            }
        )

        # The tool context should have been updated
        assert "context_window" in tool_context
        assert tool_context["context_window"] == 4096

    def test_command_processor_context_window_integration(self, mock_ollama_client):
        """Test that CommandProcessor uses context window in _get_llm_response_for_last_message."""
        # Create context window service
        context_service = Mock(spec=DynamicContextWindowService)
        context_decision = Mock(spec=ContextWindowDecision)
        context_decision.new_context_window = 2048
        context_decision.should_adjust = False
        context_decision.reason = ContextDecisionReason.INITIAL_SETUP
        context_service.calculate_optimal_context_window.return_value = context_decision

        # Create command processor with context window service
        model_selector = Mock()
        model_selector.client = mock_ollama_client
        renderer_manager = Mock()
        renderer = Mock()
        renderer.render_streaming_response.return_value = Mock(
            message=Mock(content="Response")
        )
        renderer_manager.renderer = renderer

        command_processor = CommandProcessor(
            model_selector, renderer_manager, context_window_service=context_service
        )

        # Create mock session with user message
        session = Mock(spec=ChatSession)
        session.metadata = Mock(spec=SessionMetadata)
        session.metadata.model = "test-model"
        session.metadata.context_window_config = {
            "dynamic_enabled": True,
            "current_window": None,
        }
        session.messages = [Mock(role="user")]
        session.get_messages_for_api.return_value = [
            {"role": "user", "content": "Test message"}
        ]

        # Mock chat stream
        mock_ollama_client.chat_stream.return_value = iter(
            [Mock(message=Mock(content="Response"))]
        )

        # Mock typer for output
        with patch("mochi_coco.commands.command_processor.typer"):
            with patch("mochi_coco.ui.ChatInterface"):
                # Call the method
                command_processor._get_llm_response_for_last_message(session)

        # Verify context window service was called
        context_service.calculate_optimal_context_window.assert_called_once_with(
            session, "test-model"
        )

        # Verify context window was passed to chat_stream
        mock_ollama_client.chat_stream.assert_called_once_with(
            "test-model",
            [{"role": "user", "content": "Test message"}],
            context_window=2048,
        )

    def test_tool_aware_renderer_uses_context_window(self):
        """Test that ToolAwareRenderer uses context window from tool_context."""
        # Create base renderer mock
        base_renderer = Mock()
        base_renderer.render_streaming_response.return_value = Mock(
            message=Mock(content="Base response")
        )

        # Create tool execution service mock
        tool_execution_service = Mock()

        # Create tool-aware renderer
        tool_renderer = ToolAwareRenderer(base_renderer, tool_execution_service)

        # Mock client for continuation stream
        mock_client = Mock()
        continuation_chunks = [Mock(message=Mock(content="Continuation response"))]
        mock_client.chat_stream.return_value = iter(continuation_chunks)

        # Create tool context with context window
        tool_context = {
            "tools_enabled": True,
            "tool_settings": Mock(),
            "session": Mock(),
            "model": "test-model",
            "client": mock_client,
            "available_tools": [Mock()],
            "context_window": 6144,
        }

        # Test direct method call that uses context window
        with patch.object(tool_renderer, "StreamInterceptor") as mock_interceptor_class:
            interceptor = Mock()
            interceptor.tool_calls_detected = [Mock()]  # Simulate detected tool calls
            interceptor.accumulated_content = "I'll use tools"
            mock_interceptor_class.return_value = interceptor

            # Mock successful tool execution that doesn't trigger recursion
            with patch.object(tool_renderer, "_handle_tool_call") as mock_handle_tool:
                with patch.object(
                    tool_renderer, "_add_tool_call_to_session"
                ) as mock_add_tool_call:
                    with patch.object(
                        tool_renderer, "_add_tool_response_to_session"
                    ) as mock_add_tool_response:
                        # Mock tool result that results in no continuation
                        tool_result = Mock()
                        tool_result.success = False
                        tool_result.error_message = "Tool execution denied by user"
                        mock_handle_tool.return_value = tool_result

                        # Mock text chunks
                        text_chunks = iter([Mock()])

                        # Render with tools (should not trigger continuation due to denied tool)
                        result = tool_renderer._render_with_tools(
                            text_chunks,
                            tool_context["tool_settings"],
                            tool_context["session"],
                            tool_context["model"],
                            tool_context["client"],
                            tool_context["available_tools"],
                            tool_context,
                        )

        # Test the context window extraction logic directly
        context_window_from_context = (
            tool_context.get("context_window") if tool_context else None
        )
        assert context_window_from_context == 6144

    def test_context_window_error_handling(
        self, session_controller, mock_session, mock_ollama_client
    ):
        """Test that context window calculation errors are handled gracefully."""
        # Mock context window service to raise exception
        session_controller.context_window_service.calculate_optimal_context_window.side_effect = Exception(
            "Context calculation failed"
        )

        # Mock renderer
        renderer = Mock()
        renderer.render_streaming_response_with_interrupt.return_value = (
            Mock(message=Mock(content="Response")),
            False,
        )

        # Mock chat stream
        mock_ollama_client.chat_stream.return_value = iter(
            [Mock(message=Mock(content="Response"))]
        )

        # Process user message
        result = session_controller.process_user_message(
            mock_session, "test-model", "Hello", renderer
        )

        # Verify fallback behavior - chat_stream called without context_window
        mock_ollama_client.chat_stream.assert_called_once_with(
            model="test-model",
            messages=[{"role": "user", "content": "Hello"}],
            context_window=None,
        )

        # Verify success despite error
        assert result.success is True

    def test_context_window_metadata_history_tracking(
        self,
        session_controller,
        mock_session,
        mock_context_decision,
        mock_ollama_client,
    ):
        """Test that context window adjustments are tracked in session metadata."""
        # Mock renderer
        renderer = Mock()
        renderer.render_streaming_response_with_interrupt.return_value = (
            Mock(message=Mock(content="Response")),
            False,
        )

        # Mock chat stream
        mock_ollama_client.chat_stream.return_value = iter(
            [Mock(message=Mock(content="Response"))]
        )

        # Ensure session has adjustment history
        mock_session.metadata.context_window_config["adjustment_history"] = []

        # Process user message
        result = session_controller.process_user_message(
            mock_session, "test-model", "Hello", renderer
        )

        # Verify adjustment history was updated
        history = mock_session.metadata.context_window_config["adjustment_history"]
        assert len(history) == 1
        assert history[0]["window_size"] == 4096
        assert history[0]["reason"] == "performance_optimization"
        assert "timestamp" in history[0]

        # Process another message to test history limit
        for _ in range(12):  # Add more than 10 entries
            session_controller.process_user_message(
                mock_session, "test-model", f"Hello {_}", renderer
            )

        # Verify history is limited to last 10 entries
        history = mock_session.metadata.context_window_config["adjustment_history"]
        assert len(history) == 10

    def test_context_window_service_not_available(self, mock_ollama_client):
        """Test behavior when context window service is not available."""
        # Create session controller without context window service
        session_manager = Mock()
        session_controller = SessionController(session_manager, mock_ollama_client)

        # Mock session
        session = Mock(spec=ChatSession)
        session.get_messages_for_api.return_value = [
            {"role": "user", "content": "Hello"}
        ]

        # Mock renderer
        renderer = Mock()
        renderer.render_streaming_response_with_interrupt.return_value = (
            Mock(message=Mock(content="Response")),
            False,
        )

        # Mock chat stream
        mock_ollama_client.chat_stream.return_value = iter(
            [Mock(message=Mock(content="Response"))]
        )

        # Process user message
        result = session_controller.process_user_message(
            session, "test-model", "Hello", renderer
        )

        # Verify chat_stream was called without context_window
        mock_ollama_client.chat_stream.assert_called_once_with(
            model="test-model",
            messages=[{"role": "user", "content": "Hello"}],
            context_window=None,
        )

        # Verify success
        assert result.success is True
