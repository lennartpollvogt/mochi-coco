"""
Command result handler for processing command execution results and managing state transitions.

This module extracts command result handling logic from ChatController to improve
separation of concerns and provide focused command result processing.
"""

from typing import Optional, NamedTuple, TYPE_CHECKING
from ..commands import CommandResult

if TYPE_CHECKING:
    from ..chat import ChatSession
    from ..ui.chat_ui_orchestrator import ChatUIOrchestrator


class StateUpdateResult(NamedTuple):
    """Result of state update operation."""
    session: Optional["ChatSession"]
    model: Optional[str]
    should_continue: bool
    should_exit: bool


class CommandResultHandler:
    """Handles command execution results and manages state transitions."""

    def __init__(self, ui_orchestrator: "ChatUIOrchestrator"):
        self.ui_orchestrator = ui_orchestrator

    def handle_command_result(self, result: CommandResult,
                            current_session: "ChatSession",
                            current_model: str) -> StateUpdateResult:
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

            # Display state changes if any occurred
            self._display_state_changes(
                current_session, updated_session,
                current_model, updated_model
            )

            return StateUpdateResult(updated_session, updated_model, True, False)

        # Command processed, continue with current state
        return StateUpdateResult(current_session, current_model, True, False)

    def _display_state_changes(self, old_session: "ChatSession", new_session: "ChatSession",
                              old_model: str, new_model: str) -> None:
        """Display any state changes to the user."""
        if new_session != old_session:
            self.ui_orchestrator.display_info_message(
                f"Switched to session: {new_session.session_id}"
            )

        if new_model != old_model:
            self.ui_orchestrator.display_info_message(
                f"Switched to model: {new_model}"
            )
