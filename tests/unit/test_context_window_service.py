"""
Unit tests for ContextWindowService.

Tests cover on-demand context calculation, error handling,
and integration with chat sessions and model information.
"""

from typing import List
from unittest.mock import MagicMock, Mock

import pytest

from mochi_coco.services.context_window_service import (
    ContextWindowInfo,
    ContextWindowService,
)


class TestContextWindowService:
    """Test suite for ContextWindowService functionality."""

    @pytest.fixture
    def mock_ollama_client(self):
        """Create a mock Ollama client."""
        mock_client = Mock()
        return mock_client

    @pytest.fixture
    def mock_model_info(self):
        """Create a mock ModelInfo object."""
        mock_model = Mock()
        mock_model.name = "llama2:7b"
        mock_model.context_length = 4096
        return mock_model

    @pytest.fixture
    def mock_session_with_valid_data(self):
        """Create a mock session with valid context data."""
        mock_session = Mock()
        mock_session.session_id = "test_session"

        # Create mock messages with valid context data
        mock_message = Mock()
        mock_message.role = "assistant"
        mock_message.tool_calls = None
        mock_message.eval_count = 150
        mock_message.prompt_eval_count = 50

        mock_session.messages = [mock_message]
        return mock_session

    @pytest.fixture
    def mock_session_with_tool_calls(self):
        """Create a mock session with tool calls that should be ignored."""
        mock_session = Mock()
        mock_session.session_id = "test_session"

        # Message with tool calls (should be ignored)
        mock_tool_message = Mock()
        mock_tool_message.role = "assistant"
        mock_tool_message.tool_calls = [{"name": "test_tool"}]
        mock_tool_message.eval_count = 100
        mock_tool_message.prompt_eval_count = 30

        # Valid message without tool calls
        mock_valid_message = Mock()
        mock_valid_message.role = "assistant"
        mock_valid_message.tool_calls = None
        mock_valid_message.eval_count = 75
        mock_valid_message.prompt_eval_count = 25

        mock_session.messages = [mock_tool_message, mock_valid_message]
        return mock_session

    @pytest.fixture
    def mock_session_no_valid_data(self):
        """Create a mock session with no valid context data."""
        mock_session = Mock()
        mock_session.session_id = "test_session"

        # Message without required fields
        mock_message = Mock()
        mock_message.role = "assistant"
        mock_message.tool_calls = None
        mock_message.eval_count = None
        mock_message.prompt_eval_count = None

        mock_session.messages = [mock_message]
        return mock_session

    @pytest.fixture
    def context_service(self, mock_ollama_client):
        """Create a ContextWindowService instance."""
        return ContextWindowService(mock_ollama_client)

    def test_service_initialization(self, mock_ollama_client):
        """Test service initialization."""
        service = ContextWindowService(mock_ollama_client)
        assert service.client == mock_ollama_client

    def test_calculate_context_usage_success(
        self,
        context_service,
        mock_ollama_client,
        mock_model_info,
        mock_session_with_valid_data,
    ):
        """Test successful context usage calculation."""
        # Setup mock
        mock_ollama_client.list_models.return_value = [mock_model_info]

        # Execute
        result = context_service.calculate_context_usage_on_demand(
            mock_session_with_valid_data, "llama2:7b"
        )

        # Verify
        assert result.has_valid_data is True
        assert result.current_usage == 200  # 150 + 50
        assert result.max_context == 4096
        assert result.percentage == (200 / 4096) * 100
        assert result.error_message is None

    def test_calculate_context_usage_model_not_found(
        self, context_service, mock_ollama_client, mock_session_with_valid_data
    ):
        """Test context calculation when model is not found."""
        # Setup mock - return empty list (model not found)
        mock_ollama_client.list_models.return_value = []

        # Execute
        result = context_service.calculate_context_usage_on_demand(
            mock_session_with_valid_data, "nonexistent_model"
        )

        # Verify
        assert result.has_valid_data is False
        assert result.current_usage == 0
        assert result.max_context == 0
        assert result.error_message == "Model context length unavailable"

    def test_calculate_context_usage_no_context_length(
        self, context_service, mock_ollama_client, mock_session_with_valid_data
    ):
        """Test context calculation when model has no context_length."""
        # Setup mock model without context_length
        mock_model = Mock()
        mock_model.name = "llama2:7b"
        mock_model.context_length = None
        mock_ollama_client.list_models.return_value = [mock_model]

        # Execute
        result = context_service.calculate_context_usage_on_demand(
            mock_session_with_valid_data, "llama2:7b"
        )

        # Verify
        assert result.has_valid_data is False
        assert result.error_message == "Model context length unavailable"

    def test_calculate_context_usage_no_valid_session_data(
        self,
        context_service,
        mock_ollama_client,
        mock_model_info,
        mock_session_no_valid_data,
    ):
        """Test context calculation when session has no valid context data."""
        # Setup mock
        mock_ollama_client.list_models.return_value = [mock_model_info]

        # Execute
        result = context_service.calculate_context_usage_on_demand(
            mock_session_no_valid_data, "llama2:7b"
        )

        # Verify
        assert result.has_valid_data is False
        assert result.current_usage == 0
        assert result.max_context == 4096  # Model context is available
        assert result.error_message == "No valid context data in session"

    def test_calculate_context_usage_ignores_tool_calls(
        self,
        context_service,
        mock_ollama_client,
        mock_model_info,
        mock_session_with_tool_calls,
    ):
        """Test that messages with tool_calls are ignored."""
        # Setup mock
        mock_ollama_client.list_models.return_value = [mock_model_info]

        # Execute
        result = context_service.calculate_context_usage_on_demand(
            mock_session_with_tool_calls, "llama2:7b"
        )

        # Verify - should use the message without tool_calls (75 + 25 = 100)
        assert result.has_valid_data is True
        assert result.current_usage == 100  # 75 + 25 from the valid message
        assert result.max_context == 4096

    def test_calculate_context_usage_network_error(
        self, context_service, mock_ollama_client, mock_session_with_valid_data
    ):
        """Test context calculation when network error occurs."""
        # Setup mock to raise exception
        mock_ollama_client.list_models.side_effect = Exception("Network timeout")

        # Execute
        result = context_service.calculate_context_usage_on_demand(
            mock_session_with_valid_data, "llama2:7b"
        )

        # Verify - network errors result in model context length unavailable
        assert result.has_valid_data is False
        assert result.current_usage == 0
        assert result.max_context == 0
        assert result.error_message == "Model context length unavailable"

    def test_calculate_context_usage_empty_session(
        self, context_service, mock_ollama_client, mock_model_info
    ):
        """Test context calculation with empty session."""
        # Setup mock session with no messages
        mock_session = Mock()
        mock_session.session_id = "empty_session"
        mock_session.messages = []

        mock_ollama_client.list_models.return_value = [mock_model_info]

        # Execute
        result = context_service.calculate_context_usage_on_demand(
            mock_session, "llama2:7b"
        )

        # Verify
        assert result.has_valid_data is False
        assert result.error_message == "No valid context data in session"

    def test_get_current_model_context_length_success(
        self, context_service, mock_ollama_client, mock_model_info
    ):
        """Test successful model context length retrieval."""
        # Setup mock
        mock_ollama_client.list_models.return_value = [mock_model_info]

        # Execute
        result = context_service._get_current_model_context_length("llama2:7b")

        # Verify
        assert result == 4096

    def test_get_current_model_context_length_no_models(
        self, context_service, mock_ollama_client
    ):
        """Test model context length retrieval when no models available."""
        # Setup mock
        mock_ollama_client.list_models.return_value = []

        # Execute
        result = context_service._get_current_model_context_length("llama2:7b")

        # Verify
        assert result is None

    def test_calculate_current_usage_from_history_success(self, context_service):
        """Test successful usage calculation from message history."""
        # Create mock messages
        mock_message1 = Mock()
        mock_message1.role = "user"

        mock_message2 = Mock()
        mock_message2.role = "assistant"
        mock_message2.tool_calls = None
        mock_message2.eval_count = 100
        mock_message2.prompt_eval_count = 50

        messages = [mock_message1, mock_message2]

        # Execute
        result = context_service._calculate_current_usage_from_history(messages)

        # Verify
        assert result == 150  # 100 + 50

    def test_calculate_current_usage_from_history_invalid_counts(self, context_service):
        """Test usage calculation with invalid count values."""
        # Create mock message with invalid counts
        mock_message = Mock()
        mock_message.role = "assistant"
        mock_message.tool_calls = None
        mock_message.eval_count = -5  # Invalid negative count
        mock_message.prompt_eval_count = 50

        messages = [mock_message]

        # Execute
        result = context_service._calculate_current_usage_from_history(messages)

        # Verify
        assert result is None

    def test_calculate_current_usage_from_history_no_valid_messages(
        self, context_service
    ):
        """Test usage calculation with no valid messages."""
        # Create mock messages that should be ignored
        mock_message1 = Mock()
        mock_message1.role = "user"  # Not assistant

        mock_message2 = Mock()
        mock_message2.role = "assistant"
        mock_message2.tool_calls = [{"name": "test"}]  # Has tool calls
        mock_message2.eval_count = 100
        mock_message2.prompt_eval_count = 50

        messages = [mock_message1, mock_message2]

        # Execute
        result = context_service._calculate_current_usage_from_history(messages)

        # Verify
        assert result is None

    def test_create_error_info(self, context_service):
        """Test error info creation."""
        result = context_service._create_error_info("Test error", 2048)

        assert result.current_usage == 0
        assert result.max_context == 2048
        assert result.percentage == 0.0
        assert result.has_valid_data is False
        assert result.error_message == "Test error"

    def test_percentage_calculation_edge_cases(
        self, context_service, mock_ollama_client
    ):
        """Test percentage calculation for edge cases."""
        # Test with zero max_context
        mock_model = Mock()
        mock_model.name = "test_model"
        mock_model.context_length = 0
        mock_ollama_client.list_models.return_value = [mock_model]

        mock_session = Mock()
        mock_session.session_id = "test"
        mock_message = Mock()
        mock_message.role = "assistant"
        mock_message.tool_calls = None
        mock_message.eval_count = 100
        mock_message.prompt_eval_count = 50
        mock_session.messages = [mock_message]

        # Execute
        result = context_service.calculate_context_usage_on_demand(
            mock_session, "test_model"
        )

        # Should handle zero division gracefully
        assert result.percentage == 0.0

    def test_uses_most_recent_valid_message(
        self, context_service, mock_ollama_client, mock_model_info
    ):
        """Test that the service uses the most recent valid assistant message."""
        mock_ollama_client.list_models.return_value = [mock_model_info]

        # Create session with multiple valid messages
        mock_session = Mock()
        mock_session.session_id = "test"

        # Older message
        old_message = Mock()
        old_message.role = "assistant"
        old_message.tool_calls = None
        old_message.eval_count = 50
        old_message.prompt_eval_count = 25

        # More recent message (should be used)
        recent_message = Mock()
        recent_message.role = "assistant"
        recent_message.tool_calls = None
        recent_message.eval_count = 100
        recent_message.prompt_eval_count = 75

        mock_session.messages = [old_message, recent_message]

        # Execute
        result = context_service.calculate_context_usage_on_demand(
            mock_session, "llama2:7b"
        )

        # Should use the most recent message (100 + 75 = 175)
        assert result.current_usage == 175
