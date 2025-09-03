"""
Session manager for handling chat session lifecycle and operations.
"""

from typing import Optional, Tuple, TYPE_CHECKING
import typer

if TYPE_CHECKING:
    from ..chat import ChatSession
    from ..ui import ModelSelector



class SessionManager:
    """Manages chat session lifecycle, creation, and configuration."""

    def __init__(self, model_selector: "ModelSelector"):
        self.model_selector = model_selector

    def initialize_session(self) -> Tuple[Optional["ChatSession"], Optional[str], bool, bool]:
        """
        Initialize a chat session - either select existing or create new.

        Returns:
            Tuple of (session, selected_model, markdown_enabled, show_thinking)
        """
        session, selected_model, markdown_enabled, show_thinking = self.model_selector.select_session_or_new()

        if session is None and selected_model is None:
            return None, None, False, False

        return session, selected_model, markdown_enabled, show_thinking

    def setup_session(self, session: Optional["ChatSession"], selected_model: Optional[str]) -> Tuple[Optional["ChatSession"], Optional[str]]:
        """
        Set up the session for chatting - create new if needed or load existing.

        Args:
            session: Existing session or None for new session
            selected_model: Selected model name

        Returns:
            Tuple of (final_session, final_model)
        """
        if session is None and selected_model is None:
            typer.secho("Exiting.", fg=typer.colors.YELLOW)
            return None, None

        # Handle new session
        if session is None:
            if not selected_model:
                typer.secho("No model selected. Exiting.", fg=typer.colors.YELLOW)
                return None, None

            from ..chat import ChatSession
            session = ChatSession(model=selected_model)
            typer.secho(f"\n💬 New chat started with {selected_model}",
                        fg=typer.colors.BRIGHT_GREEN)
            typer.secho(f"Session ID: {session.session_id}", fg=typer.colors.CYAN)
            return session, selected_model
        else:
            # Handle existing session
            self.model_selector.display_chat_history(session)
            selected_model = session.metadata.model
            typer.secho(f"\n💬 Continuing chat with {selected_model}",
                        fg=typer.colors.BRIGHT_GREEN)
            return session, selected_model

    def display_session_info(self, markdown_enabled: bool, show_thinking: bool) -> None:
        """Display session information and available commands."""
        typer.secho("Type 'exit' to quit, '/models' to change model, '/chats' to switch sessions, '/edit' to edit messages, '/markdown' to toggle formatting, or '/thinking' to toggle thinking blocks.\n",
                   fg=typer.colors.BRIGHT_GREEN)

        if markdown_enabled:
            typer.secho("Markdown rendering is enabled.", fg=typer.colors.CYAN)
            if show_thinking:
                typer.secho("Thinking blocks will be displayed.", fg=typer.colors.CYAN)
