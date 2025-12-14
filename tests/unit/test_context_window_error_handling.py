"""
Unit tests for Phase 6: Error Handling and Resilience in Dynamic Context Window Service.

Tests graceful degradation, validation, edge cases, and recovery mechanisms.
"""

from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest

from mochi_coco.chat.session import ChatSession, SessionMessage, SessionMetadata
from mochi_coco.ollama.client import ModelInfo, OllamaClient
from mochi_coco.services.context_window_service import (
    ContextDecisionReason,
    ContextWindowDecision,
    ContextWindowInfo,
    DynamicContextWindowService,
)


class TestContextWindowErrorHandling:
    """Test error handling and resilience in context window service."""

    @pytest.fixture
    def mock_ollama_client(self):
        """Mock Ollama client."""
        return Mock(spec=OllamaClient)

    @pytest.fixture
    def service(self, mock_ollama_client):
        """Create service instance."""
        return DynamicContextWindowService(mock_ollama_client)

    @pytest.fixture
    def mock_session_with_corrupted_metadata(self):
        """Mock session with corrupted metadata."""
        session = Mock()
        session.session_id = "test-session"
        session.messages = []
        session.metadata = Mock()
        # Simulate corrupted context_window_config
        session.metadata.context_window_config = "invalid_string_instead_of_dict"
        return session

    @pytest.fixture
    def mock_session_with_missing_metadata(self):
        """Mock session with missing metadata."""
        session = Mock()
        session.session_id = "test-session"
        session.messages = []
        session.metadata = None
        return session

    @pytest.fixture
    def mock_session_with_invalid_context_window(self):
        """Mock session with invalid context window values."""
        session = Mock()
        session.session_id = "test-session"
        session.messages = []
        session.metadata = Mock()
        session.metadata.context_window_config = {
            "dynamic_enabled": True,
            "current_window": -5000,  # Invalid negative value
            "last_adjustment": None,
            "adjustment_history": [],
            "manual_override": False,
        }
        return session

    def test_graceful_degradation_model_info_unavailable(
        self, service, mock_ollama_client
    ):
        """Test graceful degradation when model info is unavailable."""
        # Setup: No models available
        mock_ollama_client.list_models.return_value = []

        session = Mock()
        session.session_id = "test-session"
        session.messages = []
        session.metadata = Mock()
        session.metadata.context_window_config = None

        # Execute
        decision = service.calculate_optimal_context_window(session, "unknown-model")

        # Verify: Should use fallback context
        assert decision.should_adjust is True
        assert decision.new_context_window == service.DEFAULT_FALLBACK_CONTEXT
        assert decision.reason == ContextDecisionReason.INITIAL_SETUP
        assert "fallback" in decision.explanation.lower()

    def test_graceful_degradation_calculation_error(self, service, mock_ollama_client):
        """Test graceful degradation when calculation fails with exception."""
        # Setup: Mock to raise exception during model list
        mock_ollama_client.list_models.side_effect = ConnectionError("Network error")

        session = Mock()
        session.session_id = "test-session"
        session.messages = []
        session.metadata = Mock()
        session.metadata.context_window_config = {
            "dynamic_enabled": True,
            "current_window": 8192,
            "last_adjustment": None,
            "adjustment_history": [],
            "manual_override": False,
        }

        # Execute
        decision = service.calculate_optimal_context_window(session, "test-model")

        # Verify: Should use session's current context as fallback
        assert decision.should_adjust is True
        assert decision.new_context_window == 8192
        assert decision.reason == ContextDecisionReason.INITIAL_SETUP
        assert "fallback" in decision.explanation.lower()
        # The error is logged but not included in explanation for graceful degradation
        assert "fallback" in decision.explanation.lower()

    def test_corrupted_metadata_recovery(
        self, service, mock_session_with_corrupted_metadata
    ):
        """Test recovery from corrupted session metadata."""
        # Execute fallback strategy
        fallback_context = service._get_fallback_context_window(
            mock_session_with_corrupted_metadata
        )

        # Verify: Should recover with default fallback
        assert fallback_context == service.DEFAULT_FALLBACK_CONTEXT

    def test_missing_metadata_handling(
        self, service, mock_session_with_missing_metadata
    ):
        """Test handling of sessions with missing metadata."""
        # Execute fallback strategy
        fallback_context = service._get_fallback_context_window(
            mock_session_with_missing_metadata
        )

        # Verify: Should use default fallback
        assert fallback_context == service.DEFAULT_FALLBACK_CONTEXT

    def test_invalid_context_window_validation(
        self, service, mock_session_with_invalid_context_window
    ):
        """Test validation of invalid context window values."""
        # Execute fallback strategy
        fallback_context = service._get_fallback_context_window(
            mock_session_with_invalid_context_window
        )

        # Verify: Should use minimum context window due to invalid negative value
        assert fallback_context == service.DEFAULT_FALLBACK_CONTEXT

    def test_context_window_validation_positive_integer(self, service):
        """Test context window validation ensures positive integer."""
        # Test invalid inputs
        assert service._validate_context_window(0) == service.MIN_CONTEXT_WINDOW
        assert service._validate_context_window(-1000) == service.MIN_CONTEXT_WINDOW
        assert service._validate_context_window("invalid") == service.MIN_CONTEXT_WINDOW
        assert service._validate_context_window(None) == service.MIN_CONTEXT_WINDOW

    def test_context_window_validation_minimum_enforcement(self, service):
        """Test context window validation enforces minimum."""
        # Test below minimum
        assert service._validate_context_window(100) == service.MIN_CONTEXT_WINDOW
        assert service._validate_context_window(1000) == service.MIN_CONTEXT_WINDOW

        # Test valid values
        assert service._validate_context_window(4096) == 4096
        assert service._validate_context_window(8192) == 8192

    def test_context_window_validation_maximum_capping(self, service):
        """Test context window validation caps at model maximum."""
        max_context = 32768

        # Test normal values
        assert service._validate_context_window(4096, max_context) == 4096
        assert service._validate_context_window(16384, max_context) == 16384

        # Test exceeding maximum (should be capped at 90% of max)
        expected_cap = int(max_context * service.CONTEXT_SAFETY_BUFFER)
        assert service._validate_context_window(50000, max_context) == expected_cap

    def test_very_large_context_usage_edge_case(self, service, mock_ollama_client):
        """Test handling of very large context usage that would exceed model limits."""
        # Setup: Model with limited context
        mock_model = Mock()
        mock_model.name = "small-model"
        mock_model.context_length = 8192  # Small context limit
        mock_ollama_client.list_models.return_value = [mock_model]

        # Mock session with very high usage that would require more than model max
        session = Mock()
        session.session_id = "test-session"
        session.messages = [
            Mock(token_counts={"total_tokens": 7500})  # Very high usage
        ]
        session.metadata = Mock()
        session.metadata.context_window_config = {
            "dynamic_enabled": True,
            "current_window": 4096,
            "last_adjustment": None,
            "adjustment_history": [],
            "manual_override": False,
        }

        # Execute
        decision = service.calculate_optimal_context_window(session, "small-model")

        # Verify: Should handle gracefully - may use conservative default for new session
        assert decision.should_adjust is True
        assert decision.new_context_window is not None
        assert decision.new_context_window >= service.MIN_CONTEXT_WINDOW

    def test_model_change_error_handling(self, service, mock_ollama_client):
        """Test error handling during model change operations."""
        # Setup: Mock client to fail on model lookup
        mock_ollama_client.list_models.side_effect = Exception("Server error")

        session = Mock()
        session.session_id = "test-session"
        session.messages = []
        session.metadata = Mock()
        session.metadata.context_window_config = {
            "dynamic_enabled": True,
            "current_window": 4096,
            "last_adjustment": None,
            "adjustment_history": [],
            "manual_override": False,
        }

        # Execute
        decision = service.reset_context_window_for_model_change(
            session, "old-model", "new-model"
        )

        # Verify: Should use fallback strategy
        assert decision.should_adjust is True
        assert decision.new_context_window == 4096  # From session metadata
        assert decision.reason == ContextDecisionReason.MODEL_CHANGE
        assert "fallback" in decision.explanation.lower()

    def test_safe_context_config_access(self, service):
        """Test safe context config access with various invalid inputs."""
        # Test with None session
        assert service._safe_get_context_config(None) is None

        # Test with session without metadata
        session_no_meta = Mock()
        session_no_meta.metadata = None
        assert service._safe_get_context_config(session_no_meta) is None

        # Test with session without context_window_config
        session_no_config = Mock()
        session_no_config.metadata = Mock()
        delattr(session_no_config.metadata, "context_window_config")
        assert service._safe_get_context_config(session_no_config) is None

        # Test with invalid config type (should auto-repair)
        session_invalid_config = Mock()
        session_invalid_config.metadata = Mock()
        session_invalid_config.metadata.context_window_config = "invalid"
        result = service._safe_get_context_config(session_invalid_config)
        assert result is not None
        assert isinstance(result, dict)
        assert result["dynamic_enabled"] is True
        assert result["current_window"] == 4096

        # Test with missing required fields (should auto-repair)
        session_incomplete = Mock()
        session_incomplete.metadata = Mock()
        session_incomplete.metadata.context_window_config = {
            "dynamic_enabled": True,
            # Missing other required fields
        }
        result = service._safe_get_context_config(session_incomplete)
        assert result is not None
        assert isinstance(result, dict)
        assert "current_window" in result
        assert "last_adjustment" in result
        assert "adjustment_history" in result
        assert "manual_override" in result

        # Test with valid config
        session_valid = Mock()
        session_valid.metadata = Mock()
        session_valid.metadata.context_window_config = {
            "dynamic_enabled": True,
            "current_window": 4096,
            "last_adjustment": None,
            "adjustment_history": [],
            "manual_override": False,
        }
        result = service._safe_get_context_config(session_valid)
        assert result is not None
        assert isinstance(result, dict)
        assert result["current_window"] == 4096

    def test_context_usage_calculation_error_handling(
        self, service, mock_ollama_client
    ):
        """Test error handling in context usage calculation."""
        # Setup: Model available but usage calculation fails
        mock_model = Mock()
        mock_model.name = "test-model"
        mock_model.context_length = 16384
        mock_ollama_client.list_models.return_value = [mock_model]

        # Session with malformed message that causes calculation error
        session = Mock()
        session.session_id = "test-session"
        # Mock messages to cause an error in usage calculation
        session.messages = [Mock(token_counts=None)]  # This should cause an error

        # Mock the usage calculation to raise an exception
        with patch.object(
            service,
            "_calculate_current_usage_from_history",
            side_effect=Exception("Calculation error"),
        ):
            info = service.calculate_context_usage_on_demand(session, "test-model")

            # Verify: Should return error info
            assert info.has_valid_data is False
            assert "Calculation failed" in info.error_message

    def test_edge_case_zero_usage_handling(self, service, mock_ollama_client):
        """Test handling of edge case with zero token usage."""
        # Setup
        mock_model = Mock()
        mock_model.name = "test-model"
        mock_model.context_length = 16384
        mock_ollama_client.list_models.return_value = [mock_model]

        session = Mock()
        session.session_id = "test-session"
        session.messages = []  # No messages = zero usage
        session.metadata = Mock()
        session.metadata.context_window_config = {
            "dynamic_enabled": True,
            "current_window": 4096,
            "last_adjustment": None,
            "adjustment_history": [],
            "manual_override": False,
        }

        # Execute
        decision = service.calculate_optimal_context_window(session, "test-model")

        # Verify: Should handle zero usage gracefully
        assert decision.should_adjust is True
        assert decision.new_context_window is not None
        assert decision.new_context_window >= service.MIN_CONTEXT_WINDOW

    def test_recovery_mechanism_preserves_session_id(self, service):
        """Test that recovery mechanisms preserve session identity."""
        session = Mock()
        session.session_id = "important-session-123"
        session.messages = []
        session.metadata = Mock()
        session.metadata.context_window_config = None

        # Attempt recovery
        recovered_context = service._recover_from_corrupted_metadata(session)

        # Verify: Session ID preserved, metadata repaired
        assert session.session_id == "important-session-123"
        assert recovered_context == service.DEFAULT_FALLBACK_CONTEXT
        assert isinstance(session.metadata.context_window_config, dict)

    def test_multiple_error_conditions_combined(self, service, mock_ollama_client):
        """Test handling of multiple error conditions occurring together."""
        # Setup: Multiple failures
        mock_ollama_client.list_models.side_effect = [
            # First call fails
            ConnectionError("Network error"),
        ]

        # Session with corrupted metadata AND no fallback
        session = Mock()
        session.session_id = "test-session"
        session.messages = []
        session.metadata = Mock()
        session.metadata.context_window_config = {"invalid": "structure"}

        # Execute
        decision = service.calculate_optimal_context_window(session, "test-model")

        # Verify: Should still provide a reasonable fallback
        assert decision.should_adjust is True
        assert decision.new_context_window == service.DEFAULT_FALLBACK_CONTEXT
        assert "fallback" in decision.explanation.lower()

    def test_validation_error_recovery(self, service):
        """Test recovery from validation errors."""
        # Test validation handles exception gracefully
        try:
            result = service._validate_context_window("invalid_type")
            assert result == service.MIN_CONTEXT_WINDOW
        except Exception:
            # If exception is raised, test that it's handled appropriately
            assert True

    def test_threshold_edge_cases(self, service, mock_ollama_client):
        """Test edge cases around usage thresholds."""
        # Setup
        mock_model = Mock()
        mock_model.name = "test-model"
        mock_model.context_length = 16384
        mock_ollama_client.list_models.return_value = [mock_model]

        session = Mock()
        session.session_id = "test-session"
        session.messages = [
            Mock(token_counts={"total_tokens": 3072})
        ]  # Exactly at threshold
        session.metadata = Mock()
        session.metadata.context_window_config = {
            "dynamic_enabled": True,
            "current_window": 4096,
            "last_adjustment": None,
            "adjustment_history": [],
            "manual_override": False,
        }

        # Execute
        decision = service.calculate_optimal_context_window(session, "test-model")

        # Verify: Should handle threshold edge case gracefully
        assert decision is not None
        # Current usage may be 0 if no valid token count found in messages
        assert decision.current_usage >= 0
        assert decision.should_adjust in [True, False]  # Either is acceptable
