"""
Unit tests for CommandResultHandler model change handling (Phase 4 implementation).

Tests the integration between CommandResultHandler and DynamicContextWindowService
for handling model changes with context window reset logic.
"""

import logging
from unittest.mock import Mock, patch

import pytest

from mochi_coco.commands import CommandResult
from mochi_coco.controllers.command_result_handler import (
    CommandResultHandler,
    StateUpdateResult,
)
from mochi_coco.services.context_window_service import (
    ContextDecisionReason,
    ContextWindowDecision,
)


class TestCommandResultHandlerModelChange:
    """Test model change handling in CommandResultHandler."""

    @pytest.fixture
    def mock_ui_orchestrator(self):
        """Mock UI orchestrator."""
        return Mock()

    @pytest.fixture
    def mock_context_window_service(self):
        """Mock context window service."""
        service = Mock()
        # Default successful reset
        service.reset_context_window_for_model_change.return_value = ContextWindowDecision(
            should_adjust=True,
            new_context_window=8192,
            reason=ContextDecisionReason.MODEL_CHANGE,
            current_usage=2048,
            current_percentage=25.0,
            explanation="Model changed to new-model, adjusted context window to 8,192 tokens",
        )
        return service

    @pytest.fixture
    def mock_session(self):
        """Mock chat session."""
        session = Mock()
        session.session_id = "test-session"
        session.metadata = Mock()
        session.metadata.context_window = 4096
        return session

    @pytest.fixture
    def handler_with_service(self, mock_ui_orchestrator, mock_context_window_service):
        """CommandResultHandler with context window service."""
        return CommandResultHandler(mock_ui_orchestrator, mock_context_window_service)

    @pytest.fixture
    def handler_without_service(self, mock_ui_orchestrator):
        """CommandResultHandler without context window service."""
        return CommandResultHandler(mock_ui_orchestrator, None)

    def test_model_change_with_context_window_service(
        self,
        handler_with_service,
        mock_session,
        mock_context_window_service,
        mock_ui_orchestrator,
    ):
        """Test model change handling when context window service is available."""
        # Setup command result with model change
        result = CommandResult(should_continue=True, new_model="new-model")
        old_model = "old-model"

        # Execute
        state_result = handler_with_service.handle_command_result(
            result, mock_session, old_model
        )

        # Verify state result
        assert isinstance(state_result, StateUpdateResult)
        assert state_result.model == "new-model"
        assert state_result.session == mock_session
        assert state_result.should_continue is True
        assert state_result.should_exit is False

        # Verify context window service was called
        mock_context_window_service.reset_context_window_for_model_change.assert_called_once_with(
            mock_session, old_model, "new-model"
        )

        # Verify session metadata was updated
        assert mock_session.metadata.context_window == 8192
        mock_session.save_session.assert_called_once()

        # Verify user feedback was displayed
        expected_calls = [
            (
                "Context window adjusted: Model changed to new-model, adjusted context window to 8,192 tokens",
            ),
            ("Switched to model: new-model",),
        ]
        actual_calls = [
            call[0] for call in mock_ui_orchestrator.display_info_message.call_args_list
        ]
        assert actual_calls == expected_calls

    def test_model_change_without_adjustment_needed(
        self,
        handler_with_service,
        mock_session,
        mock_context_window_service,
        mock_ui_orchestrator,
    ):
        """Test model change when no context window adjustment is needed."""
        # Setup service to return no adjustment needed
        mock_context_window_service.reset_context_window_for_model_change.return_value = ContextWindowDecision(
            should_adjust=False,
            new_context_window=None,
            reason=ContextDecisionReason.MODEL_CHANGE,
            current_usage=2048,
            current_percentage=50.0,
            explanation="Current context window is suitable for new model",
        )

        result = CommandResult(should_continue=True, new_model="new-model")
        old_model = "old-model"

        # Execute
        handler_with_service.handle_command_result(result, mock_session, old_model)

        # Verify context window service was called
        mock_context_window_service.reset_context_window_for_model_change.assert_called_once()

        # Verify session metadata was NOT updated (since no adjustment needed)
        mock_session.save_session.assert_not_called()

        # Verify only model switch message was displayed
        mock_ui_orchestrator.display_info_message.assert_called_once_with(
            "Switched to model: new-model"
        )

    def test_model_change_without_context_window_service(
        self, handler_without_service, mock_session, mock_ui_orchestrator
    ):
        """Test model change handling when context window service is not available."""
        result = CommandResult(should_continue=True, new_model="new-model")
        old_model = "old-model"

        # Execute
        state_result = handler_without_service.handle_command_result(
            result, mock_session, old_model
        )

        # Verify state result is still correct
        assert state_result.model == "new-model"
        assert state_result.session == mock_session

        # Verify only model switch message was displayed
        mock_ui_orchestrator.display_info_message.assert_called_once_with(
            "Switched to model: new-model"
        )

    def test_model_change_with_context_window_service_error(
        self,
        handler_with_service,
        mock_session,
        mock_context_window_service,
        mock_ui_orchestrator,
    ):
        """Test model change handling when context window service throws an error."""
        # Setup service to throw an exception
        mock_context_window_service.reset_context_window_for_model_change.side_effect = Exception(
            "Service error"
        )

        result = CommandResult(should_continue=True, new_model="new-model")
        old_model = "old-model"

        # Execute (should not raise exception)
        state_result = handler_with_service.handle_command_result(
            result, mock_session, old_model
        )

        # Verify state result is still correct
        assert state_result.model == "new-model"
        assert state_result.session == mock_session

        # Verify error handling message was displayed
        expected_calls = [
            ("Model switched successfully (context window adjustment unavailable)",),
            ("Switched to model: new-model",),
        ]
        actual_calls = [
            call[0] for call in mock_ui_orchestrator.display_info_message.call_args_list
        ]
        assert actual_calls == expected_calls

    def test_no_model_change_no_context_window_reset(
        self,
        handler_with_service,
        mock_session,
        mock_context_window_service,
        mock_ui_orchestrator,
    ):
        """Test that context window reset is not called when model doesn't change."""
        result = CommandResult(should_continue=True, new_model="same-model")
        current_model = "same-model"

        # Execute
        handler_with_service.handle_command_result(result, mock_session, current_model)

        # Verify context window service was NOT called
        mock_context_window_service.reset_context_window_for_model_change.assert_not_called()

        # Verify no model switch message was displayed
        mock_ui_orchestrator.display_info_message.assert_not_called()

    def test_session_change_no_model_change_no_context_reset(
        self,
        handler_with_service,
        mock_session,
        mock_context_window_service,
        mock_ui_orchestrator,
    ):
        """Test that context window reset is not called for session changes without model change."""
        new_session = Mock()
        new_session.session_id = "new-session"

        result = CommandResult(should_continue=True, new_session=new_session)
        current_model = "same-model"

        # Execute
        handler_with_service.handle_command_result(result, mock_session, current_model)

        # Verify context window service was NOT called
        mock_context_window_service.reset_context_window_for_model_change.assert_not_called()

        # Verify only session switch message was displayed
        mock_ui_orchestrator.display_info_message.assert_called_once_with(
            "Switched to session: new-session"
        )

    @patch("mochi_coco.controllers.command_result_handler.logger")
    def test_model_change_logging(
        self,
        mock_logger,
        handler_with_service,
        mock_session,
        mock_context_window_service,
    ):
        """Test that model change operations are properly logged."""
        result = CommandResult(should_continue=True, new_model="new-model")
        old_model = "old-model"

        # Execute
        handler_with_service.handle_command_result(result, mock_session, old_model)

        # Verify logging calls
        mock_logger.info.assert_any_call(
            "Handling model change: old-model -> new-model"
        )
        mock_logger.info.assert_any_call(
            "Context window reset for model change: old-model -> new-model, "
            "new context window: 8,192 tokens"
        )

    @patch("mochi_coco.controllers.command_result_handler.logger")
    def test_model_change_error_logging(
        self,
        mock_logger,
        handler_with_service,
        mock_session,
        mock_context_window_service,
    ):
        """Test that model change errors are properly logged."""
        # Setup service to throw an exception
        error_message = "Service error"
        mock_context_window_service.reset_context_window_for_model_change.side_effect = Exception(
            error_message
        )

        result = CommandResult(should_continue=True, new_model="new-model")
        old_model = "old-model"

        # Execute
        handler_with_service.handle_command_result(result, mock_session, old_model)

        # Verify error logging
        mock_logger.error.assert_called_once_with(
            f"Error handling model change context window reset: {error_message}"
        )

    def test_exit_command_no_model_change_handling(
        self, handler_with_service, mock_session, mock_context_window_service
    ):
        """Test that exit commands don't trigger model change handling."""
        result = CommandResult(should_exit=True, new_model="new-model")
        old_model = "old-model"

        # Execute
        state_result = handler_with_service.handle_command_result(
            result, mock_session, old_model
        )

        # Verify exit state
        assert state_result.should_exit is True
        assert state_result.should_continue is False

        # Verify context window service was NOT called
        mock_context_window_service.reset_context_window_for_model_change.assert_not_called()

    def test_non_continue_command_no_model_change_handling(
        self, handler_with_service, mock_session, mock_context_window_service
    ):
        """Test that non-continue commands don't trigger model change handling."""
        result = CommandResult(should_continue=False, new_model="new-model")
        old_model = "old-model"

        # Execute
        state_result = handler_with_service.handle_command_result(
            result, mock_session, old_model
        )

        # Verify continue state
        assert state_result.should_continue is True
        assert state_result.should_exit is False

        # Verify context window service was NOT called
        mock_context_window_service.reset_context_window_for_model_change.assert_not_called()
