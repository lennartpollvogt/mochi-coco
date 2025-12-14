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


class TestDynamicContextWindowService:
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


class TestDynamicContextWindowFeatures:
    """Test suite for new dynamic context window features."""

    @pytest.fixture
    def dynamic_service(self, mock_ollama_client):
        """Create DynamicContextWindowService for testing."""
        from mochi_coco.services.context_window_service import (
            DynamicContextWindowService,
        )

        return DynamicContextWindowService(mock_ollama_client)

    @pytest.fixture
    def mock_session_with_context_config(self):
        """Create a mock session with dynamic context window configuration."""
        session = Mock()
        session.session_id = "test-session"
        session.metadata = Mock()
        session.metadata.context_window_config = {
            "dynamic_enabled": True,
            "current_window": 8192,
            "last_adjustment": "2024-01-01T00:00:00",
            "adjustment_history": [],
            "manual_override": False,
        }
        session.messages = []
        return session

    def test_calculate_optimal_context_window_initial_setup(
        self, dynamic_service, mock_ollama_client
    ):
        """Test optimal context window calculation for initial setup."""
        # Setup mock
        mock_model = Mock()
        mock_model.name = "test-model"
        mock_model.context_length = 32768
        mock_ollama_client.list_models.return_value = [mock_model]

        session = Mock()
        session.session_id = "test"
        session.messages = []

        # Execute
        decision = dynamic_service.calculate_optimal_context_window(
            session, "test-model"
        )

        # Should recommend conservative default for new session
        assert decision.should_adjust is True
        assert decision.new_context_window == 8192  # Conservative default
        assert decision.reason.value == "initial_setup"
        assert "conservative" in decision.explanation.lower()

    def test_calculate_optimal_context_window_high_usage(
        self, dynamic_service, mock_ollama_client
    ):
        """Test context window expansion for high usage."""
        # Setup mock with high usage
        mock_model = Mock()
        mock_model.name = "test-model"
        mock_model.context_length = 32768
        mock_ollama_client.list_models.return_value = [mock_model]

        session = Mock()
        session.session_id = "test"
        session.metadata = Mock()
        session.metadata.context_window_config = {
            "dynamic_enabled": True,
            "current_window": 4096,
            "last_adjustment": None,
            "adjustment_history": [],
            "manual_override": False,
        }

        # Mock message with high usage (95% of 4096, above MAX_USAGE_THRESHOLD of 90%)
        high_usage_message = Mock()
        high_usage_message.role = "assistant"
        high_usage_message.tool_calls = None
        high_usage_message.eval_count = 2200
        high_usage_message.prompt_eval_count = 1691  # Total: 3891 (95% of 4096)
        session.messages = [high_usage_message]

        # Execute
        decision = dynamic_service.calculate_optimal_context_window(
            session, "test-model"
        )

        # Should recommend expansion
        assert decision.should_adjust is True
        assert decision.new_context_window > 4096
        # With Phase 6 improvements, the reason may vary based on threshold logic
        assert decision.reason.value in ["usage_threshold", "performance_optimization"]
        # The percentage should be calculated against the current window (4096), so 3891/4096 = ~95%
        assert decision.current_percentage >= 90.0

    def test_calculate_optimal_context_window_low_usage(
        self, dynamic_service, mock_ollama_client
    ):
        """Test context window optimization for low usage."""
        # Setup mock with low usage
        mock_model = Mock()
        mock_model.name = "test-model"
        mock_model.context_length = 32768
        mock_ollama_client.list_models.return_value = [mock_model]

        session = Mock()
        session.session_id = "test"
        session.metadata = Mock()
        session.metadata.context_window_config = {"current_window": 16384}

        # Mock message with very low usage (10% of 16384, below 15% MIN_USAGE_THRESHOLD)
        low_usage_message = Mock()
        low_usage_message.role = "assistant"
        low_usage_message.tool_calls = None
        low_usage_message.eval_count = 1000
        low_usage_message.prompt_eval_count = 638  # Total: 1638 (10% of 16384)
        session.messages = [low_usage_message]

        # Execute
        decision = dynamic_service.calculate_optimal_context_window(
            session, "test-model"
        )

        # Should recommend optimization (reduction)
        assert decision.should_adjust is True
        assert decision.new_context_window < 16384
        assert decision.reason.value == "performance_optimization"
        assert decision.current_percentage <= 15.0

    def test_reset_context_window_for_model_change(
        self, dynamic_service, mock_ollama_client
    ):
        """Test context window reset when model changes."""
        # Setup mock for new model
        mock_model = Mock()
        mock_model.name = "new-model"
        mock_model.context_length = 16384
        mock_ollama_client.list_models.return_value = [mock_model]

        session = Mock()
        session.session_id = "test"

        # Mock current usage
        usage_message = Mock()
        usage_message.role = "assistant"
        usage_message.tool_calls = None
        usage_message.eval_count = 1500
        usage_message.prompt_eval_count = 1000  # Total: 2500
        session.messages = [usage_message]

        # Execute
        decision = dynamic_service.reset_context_window_for_model_change(
            session, "old-model", "new-model"
        )

        # Should recommend conservative reset
        assert decision.should_adjust is True
        assert decision.new_context_window is not None
        assert decision.new_context_window >= 2048  # At least minimum
        assert decision.new_context_window <= int(16384 * 0.9)  # Within safety buffer
        assert decision.reason.value == "model_change"
        assert "new-model" in decision.explanation

    def test_context_usage_with_dynamic_metadata(
        self, dynamic_service, mock_ollama_client, mock_session_with_context_config
    ):
        """Test context usage calculation includes dynamic metadata."""
        # Setup mock
        mock_model = Mock()
        mock_model.name = "test-model"
        mock_model.context_length = 16384
        mock_ollama_client.list_models.return_value = [mock_model]

        # Add usage message
        usage_message = Mock()
        usage_message.role = "assistant"
        usage_message.tool_calls = None
        usage_message.eval_count = 1000
        usage_message.prompt_eval_count = 500
        mock_session_with_context_config.messages = [usage_message]

        # Execute
        result = dynamic_service.calculate_context_usage_on_demand(
            mock_session_with_context_config, "test-model"
        )

        # Should include dynamic metadata
        assert result.has_valid_data is True
        assert result.is_dynamic is True
        assert result.optimal_context is not None
        assert result.last_adjustment == "2024-01-01T00:00:00"

    def test_make_context_decision_optimal_usage(self, dynamic_service):
        """Test context decision for optimal usage range."""
        session = Mock()

        # Test moderate usage (50% - in optimal range)
        decision = dynamic_service._make_context_decision(
            current_usage=2048,
            current_percentage=50.0,
            max_context=16384,
            current_context_window=4096,
            session=session,
        )

        # Should not adjust
        assert decision.should_adjust is False
        assert decision.new_context_window == 4096
        assert "optimal" in decision.explanation.lower()

    def test_calculate_optimal_context_window_no_model(
        self, dynamic_service, mock_ollama_client
    ):
        """Test optimal context calculation when model not found."""
        # Setup mock with no models
        mock_ollama_client.list_models.return_value = []

        session = Mock()
        session.session_id = "test"
        session.messages = []

        # Execute
        decision = dynamic_service.calculate_optimal_context_window(
            session, "nonexistent-model"
        )

        # With Phase 6 graceful degradation, should use fallback
        assert decision.should_adjust is True
        assert decision.new_context_window == dynamic_service.DEFAULT_FALLBACK_CONTEXT
        assert "fallback" in decision.explanation.lower()

    def test_context_window_safety_limits(self, dynamic_service):
        """Test that context window recommendations respect safety limits."""
        # Test minimum context enforcement
        result = dynamic_service._calculate_optimal_context_window(
            current_usage=100,  # Very low usage
            max_context=32768,
            session=Mock(),
        )

        # Should enforce minimum
        assert result >= dynamic_service.MIN_CONTEXT_WINDOW

    def test_backward_compatibility_alias(self):
        """Test that ContextWindowService is aliased to DynamicContextWindowService."""
        from mochi_coco.services.context_window_service import (
            ContextWindowService,
            DynamicContextWindowService,
        )

        # Should be the same class
        assert ContextWindowService is DynamicContextWindowService
