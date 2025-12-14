"""
Command result handler for processing command execution results and managing state transitions.

This module extracts command result handling logic from ChatController to improve
separation of concerns and provide focused command result processing.
"""

import logging
from typing import TYPE_CHECKING, NamedTuple, Optional

from ..commands import CommandResult

if TYPE_CHECKING:
    from ..chat import ChatSession
    from ..services import DynamicContextWindowService
    from ..ui.chat_ui_orchestrator import ChatUIOrchestrator

logger = logging.getLogger(__name__)


class StateUpdateResult(NamedTuple):
    """Result of state update operation."""

    session: Optional["ChatSession"]
    model: Optional[str]
    should_continue: bool
    should_exit: bool


class CommandResultHandler:
    """Handles command execution results and manages state transitions."""

    def __init__(
        self,
        ui_orchestrator: "ChatUIOrchestrator",
        context_window_service: Optional["DynamicContextWindowService"] = None,
    ):
        self.ui_orchestrator = ui_orchestrator
        self.context_window_service = context_window_service

    def handle_command_result(
        self, result: CommandResult, current_session: "ChatSession", current_model: str
    ) -> StateUpdateResult:
        """
        Process command result and determine next application state.

        Args:
            result: Command execution result
            current_session: Current chat session
            current_model: Current model name

        Returns:
            StateUpdateResult with updated session/model and flow control
        """
        # Handle exit commands
        if result.should_exit:
            return StateUpdateResult(current_session, current_model, False, True)

        # Handle continue commands (no state change)
        if result.should_continue:
            updated_session = result.new_session or current_session
            updated_model = result.new_model or current_model

            # Handle model changes with context window reset
            if updated_model != current_model:
                self._handle_model_change(updated_session, current_model, updated_model)

            # Display state changes if any occurred
            self._display_state_changes(
                current_session, updated_session, current_model, updated_model
            )

            return StateUpdateResult(updated_session, updated_model, True, False)

        # Command processed, continue with current state
        return StateUpdateResult(current_session, current_model, True, False)

    def _display_state_changes(
        self,
        old_session: "ChatSession",
        new_session: "ChatSession",
        old_model: str,
        new_model: str,
    ) -> None:
        """Display any state changes to the user."""
        if new_session != old_session:
            self.ui_orchestrator.display_info_message(
                f"Switched to session: {new_session.session_id}"
            )

        if new_model != old_model:
            self.ui_orchestrator.display_info_message(f"Switched to model: {new_model}")

    def _handle_model_change(
        self, session: "ChatSession", old_model: str, new_model: str
    ) -> None:
        """
        Handle model change by resetting context window if service is available.

        Args:
            session: Current chat session
            old_model: Previous model name
            new_model: New model name
        """
        if not self.context_window_service:
            logger.debug(
                "Context window service not available for model change handling"
            )
            return

        try:
            logger.info(f"Handling model change: {old_model} -> {new_model}")

            # Call the context window service to handle model change
            decision = (
                self.context_window_service.reset_context_window_for_model_change(
                    session, old_model, new_model
                )
            )

            # Update session metadata if context window was adjusted
            if decision.should_adjust and decision.new_context_window:
                session.metadata.context_window = decision.new_context_window
                session.save_session()

                # Display context window adjustment message to user
                self.ui_orchestrator.display_info_message(
                    f"Context window adjusted: {decision.explanation}"
                )

                logger.info(
                    f"Context window reset for model change: {old_model} -> {new_model}, "
                    f"new context window: {decision.new_context_window:,} tokens"
                )
            else:
                logger.debug(
                    f"No context window adjustment needed: {decision.explanation}"
                )

        except Exception as e:
            logger.error(f"Error handling model change context window reset: {str(e)}")
            # Don't fail the model change operation - just log the error
            self.ui_orchestrator.display_info_message(
                "Model switched successfully (context window adjustment unavailable)"
            )
