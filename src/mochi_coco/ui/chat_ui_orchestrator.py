"""
Chat UI orchestrator that handles all chat-related UI display and user interactions.

This module extracts UI orchestration logic from ChatController to improve
separation of concerns and testability.
"""

from typing import TYPE_CHECKING, Optional

from rich.console import Console

from ..user_prompt import get_user_input
from .chat_interface import ChatInterface

if TYPE_CHECKING:
    from ..chat import ChatSession
    from ..services import ContextWindowService
    from ..ui import ModelSelector


class ChatUIOrchestrator:
    """Orchestrates all chat-related UI display and user interactions."""

    def __init__(self):
        self.chat_interface = ChatInterface()
        self.console = Console()

    def display_session_setup(
        self,
        session: "ChatSession",
        model: str,
        markdown_enabled: bool,
        show_thinking: bool,
        context_window_service: Optional["ContextWindowService"] = None,
    ) -> None:
        """Display session information and setup UI with on-demand context calculation."""
        # Calculate context window info ON-DEMAND only at session start
        context_info = None
        if context_window_service:
            try:
                context_info = context_window_service.calculate_context_usage_on_demand(
                    session,
                    model,  # Use current model, not historical models
                )
            except Exception as e:
                from ..services import ContextWindowInfo

                context_info = ContextWindowInfo(
                    current_usage=0,
                    max_context=0,
                    percentage=0.0,
                    has_valid_data=False,
                    error_message=f"Calculation failed: {str(e)}",
                )

        # Extract additional session metadata
        summary_model = session.metadata.summary_model
        tool_settings = session.get_tool_settings()
        session_summary = session.metadata.summary if session.metadata else None

        self.chat_interface.print_session_info(
            session_id=session.session_id,
            model=model,
            markdown=markdown_enabled,
            thinking=show_thinking,
            summary_model=summary_model,
            tool_settings=tool_settings,
            session_summary=session_summary,
            context_info=context_info,
        )

    def display_chat_history_if_needed(
        self, session: "ChatSession", model_selector: "ModelSelector"
    ) -> None:
        """Display existing chat history for resumed sessions."""
        if session.messages:
            self.chat_interface.print_separator()
            model_selector.display_chat_history(session)
            self.chat_interface.print_separator()

    def get_user_input(self) -> str:
        """Get user input with proper UI styling."""
        self.chat_interface.print_user_header()
        return get_user_input()

    def display_streaming_response_headers(self) -> None:
        """Display headers for streaming response."""
        self.chat_interface.print_separator()
        self.chat_interface.print_assistant_header()

    def display_response_footer(self) -> None:
        """Display footer after streaming response."""
        self.chat_interface.print_separator()

    def display_error(self, error_message: str) -> None:
        """Display error message with proper styling."""
        self.chat_interface.print_error_message(f"Error: {error_message}")

    def display_info_message(self, message: str) -> None:
        """Display info message with proper styling."""
        self.chat_interface.print_info_message(message)

    def display_success_message(self, message: str) -> None:
        """Display success message with proper styling."""
        self.chat_interface.print_success_message(message)

    def display_exit_message(self) -> None:
        """Display exit message."""
        import typer

        typer.secho("\nExiting.", fg=typer.colors.YELLOW)
